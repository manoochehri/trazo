"""Issue #330: the engineer's Bash cannot merge, set statuses or read secrets, enforced by a hook.

The `settings.json` deny rules match command text as written, so `gh api -X PUT .../merge`,
`gh api -X POST .../statuses/<sha>` and `cat .env` slipped past them. A PreToolUse hook now denies
those routes for every caller except `pm` (which keeps its own allowlist, pm_bash_guard.py).

These tests run every Bash hook command the shipped settings.json declares, the way the harness
does: JSON on stdin, and an exit code 2 from any of them blocks the call.

UNVERIFIED live: the hook input shape (`tool_input.command`, optional `agent_type`) comes from the
Claude Code hooks documentation, as for the other guards. The hook fails closed.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SETTINGS = REPO_ROOT / "src/adapters/claude/settings.json"
HOOKS = REPO_ROOT / "src/overlay/hooks"
HOOKS_DOC = HOOKS / "README.md"
SH = shutil.which("sh") or "/bin/sh"


def _bash_commands() -> list[str]:
    entries = json.loads(SETTINGS.read_text(encoding="utf-8"))["hooks"]["PreToolUse"]
    return [h["command"] for e in entries if e["matcher"] == "Bash" for h in e["hooks"]]


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A host-shaped project: hooks at .trazo/hooks/, settings at .claude/settings.json."""
    hooks = tmp_path / ".trazo" / "hooks"
    hooks.mkdir(parents=True)
    for script in HOOKS.glob("*.py"):
        shutil.copy(script, hooks / script.name)
    (tmp_path / ".claude").mkdir()
    shutil.copy(SETTINGS, tmp_path / ".claude" / "settings.json")
    return tmp_path


def _exit_codes(project_dir: Path, command: str, agent: str | None) -> list[int]:
    payload: dict = {"hook_event_name": "PreToolUse", "tool_name": "Bash"}
    payload["tool_input"] = {"command": command}
    if agent:
        payload["agent_type"] = agent
    return [
        subprocess.run(  # noqa: S603 - fixed argv; the command comes from the repo's settings.json
            [SH, "-c", hook],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env={"CLAUDE_PROJECT_DIR": str(project_dir), "PATH": "/usr/bin:/bin:/usr/local/bin"},
            check=False,
        ).returncode
        for hook in _bash_commands()
    ]


def _blocked(project_dir: Path, command: str, agent: str | None) -> bool:
    return 2 in _exit_codes(project_dir, command, agent)


# Routes the settings.json deny rules miss, plus the denied commands themselves.
DENIED = [
    # merge through the API
    "gh api -X PUT repos/o/r/pulls/5/merge",
    "gh api --method PUT repos/o/r/pulls/5/merge",
    "gh api --method=PUT repos/o/r/pulls/5/merge",
    "gh api -XPUT repos/o/r/pulls/5/merge",
    "gh api repos/o/r/pulls/5/merge -X PUT -f merge_method=squash",
    "gh api repos/o/r/pulls/5/merge -f merge_method=squash",
    "gh -R o/r api -X PUT repos/o/r/pulls/5/merge",
    # commit statuses, including trazo/verdict
    "gh api -X POST repos/o/r/statuses/abc123 -f state=success -f context=trazo/verdict",
    "gh api repos/o/r/statuses/abc123 -f state=success -f context=trazo/verdict",
    "gh api repos/o/r/statuses/abc123 --input status.json",
    # other gh api writes
    "gh api -X DELETE repos/o/r/git/refs/heads/x",
    "gh api -X PATCH repos/o/r/branches/main/protection",
    "gh api -X POST repos/o/r/dispatches -f event_type=x",
    "gh api graphql -f query='mutation { mergePullRequest(input:{}) { clientMutationId } }'",
    "gh api repos/o/r/pulls/5 -H 'X-HTTP-Method-Override: PUT'",
    # chained and wrapped
    "git status && gh api -X PUT repos/o/r/pulls/5/merge",
    "echo hi; gh api -X POST repos/o/r/statuses/abc -f state=success",
    "bash -c 'gh api -X PUT repos/o/r/pulls/5/merge'",
    'sh -c "gh pr merge 5"',
    "env GH_DEBUG=1 gh pr merge 5",
    "eval gh pr merge 5",
    "echo $(gh api -X PUT repos/o/r/pulls/5/merge)",
    # the deny-rule commands, however spelled
    "gh pr merge 5",
    "gh -R o/r pr merge 5 --squash",
    "gh secret set X",
    "gh variable set X --body y",
    "gh workflow run deploy.yml",
    "scripts/put_secret.sh KEY",
    "./scripts/put_secret.sh KEY",
    "bash scripts/put_secret.sh KEY",
    "gh alias set m 'pr merge'",
    "gh auth token",
    # secret reads through Bash
    "cat .env",
    "cat ./.env",
    "cat app/.env",
    "cat .env.local",
    "cat .env.production",
    "less secrets/prod.txt",
    "head -1 config/secrets/x",
    "grep KEY .env",
    "cat < .env",
    "source .env",
    "cat server.pem",
    "cat certs/tls.key",
    "cat ~/.ssh/id_rsa",
    "cat ~/.aws/credentials",
    "cat ~/.netrc",
    "cat ~/.gitconfig",
    "git add .env",
    "bash -c 'cat .env'",
    "cd app && cat .env",
    "echo $(cat .env)",
    "gh pr create --title t --body-file .env",
    # fail closed on what cannot be parsed
    "cat 'unterminated",
    "$CMD pr merge 5",
]

ALLOWED = [
    "git status",
    "git diff origin/main...HEAD",
    "git add src/overlay/hooks/engineer_bash_guard.py tests/test_engineer_bash_guard.py",
    'git commit -m "Closes #330: guard the engineer Bash"',
    'git commit -m "document why gh pr merge and .env are denied"',
    "git push -u origin eng-330",
    "git fetch origin main",
    "git worktree add ../w origin/main",
    "gh pr create --title t --body 'Review rounds: 0'",
    "gh pr create --title t --body 'mentions .env and gh pr merge'",
    "gh pr view 5 --json state",
    "gh pr view 5",
    "gh pr comment 5 --body 'fixed'",
    "gh pr checks 5",
    "gh pr diff 5",
    "gh issue view 330",
    "gh issue list --label bug",
    "gh issue comment 330 --body 'Decided: x'",
    "gh issue edit 330 --add-label needs-pm",
    "gh issue create --title t --body b",
    "gh api repos/o/r/pulls/5",
    "gh api repos/o/r/pulls/5/merge",
    "gh api -X GET repos/o/r/commits/abc/statuses",
    "gh api repos/o/r/issues --paginate --jq '.[].number'",
    "gh api -X GET search/issues -f q=repo:o/r",
    "gh -R o/r pr view 5",
    "uv run pytest tests/test_engineer_bash_guard.py -q",
    "uv run ruff check .",
    "make test",
    "make lint",
    "cat .env.example",
    "cat README.md",
    "ls -la",
    "grep -rn environment src | head -5",
    "python3 -m pytest -q",
    "bash scripts/install.sh --help",
    "echo done",
]


@pytest.mark.parametrize("command", DENIED)
@pytest.mark.parametrize("agent", [None, "engineer", "senior-engineer"])
def test_bypass_route_is_denied_for_the_engineer_and_the_main_session(project, command, agent):
    assert _blocked(project, command, agent), f"{command!r} must be blocked (agent={agent})"


@pytest.mark.parametrize("command", ALLOWED)
@pytest.mark.parametrize("agent", [None, "engineer", "senior-engineer"])
def test_allowed_engineer_commands_still_work(project, command, agent):
    assert not _blocked(project, command, agent), f"{command!r} must be allowed (agent={agent})"


def _run_guard(project: Path, stdin: str) -> int:
    guard = project / ".trazo/hooks/engineer_bash_guard.py"
    return subprocess.run(  # noqa: S603 - fixed argv
        [sys.executable, str(guard), "--skip-agent", "pm"],
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    ).returncode


def test_pm_keeps_its_own_allowlist_and_the_engineer_guard_steps_aside(project):
    """pm stays under pm_bash_guard.py: `gh issue comment` passes, an API write does not."""
    assert not _blocked(project, "gh issue comment 5 --body ok", "pm")
    assert _blocked(project, "gh api -X PUT repos/o/r/pulls/5/merge", "pm")
    payload = {"tool_name": "Bash", "tool_input": {"command": "cat .env"}, "agent_type": "pm"}
    assert _run_guard(project, json.dumps(payload)) == 0, "the engineer guard must not run for pm"


def test_guard_fails_closed(project):
    assert _run_guard(project, "not json") == 2
    assert _run_guard(project, json.dumps({"tool_name": "Bash", "tool_input": {"command": 5}})) == 2
    assert _run_guard(project, json.dumps({"tool_name": "Bash", "tool_input": {}})) == 2
    # the guard derives its lists from settings.json: without them nothing can be trusted
    ok = json.dumps({"tool_name": "Bash", "tool_input": {"command": "git status"}})
    (project / ".claude/settings.json").write_text('{"permissions": {"deny": []}}')
    assert _run_guard(project, ok) == 2
    (project / ".claude/settings.json").unlink()
    assert _run_guard(project, ok) == 2


def test_lists_come_from_settings_json_so_there_is_one_source(project):
    """Adding a deny rule to settings.json is enough to extend the guard."""
    path = project / ".claude/settings.json"
    settings = json.loads(path.read_text())
    settings["permissions"]["deny"] += ["Bash(terraform apply *)", "Read(./**/*.tfstate)"]
    path.write_text(json.dumps(settings))
    assert _blocked(project, "terraform apply -auto-approve", None)
    assert _blocked(project, "cat prod.tfstate", None)
    assert not _blocked(project, "terraform plan", None)


def test_settings_registers_the_guard_on_bash_for_every_caller_but_pm():
    commands = _bash_commands()
    assert any("pm_bash_guard.py" in c and "--agent pm" in c for c in commands)
    (guard,) = [c for c in commands if "engineer_bash_guard.py" in c]
    assert "--skip-agent pm" in guard
    assert guard.rstrip().endswith("|| exit 2"), "a missing script or python3 must block"
    assert (HOOKS / "engineer_bash_guard.py").is_file()


def test_hooks_doc_describes_the_guard_and_its_limits():
    text = HOOKS_DOC.read_text(encoding="utf-8")
    assert "engineer_bash_guard.py" in text
    assert "not a security boundary" in text
    assert "#320" in text, "the guard is a backstop; the non-admin agent token is the real fix"
