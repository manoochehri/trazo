"""Issue #321: one owner-triggered merge path for any pull request.

An agent session may not run `gh pr merge` (settings.json denies it) and drive.yml merges only
issue-* branches that touch no owner-protected path, so "merge it" had no path. owner-merge.yml is
that path. These tests read the workflow and also run its merge script against a fake `gh`, so the
gates (verdict, CI, security on protected paths, head pinning) are exercised, not just described.

UNVERIFIED on a live run: that github.token can squash-merge a pull request that edits files under
.github/workflows/. The workflow header says so.
"""

import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github/workflows/owner-merge.yml"
SHIPPED = REPO_ROOT / "src/harness/.github/workflows/owner-merge.yml"
SHA = "a" * 40


def _load() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _job() -> dict:
    return _load()["jobs"]["merge"]


def _script() -> str:
    (step,) = [s for s in _job()["steps"] if "run" in s]
    return step["run"]


def test_it_runs_only_when_the_owner_dispatches_it_from_the_default_branch():
    wf = _load()
    triggers = wf.get("on", wf.get(True))
    assert set(triggers) == {"workflow_dispatch"}
    assert triggers["workflow_dispatch"]["inputs"]["pr"]["required"] is True
    condition = " ".join(str(_job()["if"]).split())
    assert "github.actor == github.repository_owner" in condition
    assert "github.event.repository.default_branch" in condition


def test_the_pull_request_number_never_reaches_the_shell_as_text():
    """An input interpolated into `run:` is shell injection; it must arrive through env."""
    for step in _job()["steps"]:
        assert "${{" not in str(step.get("run", "")), step.get("name")
    (step,) = [s for s in _job()["steps"] if "run" in s]
    assert step["env"]["PR"] == "${{ inputs.pr }}"


def test_it_checks_out_the_default_branch_without_credentials_and_with_pinned_actions():
    checkout = _job()["steps"][0]
    assert checkout["with"]["ref"] == "${{ github.event.repository.default_branch }}"
    assert checkout["with"]["persist-credentials"] is False
    for step in _job()["steps"]:
        if "uses" in step:
            assert re.fullmatch(r"[\w./-]+@[0-9a-f]{40}", step["uses"]), step["uses"]


def test_permissions_are_the_least_that_can_merge():
    wf = _load()
    assert wf["permissions"] == {"contents": "read"}
    assert _job()["permissions"] == {
        "contents": "write",
        "pull-requests": "write",
        "statuses": "read",
        "checks": "read",
        "issues": "read",
    }


def test_the_script_fails_closed_and_pins_the_head_it_checked():
    script = _script()
    assert "set -euo pipefail" in script
    assert '--match-head-commit "$sha"' in script
    assert "scripts/report_verdict.py --sensitive .github/CODEOWNERS" in script
    for gate in ("trazo/verdict", "trazo/security", "check-runs"):
        assert gate in script


def test_the_shipped_copy_is_the_one_this_repo_runs():
    assert SHIPPED.read_text(encoding="utf-8") == WORKFLOW.read_text(encoding="utf-8")


# ---- the merge script against a fake gh ---------------------------------------------------------

FAKE_GH = r"""#!{python}
import json, os, sys

args = sys.argv[1:]
log = os.environ["FAKE_LOG"]
env = os.environ


def say(text):
    sys.stdout.write(text if text.endswith("\n") or not text else text + "\n")


if args[:2] == ["pr", "view"]:
    say("\t".join([env.get("FAKE_STATE", "OPEN"), env.get("FAKE_DRAFT", "false"),
                   env.get("FAKE_CROSS", "false"), env.get("FAKE_BASE", "main"),
                   env.get("FAKE_SHA", "{sha}")]))
elif args[:2] == ["pr", "merge"]:
    open(log, "a").write(" ".join(args) + "\n")
elif args[0] == "api" and any(a.endswith("/files") for a in args):
    for name in env["FAKE_FILES"].split(","):
        say(name + "\t")
elif args[0] == "api" and any("/commits/" in a and a.endswith("/check-runs") for a in args):
    for run in env.get("FAKE_RUNS", "success,skipped").split(","):
        if run:
            say(run)
elif args[0] == "api" and any("/commits/" in a and "/status" in a for a in args):
    statuses = []
    if env.get("FAKE_VERDICT"):
        statuses.append({{"context": "trazo/verdict", "state": env["FAKE_VERDICT"]}})
    if env.get("FAKE_SECURITY"):
        statuses.append({{"context": "trazo/security", "state": env["FAKE_SECURITY"]}})
    say(json.dumps({{"statuses": statuses}}))
elif args[0] == "api":
    say(str(len(env["FAKE_FILES"].split(","))))
else:
    sys.stderr.write("fake gh: unexpected " + " ".join(args) + "\n")
    sys.exit(3)
"""


def _run(
    tmp_path: Path, pr: str = "7", **fake: str
) -> tuple[subprocess.CompletedProcess, list[str]]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    gh = bin_dir / "gh"
    gh.write_text(FAKE_GH.format(python=sys.executable, sha=SHA), encoding="utf-8")
    gh.chmod(gh.stat().st_mode | stat.S_IXUSR)
    log = tmp_path / "gh.log"
    env = {
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "FAKE_LOG": str(log),
        "GITHUB_REPOSITORY": "o/r",
        "DEFAULT_BRANCH": "main",
        "PR": pr,
        "FAKE_FILES": "docs/notes.md",
        "FAKE_VERDICT": "success",
        **fake,
    }
    result = subprocess.run(  # noqa: S603 - the script is this repo's own workflow step
        ["/bin/bash", "-c", _script()],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    merges = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    return result, merges


def test_a_green_ordinary_pull_request_is_merged_at_the_head_that_was_checked(tmp_path):
    result, merges = _run(tmp_path)
    assert result.returncode == 0, result.stderr
    assert merges == [f"pr merge 7 --squash --match-head-commit {SHA}"]


@pytest.mark.parametrize(
    "fake",
    [
        {"FAKE_VERDICT": ""},
        {"FAKE_VERDICT": "failure"},
        {"FAKE_VERDICT": "pending"},
        {"FAKE_RUNS": "success,failure"},
        {"FAKE_RUNS": "success,pending"},
        {"FAKE_RUNS": ""},
        {"FAKE_STATE": "MERGED"},
        {"FAKE_STATE": "CLOSED"},
        {"FAKE_DRAFT": "true"},
        {"FAKE_CROSS": "true"},
        {"FAKE_BASE": "other"},
        {"FAKE_SHA": "not-a-sha"},
    ],
)
def test_it_refuses_unless_every_gate_passed(tmp_path, fake):
    result, merges = _run(tmp_path, **fake)
    assert result.returncode != 0
    assert merges == []


@pytest.mark.parametrize("pr", ["", "abc", "7; rm -rf .", "7 --admin", "$(id)", "-1", "07x"])
def test_a_pull_request_value_that_is_not_a_number_is_refused(tmp_path, pr):
    result, merges = _run(tmp_path, pr=pr)
    assert result.returncode != 0
    assert merges == []


def test_a_protected_path_needs_a_passing_security_status_as_well(tmp_path):
    protected = {"FAKE_FILES": ".github/workflows/ci.yml"}
    for security in ("", "pending", "failure"):
        result, merges = _run(tmp_path, FAKE_SECURITY=security, **protected)
        assert result.returncode != 0 and merges == [], security
    result, merges = _run(tmp_path, FAKE_SECURITY="success", **protected)
    assert result.returncode == 0, result.stderr
    assert merges == [f"pr merge 7 --squash --match-head-commit {SHA}"]


def test_the_fake_statuses_are_valid_json_for_the_script(tmp_path):
    """Guards the test double: a broken fake would pass every refusal test for the wrong reason."""
    result, merges = _run(tmp_path, FAKE_SECURITY="success")
    assert result.returncode == 0 and len(merges) == 1
    assert json.loads('{"statuses": []}') == {"statuses": []}
