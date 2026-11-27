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
import sys
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
    assert "scripts/ci_green.sh" in text
    assert text.index("scripts/ci_green.sh") < text.rindex("scripts/release.sh")
    assert "SELF_JOB: release" in text and wf_job_name_is_release()
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


def wf_job_name_is_release():
    job = _wf(RELEASE)["jobs"]["release"]
    return "name" not in job  # check-run name is then the job id, "release"


# ---- review fixes: CI-green step, audit dedup, read-back -----------------------------------------

SHA = "a" * 40
CI_STUB = """#!/usr/bin/env bash
cat "$(dirname "$0")/runs.json"
"""


def _ci(tmp_path, runs):
    stub = tmp_path / "gh"
    stub.write_text(CI_STUB)
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    (tmp_path / "runs.json").write_text(json.dumps({"check_runs": runs}))
    env = {
        **os.environ,
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "GITHUB_REPOSITORY": "o/r",
        "GITHUB_RUN_ID": "555",
        "SELF_JOB": "release",
    }
    cmd = ["bash", str(ROOT / "scripts" / "ci_green.sh"), SHA]
    return subprocess.run(cmd, env=env, capture_output=True, text=True)  # noqa: S603, S607


def _cr(i, name, conclusion, url="https://github.com/o/r/actions/runs/1/job/1"):
    return {"id": i, "name": name, "conclusion": conclusion, "details_url": url}


OWN = "https://github.com/o/r/actions/runs/555/job/9"


def test_ci_green_ignores_the_running_release_job_itself(tmp_path):
    runs = [_cr(1, "test", "success"), _cr(2, "docker", "skipped"), _cr(3, "release", None, OWN)]
    r = _ci(tmp_path, runs)
    assert r.returncode == 0, r.stderr


def test_ci_green_refuses_a_failed_or_pending_other_check(tmp_path):
    assert _ci(tmp_path, [_cr(1, "test", "failure"), _cr(3, "release", None, OWN)]).returncode == 1
    assert _ci(tmp_path, [_cr(1, "test", None), _cr(3, "release", None, OWN)]).returncode == 1


def test_ci_green_only_excuses_the_release_job_of_this_run(tmp_path):
    other = "https://github.com/o/r/actions/runs/444/job/9"
    assert (
        _ci(tmp_path, [_cr(1, "test", "success"), _cr(3, "release", None, other)]).returncode == 1
    )


def test_ci_green_judges_the_latest_run_per_check_name(tmp_path):
    runs = [_cr(1, "test", "failure"), _cr(5, "test", "success"), _cr(3, "release", None, OWN)]
    assert _ci(tmp_path, runs).returncode == 0
    runs = [_cr(1, "test", "success"), _cr(5, "test", "failure"), _cr(3, "release", None, OWN)]
    assert _ci(tmp_path, runs).returncode == 1


def test_ci_green_refuses_when_there_is_nothing_to_judge(tmp_path):
    assert _ci(tmp_path, [_cr(3, "release", None, OWN)]).returncode == 1


def test_audit_dedup_counts_only_issues_the_workflow_opened():
    a = _audit()
    mine = {
        "title": "Merge audit: 1 (d)",
        "body": "- #7 x",
        "user": {"login": "github-actions[bot]"},
    }
    outsider = {"title": "Merge audit: 1 (d)", "body": "- #8 x", "user": {"login": "mallory"}}
    pr = {
        "title": "Merge audit: x",
        "body": "- #9 x",
        "pull_request": {},
        "user": {"login": "github-actions[bot]"},
    }
    assert a.reported_numbers([mine, outsider, pr]) == {7}


def test_verify_requires_other_actors_and_conditions_unchanged():
    mod = _load("allow_release_app", "scripts/allow_release_app.py")
    sent = mod.add_payload(V_CREATE, 12345)
    assert mod.verify({**V_CREATE, **sent}, sent) == []
    dropped_admin = {**V_CREATE, **sent, "bypass_actors": [sent["bypass_actors"][-1]]}
    assert any("bypass_actors" in x for x in mod.verify(dropped_admin, sent))
    moved = {**V_CREATE, **sent, "conditions": {"ref_name": {"include": ["~ALL"], "exclude": []}}}
    assert any("conditions" in x for x in mod.verify(moved, sent))
    no_app = {**V_CREATE, **sent, "bypass_actors": V_CREATE["bypass_actors"]}
    assert mod.verify(no_app, sent)


# ---- stub-gh tests of the GitHub I/O in allow_release_app.py and audit_merges.py -----------------

ROUTER = """#!/usr/bin/env python3
import json, os, sys
d = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[1:]
log = open(os.path.join(d, "calls.log"), "a")
log.write(json.dumps(args) + "\\n")
routes = json.load(open(os.path.join(d, "routes.json")))
if args[:2] == ["issue", "create"]:
    open(os.path.join(d, "issue.json"), "w").write(json.dumps(args))
    print("https://example/issues/1")
    sys.exit(0)
if "-X" in args and args[args.index("-X") + 1] == "PUT":
    path = [a for a in args if a.startswith("repos/")][0]
    body = json.loads(sys.stdin.read())
    routes[path] = {**routes[path], **body}
    json.dump(routes, open(os.path.join(d, "routes.json"), "w"))
    sys.exit(0)
if args[0] == "repo":
    print("o/r")
    sys.exit(0)
path = [a for a in args if a.startswith("repos/")][0]
print(json.dumps(routes[path]))
"""


def _router(tmp_path, routes):
    stub = tmp_path / "gh"
    stub.write_text(ROUTER)
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    (tmp_path / "routes.json").write_text(json.dumps(routes))
    return {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"}


def _run_allow(tmp_path, args, ruleset=V_CREATE):
    routes = {
        "repos/o/r/rulesets": [{"id": 3, "name": "v-create", "target": "tag"}],
        "repos/o/r/rulesets/3": ruleset,
    }
    env = _router(tmp_path, routes)
    cmd = ["python3", str(ROOT / "scripts" / "allow_release_app.py"), *args]
    r = subprocess.run(cmd, env=env, capture_output=True, text=True)  # noqa: S603, S607
    return r, json.loads((tmp_path / "routes.json").read_text())["repos/o/r/rulesets/3"]


def test_allow_release_app_applies_the_documented_actor_shape_through_gh(tmp_path):
    r, live = _run_allow(tmp_path, ["12345"])
    assert r.returncode == 0, r.stderr
    assert live["bypass_actors"] == [
        V_CREATE["bypass_actors"][0],
        {"actor_id": 12345, "actor_type": "Integration", "bypass_mode": "always"},
    ]
    assert live["conditions"] == V_CREATE["conditions"] and live["rules"] == [{"type": "creation"}]


def test_allow_release_app_dry_run_writes_nothing_and_remove_restores(tmp_path):
    r, live = _run_allow(tmp_path, ["12345", "--dry-run"])
    assert r.returncode == 0 and live == V_CREATE
    with_app = {
        **V_CREATE,
        "bypass_actors": V_CREATE["bypass_actors"]
        + [{"actor_id": 12345, "actor_type": "Integration", "bypass_mode": "always"}],
    }
    r, live = _run_allow(tmp_path, ["12345", "--remove"], with_app)
    assert r.returncode == 0, r.stderr
    assert live["bypass_actors"] == V_CREATE["bypass_actors"]


def _audit_routes(files, verdict):
    sha = "d" * 40
    return {
        "repos/o/r/pulls?state=closed&base=main&sort=updated&direction=desc&per_page=100": [
            {"number": 7, "title": "t", "head": {"sha": sha}, "merged_at": "2999-01-01T00:00:00Z"}
        ],
        "repos/o/r/issues?state=all&per_page=100": [],
        "repos/o/r/pulls/7/files": [[{"filename": f} for f in files]],
        f"repos/o/r/commits/{sha}/status?per_page=100": {
            "statuses": [{"context": "trazo/verdict", "state": verdict}] if verdict else []
        },
        f"repos/o/r/commits/{sha}/check-runs": [
            {"check_runs": [{"id": 1, "name": "test", "conclusion": "success"}]}
        ],
    }


def _run_audit(tmp_path, files, verdict):
    env = _router(tmp_path, _audit_routes(files, verdict))
    env.update(GITHUB_REPOSITORY="o/r", DEFAULT_BRANCH="main")
    r = subprocess.run(  # noqa: S603
        [sys.executable, str(ROOT / "scripts" / "audit_merges.py")],
        env=env,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    return r, tmp_path / "issue.json"


def test_audit_main_opens_an_issue_for_a_risky_merge_without_verdict(tmp_path):
    r, issue = _run_audit(tmp_path, ["scripts/report_verdict.py"], "")
    assert r.returncode == 0, r.stderr
    assert "1 failed the gate" in r.stdout
    assert issue.exists() and "#7 " in "".join(json.loads(issue.read_text()))


def test_audit_main_is_quiet_for_a_docs_only_merge(tmp_path):
    r, issue = _run_audit(tmp_path, [".trazo/project/STATUS.md"], "")
    assert r.returncode == 0, r.stderr
    assert "0 failed the gate" in r.stdout and not issue.exists()
