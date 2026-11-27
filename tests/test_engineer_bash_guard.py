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
    # security review of #335: flag order, case, release, pushes to the default branch
    "gh pr --repo o/r merge 5",
    "gh pr --repo=o/r merge 5",
    "gh pr merge --squash 5",
    "gh api -X GET graphql -f query=x",
    "gh api GRAPHQL -f query=x",
    "gh api /graphql -f query=x",
    "gh release create v1.0.0",
    "gh release upload v1.0.0 dist.zip",
    "git push origin HEAD:main",
    "git push origin main",
    "git push origin HEAD:refs/heads/main",
    "git push -u origin master",
    "git push origin +main",
    "git push origin :main",
    "git push --force origin main",
    "git -C . push origin main",
    "git push --all",
    "git push --mirror",
    "git -c alias.x='!gh pr merge 5' x",
    "git config alias.m '!gh pr merge 5'",
    # shells, wrappers, keywords and substitutions that hide the command
    "bash -lc 'gh pr merge 5'",
    "bash -xc 'cat .env'",
    "sudo gh pr merge 5",
    "sudo -u root gh pr merge 5",
    "timeout 5 gh pr merge 5",
    "env -u A gh pr merge 5",
    "env -S 'gh pr merge 5'",
    "echo 'gh pr merge 5' | bash",
    "bash <<< 'gh pr merge 5'",
    "{ gh pr merge 5; }",
    "if true; then gh pr merge 5; fi",
    "while true; do gh pr merge 5; done",
    "! gh pr merge 5",
    'echo "$(gh pr merge 5)"',
    'echo "`cat .env`"',
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
    "git push origin eng-330",
    "git push -u origin HEAD",
    "git push origin HEAD:eng-330",
    "git push",
    "git push origin feature/main-fix",
    "git log --oneline -3 main",
    "git commit -m \"$(cat <<'EOF'\nCloses #330: x\n\nbody\nEOF\n)\"",
    "timeout 60 uv run pytest -q",
    "env FOO=1 uv run pytest",
    "env -u FOO make test",
    "bash -lc 'make test'",
    "bash -c 'echo hi'",
    "gh pr comment 5 --body merge",
    "gh pr create --title 'pr merge' --body x",
    "gh pr view merge-fix",
    "gh release view v1.0.0",
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


# Issue #364: the reviewer and security subagents post their own commit status as their roles
# document it (`.trazo/roles/{reviewer,security}.md`): the repo and the head SHA come from
# read-only `gh` substitutions, not literals. The own-status allowance rejected every `$` and so
# never matched, and the call fell through to "gh api is read-only".
SHA40 = "a" * 40
REPO_SUB = "$(gh repo view --json nameWithOwner -q .nameWithOwner)"
SHA_SUB = "$(gh pr view 7 --json headRefOid -q .headRefOid)"
ROLE_CONTEXT = {"reviewer": "trazo/verdict", "security": "trazo/security"}


def _status(endpoint: str, context: str, state: str = "success") -> str:
    return f'gh api -X POST {endpoint} -f state={state} -f context={context} -f description="ok"'


@pytest.mark.parametrize("agent", sorted(ROLE_CONTEXT))
@pytest.mark.parametrize(
    "endpoint",
    [
        f"repos/o/r/statuses/{SHA40}",
        f"repos/{REPO_SUB}/statuses/{SHA40}",
        f"repos/{REPO_SUB}/statuses/{SHA_SUB}",
        f"repos/o/r/statuses/{SHA_SUB}",
    ],
    ids=["literal", "repo-substitution", "documented", "sha-substitution"],
)
def test_reviewer_and_security_may_post_their_own_status(project, agent, endpoint):
    command = _status(endpoint, ROLE_CONTEXT[agent])
    assert not _blocked(project, command, agent), f"{agent}: {command!r} must be allowed"


@pytest.mark.parametrize("agent", sorted(ROLE_CONTEXT))
def test_a_role_may_not_post_another_roles_status_or_another_write(project, agent):
    other = next(c for a, c in ROLE_CONTEXT.items() if a != agent)
    endpoint = f"repos/{REPO_SUB}/statuses/{SHA_SUB}"
    assert _blocked(project, _status(endpoint, other), agent)
    assert _blocked(project, _status(endpoint, "ci/anything"), agent)
    mine = ROLE_CONTEXT[agent]
    for command in [
        "gh api -X PUT repos/o/r/pulls/7/merge",
        _status(f"repos/o/r/statuses/{SHA40}", mine) + " ; gh api -X PUT repos/o/r/pulls/7/merge",
        _status("repos/$(rm -rf /)/statuses/" + SHA40, mine),
        _status(f"repos/{REPO_SUB}/statuses/$(gh pr merge 7)", mine),
        _status(f"repos/{REPO_SUB}/statuses/$(gh pr view 7 --json headRefOid -q .x)", mine),
        _status(f"repos/o/r/statuses/{SHA40}", mine) + " -f target_url=$(cat x)",
        f"gh api -X POST repos/o/r/issues/7/comments -f body=x -f context={mine}",
    ]:
        assert _blocked(project, command, agent), f"{agent}: {command!r} must stay blocked"


@pytest.mark.parametrize("agent", [None, "engineer", "senior-engineer", "skeptic"])
def test_no_other_caller_may_post_a_status(project, agent):
    for context in ROLE_CONTEXT.values():
        for endpoint in (f"repos/o/r/statuses/{SHA40}", f"repos/{REPO_SUB}/statuses/{SHA_SUB}"):
            assert _blocked(project, _status(endpoint, context), agent)


@pytest.mark.parametrize(
    "command",
    [
        "git diff origin/main -- .claude/settings.json",
        "grep -n permissions .claude/settings.json",
        "cat .claude/agents/reviewer.md",
        "ls .claude/commands",
    ],
)
def test_project_claude_directory_is_not_a_secret_path(project, command):
    """`Read(~/.claude/**)` is the home directory's; the project's `.claude/` is repo content."""
    assert not _blocked(project, command, None), f"{command!r} must be allowed"


@pytest.mark.parametrize(
    "command",
    ["cat ~/.claude/settings.json", "cat /Users/me/.claude/projects/x", "cat $HOME/.claude/x"],
)
def test_home_claude_directory_stays_a_secret_path(project, command):
    assert _blocked(project, command, None), f"{command!r} must stay blocked"
