"""#291: a workflow_run report job from the default branch sets trazo/verdict as the reviewer App.

review.yml stays on pull_request with no App key. report.yml runs from the default branch
(https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_run:
"will only trigger a workflow run if the workflow file exists on the default branch";
GITHUB_REF is the default branch), so the `trazo-apps` main-only rule matches
(https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments).
"""

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
HARNESS = REPO_ROOT / "src" / "harness" / ".github" / "workflows"
TOKEN_ACTION = "actions/create-github-app-token@f418cff399f7aef4c2f0ad47e25ca7a6abbdd6fc"  # noqa: S105
PR_CONTROLLED = re.compile(
    r"github\.event\.(pull_request|workflow_run\.(head_branch|display_title|pull_requests|head_commit|"
    r"head_repository\.(?!full_name)))|github\.head_ref"
)


def text(name="report.yml"):
    return (WORKFLOWS / name).read_text()


def load(name="report.yml"):
    return yaml.safe_load(text(name))


def triggers(wf):
    return wf.get("on") or wf.get(True)


def report_job():
    return load()["jobs"]["report"]


def test_report_triggers_on_workflow_run_of_review_only():
    t = triggers(load())
    assert set(t) == {"workflow_run"}
    assert t["workflow_run"]["workflows"] == ["review"]
    assert t["workflow_run"]["types"] == ["completed"]


def test_report_declares_the_main_only_environment_and_mints_the_reviewer_token():
    job = report_job()
    assert job["environment"] == "trazo-apps"
    mints = [s for s in job["steps"] if str(s.get("uses", "")).startswith(TOKEN_ACTION)]
    assert len(mints) == 1
    w = mints[0]["with"]
    assert "REVIEWER_APP_ID" in str(w) and "REVIEWER_APP_PRIVATE_KEY" in str(w)
    assert "BUILDER" not in str(w)
    perms = {k: v for k, v in w.items() if k.startswith("permission-")}
    assert perms == {"permission-statuses": "write"}
    assert w["repositories"] == "${{ github.event.repository.name }}"


def test_every_action_in_report_is_pinned_to_a_commit():
    for step in report_job()["steps"]:
        if "uses" in step:
            assert re.fullmatch(r"[\w./-]+@[0-9a-f]{40}", step["uses"]), step["uses"]


def test_no_pr_controlled_expression_reaches_a_shell_or_a_ref():
    for expr in re.findall(r"\$\{\{(.*?)\}\}", text()):
        assert not PR_CONTROLLED.search(expr), expr
    for step in report_job()["steps"]:
        assert "${{" not in str(step.get("run", "")), "expression interpolated into a shell script"


def test_report_never_checks_out_or_executes_pr_code():
    job = report_job()
    checkouts = [s for s in job["steps"] if str(s.get("uses", "")).startswith("actions/checkout@")]
    assert len(checkouts) == 1
    w = checkouts[0].get("with", {})
    assert "ref" not in w and "repository" not in w  # the default branch only
    assert w.get("persist-credentials") is False
    assert "reviewed-head" not in text()
    assert "git -C" not in text()


def test_head_sha_comes_from_the_event_payload():
    t = text()
    assert "github.event.workflow_run.head_sha" in t
    assert "github.event.workflow_run.id" in t
    assert "github.event.workflow_run.run_attempt" in t


def test_forks_and_other_events_are_not_acted_on():
    cond = str(report_job()["if"])
    assert "github.event.workflow_run.event == 'pull_request'" in cond
    assert "github.event.workflow_run.head_repository.full_name == github.repository" in cond
    assert "vars.AUTO_REVIEW_ENABLED == 'true'" in cond


def test_workflow_token_is_read_only_and_the_app_token_is_the_only_writer():
    job = report_job()
    assert job["permissions"] == {"contents": "read", "pull-requests": "read", "actions": "read"}
    posts = [s for s in job["steps"] if "-X POST" in str(s.get("run", ""))]
    assert len(posts) == 1
    assert ".outputs.token" in posts[0]["env"]["GH_TOKEN"]
    for s in job["steps"]:
        if s not in posts and "env" in s:
            assert ".outputs.token" not in str(s["env"].get("GH_TOKEN", ""))


def test_the_report_sets_only_trazo_verdict_from_the_decision_script():
    t = text()
    assert t.count("context=trazo/verdict") == 1
    assert "trazo/security" not in t
    assert "state=pending" not in t and "state=success" not in t
    assert "python3 scripts/report_verdict.py" in t
    assert "set -o pipefail" in t


def test_report_keeps_the_head_bound_rules_of_adr_0023_and_0020():
    t = text()
    assert "actions/runs/${RUN_ID}/attempts/${RUN_ATTEMPT}/jobs" in t
    assert 'select(.name == "review" and .head_sha == env.HEAD_SHA)' in t
    assert "REVIEW_STARTED_AT" in t
    assert "pulls/${PR_NUMBER}/reviews?per_page=100" in t
    assert "BOT_LOGIN: github-actions[bot]" in t
    assert "--sensitive .github/CODEOWNERS" in t
    assert "moved" in t  # a head that moved since the review is never marked


def test_terminal_verdict_skip_requires_the_current_evidence_digest():
    review = text("review.yml")
    assert "sha256sum" in review
    assert "evidence" in review
    assert '"$state" == "success" || "$state" == "failure"' in review
    assert "current evidence" in review.lower()
    assert "github.event.pull_request.body" in review
    assert "upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9" in review


def test_report_never_deletes_a_status_or_touches_the_security_context():
    report = text()
    assert "-X DELETE" not in report
    assert "trazo/security" not in report


def test_status_binding_is_explicit_for_both_independent_contexts():
    reviewer = (REPO_ROOT / "src/overlay/roles/reviewer.md").read_text()
    security = (REPO_ROOT / "src/overlay/roles/security.md").read_text()
    for role in (reviewer, security):
        assert "evidence=<digest>" in role
        assert "printf '%s' \"$body\" | sha256sum" in role
    assert "context=trazo/verdict" in reviewer
    assert "context=trazo/security" in security
    assert "context=trazo/security" not in reviewer
    assert "context=trazo/verdict" not in security


def test_report_skips_quietly_when_the_gate_or_review_did_not_run():
    t = text()
    assert '"skipped"' in t
    assert "no verdict" in t


def test_a_single_path_sets_trazo_verdict_and_review_yml_has_no_key_or_status_write():
    review = text("review.yml")
    assert "statuses: write" not in review
    assert "context=trazo/verdict" not in review
    assert "-X POST" not in review
    assert "APP_PRIVATE_KEY" not in review and "create-github-app-token" not in review
    wf = load("review.yml")
    assert set(wf["jobs"]) == {"gate", "review"}
    assert not any("environment" in j for j in wf["jobs"].values())
    for path in WORKFLOWS.glob("*.yml"):
        if path.name != "report.yml":
            assert "context=trazo/verdict" not in path.read_text(), path.name


def test_key_is_read_only_by_the_mint_step():
    for step in report_job()["steps"]:
        if "APP_PRIVATE_KEY" in yaml.safe_dump(step):
            assert str(step["uses"]).startswith(TOKEN_ACTION)


def test_host_copies_are_in_sync():
    for name in ("report.yml", "review.yml"):
        assert (HARNESS / name).read_bytes() == (WORKFLOWS / name).read_bytes(), name


def test_decide_step_writes_its_output_once_per_path_and_fails_closed_on_classification():
    t = text()
    assert "finish()" in t
    assert t.count('>> "$GITHUB_OUTPUT"') == 2  # finish() and the single decided write
    assert 'SENSITIVE="$sensitive"' in t
    assert "sensitive=true) sensitive=true" in t and "sensitive=false) sensitive=false" in t
    assert "could not be classified" in t
    assert "automatic review did not finish" in t
    assert 'REVIEW_RESULT" != "success"' in t


def test_classification_reads_fixed_shas_through_the_compare_endpoint():
    t = text()
    assert "compare/${BASE_SHA}...${HEAD_SHA}" in t
    assert "pulls/${PR_NUMBER}/files" not in t


def test_only_pull_requests_against_the_default_branch_get_a_verdict():
    # A commit status is shared by every PR with that head, so a verdict earned against another
    # base would show green on a PR into the default branch (security review of #294).
    t = text()
    step = [s for s in report_job()["steps"] if s.get("id") == "decide"][0]
    assert step["env"]["DEFAULT_BRANCH"] == "${{ github.event.repository.default_branch }}"
    assert ".base.ref == env.DEFAULT_BRANCH" in t
    assert '"$DEFAULT_BRANCH"' not in t.replace("select(", "")  # never spliced into jq text


def test_no_claim_that_report_is_the_only_writer_until_212_is_pinned():
    for path in (
        REPO_ROOT / ".github" / "CODEOWNERS",
        REPO_ROOT / ".trazo/project/adr/0028-report-job-sets-verdict-as-reviewer-app.md",
    ):
        assert "only path that sets trazo/verdict" not in path.read_text(), path.name
    adr = (
        REPO_ROOT / ".trazo/project/adr/0028-report-job-sets-verdict-as-reviewer-app.md"
    ).read_text()
    assert "integration_id" in adr and "BOT_LOGIN" in adr
    assert "default branch" in adr and "gate" in adr.lower()


def _gate_if():
    return str(load("review.yml")["jobs"]["gate"]["if"])


def test_gate_only_reviews_pull_requests_into_the_default_branch():
    # A re-run keeps the original event payload, so a review started against another base must be
    # gated out, or a retarget to the default branch would turn it into a verdict (#294 review).
    cond = _gate_if()
    assert "github.event.pull_request.base.ref == github.event.repository.default_branch" in cond


def test_a_retarget_starts_a_fresh_review_and_other_edits_do_not():
    wf = load("review.yml")
    types = triggers(wf)["pull_request"]["types"]
    assert "edited" in types
    cond = _gate_if()
    # Base or body edits start fresh review; title-only edits do not change the evidence and cannot
    # cancel a review in progress or be used to loop.
    assert (
        "github.event.action != 'edited' || github.event.changes.base != null || "
        "github.event.changes.body != null"
    ) in cond
    # the job that holds the cancel-in-progress group is behind the gate
    assert load("review.yml")["jobs"]["review"]["needs"] == "gate"
    assert "needs.gate.outputs.skip == 'false'" in str(load("review.yml")["jobs"]["review"]["if"])


def test_adr_0028_does_not_claim_a_verdict_cannot_come_from_another_base():
    adr = (
        REPO_ROOT / ".trazo/project/adr/0028-report-job-sets-verdict-as-reviewer-app.md"
    ).read_text()
    assert "can only come from a default-base review run" not in adr
    assert "retarget" in adr and "edited" in adr


# --- run the real workflow steps against a stub `gh` (issue #359) ---
import hashlib  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import subprocess  # noqa: E402
import zipfile  # noqa: E402

APP_SLUG = "trazo-reviewer"
SHA = "a" * 40
BODY = "PR evidence body"
DIGEST = hashlib.sha256(BODY.encode()).hexdigest()

# A fake `gh`: POSTs are logged; reads return the first fixture whose key is in the URL, with the
# call's own `-q` jq filter applied, so the workflow's real filters run.
STUB = r"""#!/usr/bin/env python3
import json, os, subprocess, sys
args = sys.argv[1:]
d = os.environ["STUB_DIR"]
if "-X" in args and "POST" in args:
    with open(os.path.join(d, "posts.log"), "a") as f:
        f.write(json.dumps(args) + "\n")
    sys.exit(0)
url = next(a for a in args[1:] if a.startswith("repos/"))
q = args[args.index("-q") + 1] if "-q" in args else None
fixtures = json.load(open(os.path.join(d, "fixtures.json")))
key = next((k for k in fixtures if k in url), None)
if key is None:
    sys.exit(1)
if key == "/zip":
    sys.stdout.buffer.write(open(os.path.join(d, "artifact-source.zip"), "rb").read())
    sys.exit(0)
val = fixtures[key]
if q is None:
    print(json.dumps(val))
else:
    out = subprocess.run(["jq", "-r", q], input=json.dumps(val), capture_output=True, text=True)
    if out.returncode:
        sys.exit(1)
    sys.stdout.write(out.stdout)
"""


def step_script(name):
    steps = load()["jobs"]["report"]["steps"]
    return next(s for s in steps if s.get("name", "").startswith(name))["run"]


def stub_env(tmp_path, fixtures):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    gh = bindir / "gh"
    gh.write_text(STUB)
    gh.chmod(0o755)
    (tmp_path / "fixtures.json").write_text(json.dumps(fixtures))
    with zipfile.ZipFile(tmp_path / "artifact-source.zip", "w") as z:
        z.writestr("evidence-digest", DIGEST + "\n")
    (tmp_path / "out").write_text("")
    return {
        **os.environ,
        "PATH": f"{bindir}:{os.environ['PATH']}",
        "STUB_DIR": str(tmp_path),
        "GITHUB_OUTPUT": str(tmp_path / "out"),
        "RUNNER_TEMP": str(tmp_path),
        "GITHUB_REPOSITORY": "o/r",
        "GITHUB_SERVER_URL": "https://github.com",
        "GITHUB_RUN_ID": "9",
    }


def run_bash(script, env):
    return subprocess.run(  # noqa: S603
        ["/bin/bash", "-c", script], env=env, cwd=REPO_ROOT, capture_output=True, text=True
    )


def test_decide_step_emits_the_digest_on_the_real_success_path(tmp_path):
    started = "2026-10-13T10:04:00Z"
    fixtures = {
        "/commits/": [
            {
                "state": "open",
                "base": {"ref": "main"},
                "head": {"sha": SHA, "repo": {"full_name": "o/r"}},
                "number": 5,
            }
        ],
        "/pulls/5/reviews": [
            {
                "id": 1,
                "body": f"merge\n\nReviewed-Head: {SHA}",
                "commit_id": SHA,
                "submitted_at": "2026-10-13T10:05:00Z",
                "user": {"login": "github-actions[bot]"},
            }
        ],
        "/pulls/5": {
            "head": {"sha": SHA},
            "base": {"sha": "b" * 40},
            "changed_files": 1,
            "body": BODY,
        },
        "/zip": "",
        "/artifacts": {
            "artifacts": [
                {"name": "review-evidence", "id": 7, "created_at": "2026-10-13T10:01:00Z"},
            ]
        },
        "/attempts/": {
            "jobs": [
                {"name": "gate", "conclusion": "success", "head_sha": SHA, "started_at": started},
                {"name": "review", "conclusion": "success", "head_sha": SHA, "started_at": started},
            ]
        },
        "/compare/": {"files": [{"filename": "README.md"}]},
    }
    env = stub_env(tmp_path, fixtures)
    env.update(
        HEAD_SHA=SHA,
        RUN_ID="1",
        RUN_ATTEMPT="1",
        BOT_LOGIN="github-actions[bot]",
        DEFAULT_BRANCH="main",
    )
    r = run_bash(step_script("decide"), env)
    assert r.returncode == 0, r.stderr
    lines = (tmp_path / "out").read_text().splitlines()
    assert "state=success" in lines, lines
    assert f"evidence={DIGEST}" in lines, lines


def run_set_step(tmp_path, existing, state="success", digest=DIGEST):
    env = stub_env(tmp_path, {"/statuses": [existing] if existing else []})
    env.update(
        APP_SLUG=APP_SLUG,
        SHA=SHA,
        STATE=state,
        REASON="bot review on this head says merge",
        EVIDENCE_DIGEST=digest,
    )
    r = run_bash(step_script("set trazo/verdict"), env)
    assert r.returncode == 0, r.stderr
    log = tmp_path / "posts.log"
    return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []


def status(state, creator, description=""):
    return {
        "context": "trazo/verdict",
        "state": state,
        "creator": {"login": creator},
        "description": description,
    }


def test_set_step_leaves_a_non_app_failure_with_missing_digest_in_place(tmp_path):
    assert run_set_step(tmp_path, status("failure", "manoochehri", "don't merge")) == []


def test_set_step_leaves_a_non_app_failure_with_stale_digest_in_place(tmp_path):
    stale = "e" * 64
    assert run_set_step(tmp_path, status("failure", "manoochehri", f"evidence={stale} no")) == []


def test_set_step_supersedes_a_stale_app_status_and_the_description_fits(tmp_path):
    stale = "e" * 64
    posts = run_set_step(tmp_path, status("failure", f"{APP_SLUG}[bot]", f"evidence={stale} old"))
    assert len(posts) == 1
    args = posts[0]
    desc = next(a for a in args if a.startswith("description=") or a.startswith("evidence="))
    assert len(desc.removeprefix("description=")) <= 140
    assert f"evidence={DIGEST} " in desc
    assert "state=success" in args


def test_set_step_posts_when_there_is_no_status_yet(tmp_path):
    assert len(run_set_step(tmp_path, None)) == 1


def test_report_selects_the_newest_review_evidence_artifact():
    assert "sort_by(.created_at)" in step_script("decide")


def test_set_step_leaves_a_pending_verdict_from_another_writer(tmp_path):
    assert run_set_step(tmp_path, status("pending", "someone-else")) == []
