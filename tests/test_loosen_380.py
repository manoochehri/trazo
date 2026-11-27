"""Issue #380: no owner in routine merges or releases.

Three pieces, each tested with a stubbed `gh` (no live GitHub, no ruleset is touched):
(a) scripts/drop_verdict_check.sh removes trazo/verdict from the main ruleset's required checks,
    and scripts/rollback_ruleset.sh undoes it; (b) release.yml and scripts/allow_release_app.py;
(c) scripts/audit_merges.py and merge-audit.yml.
"""

import importlib.util
import json
import os
import stat
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DROP = ROOT / "scripts" / "drop_verdict_check.sh"
ROLLBACK = ROOT / "scripts" / "rollback_ruleset.sh"
SAVED = ROOT / "scripts" / "rulesets" / "main-ruleset.saved.json"


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---- (a) drop trazo/verdict from the main ruleset ------------------------------------------------

STUB = """#!/usr/bin/env bash
d=$(dirname "$0")
if [[ "$*" == *"-X PUT"* ]]; then
  cat > "$d/live.json"; touch "$d/put.called"; exit 0
fi
if [[ "$1" == repo ]]; then echo o/r; exit 0; fi
body=$(jq '. + {id:1,node_id:"x",_links:{},current_user_can_bypass:"never"}' "$d/live.json")
while [[ $# -gt 0 ]]; do
  if [[ "$1" == -q ]]; then jq -r "$2" <<< "$body"; exit 0; fi
  shift
done
printf '%s\\n' "$body"
"""


def _gh_dir(tmp_path, live):
    stub = tmp_path / "gh"
    stub.write_text(STUB)
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    (tmp_path / "live.json").write_text(json.dumps(live))
    return {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"}


def _run(script, tmp_path, args, live):
    env = _gh_dir(tmp_path, live)
    cmd = ["bash", str(script), *args]
    return subprocess.run(cmd, env=env, capture_output=True, text=True)  # noqa: S603, S607


def _contexts(ruleset):
    (rule,) = [r for r in ruleset["rules"] if r["type"] == "required_status_checks"]
    return [c["context"] for c in rule["parameters"]["required_status_checks"]]


def test_drop_removes_only_the_verdict_check(tmp_path):
    saved = json.loads(SAVED.read_text())
    r = _run(DROP, tmp_path, [], saved)
    assert r.returncode == 0, r.stderr
    live = json.loads((tmp_path / "live.json").read_text())
    assert _contexts(live) == ["secrets-scan", "docker", "test", "docs-updated"]
    # every other field is as saved
    want = json.loads(SAVED.read_text())
    want_rules = [r for r in want["rules"] if r["type"] != "required_status_checks"]
    got_rules = [r for r in live["rules"] if r["type"] != "required_status_checks"]
    assert got_rules == want_rules
    assert live["bypass_actors"] == [] and live["enforcement"] == "active"


def test_dry_run_writes_nothing(tmp_path):
    r = _run(DROP, tmp_path, ["--dry-run"], json.loads(SAVED.read_text()))
    assert r.returncode == 0, r.stderr
    assert not (tmp_path / "put.called").exists()
    assert "trazo/verdict" in r.stdout


def test_drop_is_idempotent(tmp_path):
    saved = json.loads(SAVED.read_text())
    _run(DROP, tmp_path, [], saved)
    again = _run(DROP, tmp_path, [], json.loads((tmp_path / "live.json").read_text()))
    assert again.returncode == 0, again.stderr
    assert _contexts(json.loads((tmp_path / "live.json").read_text()))[-1] == "docs-updated"


def test_drop_refuses_a_ruleset_with_another_name(tmp_path):
    other = {**json.loads(SAVED.read_text()), "name": "something else"}
    r = _run(DROP, tmp_path, [], other)
    assert r.returncode == 2
    assert not (tmp_path / "put.called").exists()


def test_drop_refuses_if_another_required_check_would_go(tmp_path):
    live = json.loads(SAVED.read_text())
    (rule,) = [x for x in live["rules"] if x["type"] == "required_status_checks"]
    rule["parameters"]["required_status_checks"] = [{"context": "trazo/verdict"}]
    r = _run(DROP, tmp_path, [], live)
    assert r.returncode == 2
    assert not (tmp_path / "put.called").exists()


def test_rollback_restores_the_saved_ruleset_after_a_drop(tmp_path):
    _run(DROP, tmp_path, [], json.loads(SAVED.read_text()))
    assert "trazo/verdict" not in _contexts(json.loads((tmp_path / "live.json").read_text()))
    r = _run(ROLLBACK, tmp_path, [], json.loads((tmp_path / "live.json").read_text()))
    assert r.returncode == 0, r.stderr
    assert "trazo/verdict" in _contexts(json.loads((tmp_path / "live.json").read_text()))


def test_scratch_script_never_names_the_main_ruleset_or_branch_refs_other_than_scratch():
    text = (ROOT / "scripts" / "scratch_drop_verdict_test.sh").read_text()
    assert "refs/heads/scratch/drop-verdict-test" in text
    assert "~DEFAULT_BRANCH" not in text
    assert "trap cleanup EXIT" in text
    assert "drop_verdict_check.sh" in text and "rollback_ruleset.sh" in text


# ---- (b) release workflow and the tag-bypass script ----------------------------------------------

RELEASE = ROOT / ".github/workflows/release.yml"


def _wf(path):
    return yaml.safe_load(path.read_text())


def test_release_is_dispatch_only_owner_only_and_runs_release_sh_as_the_builder_app():
    wf = _wf(RELEASE)
    triggers = wf.get("on", wf.get(True))
    assert set(triggers) == {"workflow_dispatch"}
    job = wf["jobs"]["release"]
    cond = " ".join(str(job["if"]).split())
    assert "github.actor == github.repository_owner" in cond
    assert "default_branch" in cond
    text = RELEASE.read_text()
    assert "BUILDER_APP_ID" in text and "BUILDER_APP_PRIVATE_KEY" in text
    assert "scripts/release.sh" in text
    assert "permission-contents: write" in text
    assert "fetch-depth: 0" in text


def test_release_checks_ci_green_before_tagging_and_never_force_pushes():
    text = RELEASE.read_text()
    assert "check-runs" in text
    assert text.index("check-runs") < text.rindex("scripts/release.sh")
    assert "--force" not in text and "push -f" not in text


def test_release_inputs_never_reach_the_shell_as_text():
    wf = _wf(RELEASE)
    for step in wf["jobs"]["release"]["steps"]:
        assert "${{" not in str(step.get("run", "")), step.get("name")


def test_every_action_in_new_workflows_is_pinned():
    import re

    for name in ("release.yml", "merge-audit.yml"):
        for ref in re.findall(
            r"^\s*(?:-\s*)?uses:\s*(\S+)", (ROOT / ".github/workflows" / name).read_text(), re.M
        ):
            assert re.match(r"^[\w.-]+/[\w.-]+(/[\w.-]+)*@[0-9a-f]{40}$", ref), (name, ref)


V_CREATE = {
    "id": 3,
    "name": "v-create",
    "target": "tag",
    "enforcement": "active",
    "conditions": {"ref_name": {"exclude": [], "include": ["refs/tags/v*"]}},
    "bypass_actors": [{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}],
    "rules": [{"type": "creation"}],
}


def test_allow_release_app_adds_integration_to_v_create_only():
    mod = _load("allow_release_app", "scripts/allow_release_app.py")
    payload = mod.add_payload(V_CREATE, 12345)
    assert {"actor_id": 12345, "actor_type": "Integration", "bypass_mode": "always"} in payload[
        "bypass_actors"
    ]
    assert V_CREATE["bypass_actors"][0] in payload["bypass_actors"]  # Admin stays
    assert payload["rules"] == [{"type": "creation"}]
    assert payload["name"] == "v-create"


def test_allow_release_app_is_idempotent_and_reversible():
    mod = _load("allow_release_app", "scripts/allow_release_app.py")
    once = mod.add_payload(V_CREATE, 12345)
    assert mod.add_payload({**V_CREATE, **once}, 12345) == once
    assert (
        mod.remove_payload({**V_CREATE, **once}, 12345)["bypass_actors"]
        == V_CREATE["bypass_actors"]
    )


def test_allow_release_app_refuses_a_ruleset_other_than_v_create():
    mod = _load("allow_release_app", "scripts/allow_release_app.py")
    import pytest

    with pytest.raises(SystemExit):
        mod.check_target({**V_CREATE, "name": "v"})
    with pytest.raises(SystemExit):
        mod.check_target({**V_CREATE, "rules": [{"type": "deletion"}]})


# ---- (c) scheduled merge audit -------------------------------------------------------------------


def _audit():
    return _load("audit_merges", "scripts/audit_merges.py")


def test_audit_clean_when_gates_met():
    a = _audit()
    ok = a.problems(sensitive=True, verdict="success", security="success", runs=["success"])
    assert ok == []
    assert (
        a.problems(sensitive=False, verdict="", security="none", runs=["success", "skipped"]) == []
    )


def test_audit_flags_risky_merge_without_verdict_or_security():
    a = _audit()
    p = a.problems(sensitive=True, verdict="", security="none", runs=["success"])
    assert any("trazo/verdict" in x for x in p) and any("trazo/security" in x for x in p)


def test_audit_flags_red_or_pending_checks_and_recorded_objection():
    a = _audit()
    assert a.problems(sensitive=False, verdict="", security="none", runs=["failure"])
    assert a.problems(sensitive=False, verdict="", security="none", runs=[])
    assert a.problems(sensitive=False, verdict="failure", security="none", runs=["success"])


def test_audit_audit_collects_only_flagged_prs_and_skips_those_already_reported():
    a = _audit()
    prs = [
        {"number": 1, "head": {"sha": "a" * 40}, "title": "t1"},
        {"number": 2, "head": {"sha": "b" * 40}, "title": "t2"},
        {"number": 3, "head": {"sha": "c" * 40}, "title": "t3"},
    ]

    def facts(pr):
        if pr["number"] == 1:
            return dict(sensitive=True, verdict="success", security="success", runs=["success"])
        return dict(sensitive=True, verdict="", security="none", runs=["success"])

    found = a.audit(prs, facts, already_reported={3})
    assert [n for n, _ in found] == [2]


def test_audit_issue_body_names_each_pr_and_reason():
    a = _audit()
    title, body = a.issue_text([(2, ["trazo/verdict is missing"])], "2026-11-27")
    assert title.startswith("Merge audit:")
    assert "#2 " in body and "trazo/verdict is missing" in body
    assert "Posted by" in body


def test_audit_workflow_is_scheduled_read_only_except_issues():
    wf = _wf(ROOT / ".github/workflows/merge-audit.yml")
    triggers = wf.get("on", wf.get(True))
    assert "schedule" in triggers and "workflow_dispatch" in triggers
    perms = wf["jobs"]["audit"]["permissions"]
    assert perms["issues"] == "write" and perms["contents"] == "read"
    assert "pull-requests" in perms and perms["pull-requests"] == "read"
    assert "scripts/audit_merges.py" in (ROOT / ".github/workflows/merge-audit.yml").read_text()
