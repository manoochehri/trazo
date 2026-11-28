"""The drive's stuck job and the agent-denial summary (#399).

The stuck job has no checkout, so gh cannot infer the repository from a git remote and fails with
`fatal: not a git repository`. These tests run the job's script against a fake gh that behaves the
same way, and check that every job calling gh either checks out the repository or names it.
UNVERIFIED on a live run: that the denial summary lists what the live action writes; the shape of
the execution file is taken from the pinned action's source (permission_denials on the result).
"""

import importlib.util
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github/workflows/drive.yml"
SHIPPED = REPO_ROOT / "src/harness/.github/workflows/drive.yml"

# Like the real gh outside a repository: with no GH_REPO and no --repo, it asks git and fails.
FAKE_GH = r"""#!{python}
import os, sys
args = sys.argv[1:]
repo = os.environ.get("GH_REPO", "")
if "--repo" in args or "-R" in args:
    repo = "flag"
if not repo:
    sys.stderr.write("failed to run git: fatal: not a git repository\n")
    sys.exit(1)
open(os.environ["FAKE_LOG"], "a").write(repo + " " + " ".join(args[:2]) + "\n")
"""


def _jobs():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]


def test_the_stuck_job_labels_the_issue_without_a_checkout(tmp_path):
    (step,) = [s for s in _jobs()["stuck"]["steps"] if "run" in s]
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(FAKE_GH.format(python=sys.executable), encoding="utf-8")
    gh.chmod(gh.stat().st_mode | stat.S_IXUSR)
    log = tmp_path / "gh.log"
    work = tmp_path / "work"  # not a git repository, like the job's empty workspace
    work.mkdir()
    env = {"PATH": f"{bin_dir}:{os.environ['PATH']}", "FAKE_LOG": str(log), "ISSUE": "400"}
    for key, value in step.get("env", {}).items():
        env[key] = {
            "${{ github.token }}": "t",
            "${{ needs.work.outputs.issue }}": "400",
            "${{ github.repository }}": "o/r",
        }.get(value, "x")
    result = subprocess.run(  # noqa: S603 - the script is this repo's own workflow step
        ["/bin/bash", "-c", step["run"]], cwd=work, env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert log.read_text(encoding="utf-8").splitlines() == ["o/r issue edit", "o/r issue comment"]


def test_every_job_that_calls_gh_has_a_checkout_or_names_the_repository():
    for name, job in _jobs().items():
        steps = job["steps"]
        if not any("gh " in str(s.get("run", "")) for s in steps):
            continue
        checkout = any("actions/checkout" in str(s.get("uses", "")) for s in steps)
        named = "GH_REPO" in job.get("env", {}) or all(
            "GH_REPO" in s.get("env", {}) for s in steps if "gh " in str(s.get("run", ""))
        )
        assert checkout or named, f"job {name} runs gh with no checkout and no GH_REPO"


def test_the_shipped_copy_matches():
    assert SHIPPED.read_text(encoding="utf-8") == WORKFLOW.read_text(encoding="utf-8")


# ---- the denial summary --------------------------------------------------------------------------


def _guard():
    spec = importlib.util.spec_from_file_location("dg", REPO_ROOT / "scripts/drive_guard.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_denials_names_the_tool_and_file_but_never_a_command_or_content():
    messages = [
        {"type": "system"},
        {
            "type": "result",
            "permission_denials": [
                {"tool_name": "Bash", "tool_input": {"command": "echo $ANTHROPIC_API_KEY"}},
                {"tool_name": "Write", "tool_input": {"file_path": "x/y.md", "content": "SECRET"}},
            ],
        },
    ]
    out = _guard().denials(json.dumps(messages))
    assert "Bash" in out and "Write" in out and "x/y.md" in out
    assert "ANTHROPIC" not in out and "SECRET" not in out


def test_denials_says_none_for_a_clean_or_unreadable_file():
    assert "none" in _guard().denials(json.dumps([{"type": "result"}])).lower()
    assert "unreadable" in _guard().denials("not json").lower()
