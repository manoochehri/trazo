"""Issue #333: the front door merges by dispatching the gated owner-merge workflow.

`gh pr merge` stays denied. `gh workflow run` is not a settings.json prefix deny (a prefix list is
bypassed by flags before the name, a workflow ID, a path or a display name, and by a workflow added
later); engineer_bash_guard.py enforces an ALLOWLIST instead: exactly
`gh workflow run owner-merge.yml -f pr=<digits>`. The hook is exercised the way the harness runs it.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = ROOT / "src/adapters/claude/settings.json"
HOOKS = ROOT / "src/overlay/hooks"
SH = shutil.which("sh") or "/bin/sh"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    hooks = tmp_path / ".trazo" / "hooks"
    hooks.mkdir(parents=True)
    for script in HOOKS.glob("*.py"):
        shutil.copy(script, hooks / script.name)
    (tmp_path / ".claude").mkdir()
    shutil.copy(SETTINGS, tmp_path / ".claude" / "settings.json")
    return tmp_path


def _blocked(project: Path, command: str, agent: str | None = None) -> bool:
    entries = json.loads(SETTINGS.read_text(encoding="utf-8"))["hooks"]["PreToolUse"]
    hooks = [h["command"] for e in entries if e["matcher"] == "Bash" for h in e["hooks"]]
    payload: dict = {"tool_name": "Bash", "tool_input": {"command": command}}
    if agent:
        payload["agent_type"] = agent
    codes = [
        subprocess.run(  # noqa: S603 - fixed argv; hook text comes from the repo's settings.json
            [SH, "-c", hook],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env={"CLAUDE_PROJECT_DIR": str(project), "PATH": "/usr/bin:/bin:/usr/local/bin"},
            check=False,
        ).returncode
        for hook in hooks
    ]
    return 2 in codes


ALLOWED = [
    "gh workflow run owner-merge.yml -f pr=123",
    "gh workflow run owner-merge.yml --field pr=7",
    "gh workflow list",
    "gh workflow view owner-merge.yml",
    "gh run list --workflow owner-merge.yml",
]

DENIED = [
    "gh pr merge 12 --squash",
    "gh workflow run drive.yml",
    "gh workflow run drive.yml -f mode=x",
    "gh workflow run status.yml",  # a workflow added later is not dispatchable
    "gh workflow run owner-merge.yml -f pr=123 --ref my-branch",  # a branch's edited copy
    "gh workflow run owner-merge.yml --ref my-branch -f pr=123",
    "gh workflow run owner-merge.yml -r my-branch -f pr=123",
    "gh workflow run --ref my-branch owner-merge.yml -f pr=123",  # flags before the name
    "gh workflow run -f pr=123 owner-merge.yml",
    "gh workflow run owner-merge.yml -f pr=123 -f extra=1",
    "gh workflow run owner-merge.yml -f pr=abc",
    "gh workflow run owner-merge.yml",
    "gh workflow run 1234567",  # workflow ID
    "gh workflow run .github/workflows/owner-merge.yml -f pr=1",  # path form
    "gh workflow run .github/workflows/drive.yml",
    "gh workflow run Deploy",  # display name
    "gh workflow run owner-merge -f pr=1",
    "gh workflow run Owner-Merge.yml -f pr=1",  # case
    "gh workflow run owner-merge.yml -f pr=1 -R other/repo",
    "gh -R other/repo workflow run owner-merge.yml -f pr=1",
    "gh workflow enable drive.yml",
    "gh workflow disable ci.yml",
    "gh api repos/o/r/actions/workflows/drive.yml/dispatches -f ref=main",
    "gh api repos/o/r/dispatches -f event_type=x",
    "gh api repos/o/r/actions/workflows/12/dispatches",
    "gh api repos/o/r/actions/workflows/12",
    "bash -c 'gh workflow run drive.yml'",
    "GH_REPO=other/repo gh workflow run owner-merge.yml -f pr=1",  # another repo's workflow
    "GH_HOST=example.com gh workflow run owner-merge.yml -f pr=1",
    "env GH_REPO=other/repo gh workflow run owner-merge.yml -f pr=1",
    "env -i gh workflow run owner-merge.yml -f pr=1",
    "gh run rerun 123",  # reruns a workflow run
    "gh run rerun 123 --failed",
]


@pytest.mark.parametrize("agent", [None, "engineer", "senior-engineer"])
@pytest.mark.parametrize("command", ALLOWED)
def test_only_owner_merge_dispatch_and_read_only_workflow_commands_are_allowed(
    project, command, agent
):
    assert not _blocked(project, command, agent)


@pytest.mark.parametrize("agent", [None, "engineer"])
@pytest.mark.parametrize("command", DENIED)
def test_every_other_merge_or_dispatch_route_is_denied(project, command, agent):
    assert _blocked(project, command, agent)


def test_settings_keep_the_gh_pr_merge_deny_and_drop_the_broad_workflow_deny():
    deny = json.loads(SETTINGS.read_text(encoding="utf-8"))["permissions"]["deny"]
    assert "Bash(gh pr merge *)" in deny
    assert not [r for r in deny if "gh workflow" in r], "the guard allowlist replaces the prefixes"


def test_rules_front_door_says_it_merges_through_owner_merge():
    text = (ROOT / "src/overlay/rules.md").read_text(encoding="utf-8")
    front = text.split("## Front door", 1)[1].split("\n## ", 1)[0]
    flat = " ".join(front.split())
    assert "owner-merge.yml" in flat
    assert "engineer and PM never merge" in flat


def test_owner_merge_copies_identical_and_say_agents_may_dispatch():
    a = (ROOT / ".github/workflows/owner-merge.yml").read_bytes()
    b = (ROOT / "src/harness/.github/workflows/owner-merge.yml").read_bytes()
    assert a == b
    assert b"agents may dispatch" in a.lower()
