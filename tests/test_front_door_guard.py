"""Issue #319: the front door (main session) does not do engineer work, enforced by a hook.

In a v0.3.1 host the front door edited PR bodies and pushed empty commits to re-run CI instead of
dispatching an engineer. These tests run the exact commands the shipped settings.json declares, the
way the harness does: JSON on stdin, exit code 2 blocks the call.

The front door is the main session: its payload has no `agent_id`/`agent_type`; a subagent's has
both. UNVERIFIED live: that shape comes from the Claude Code hooks documentation, not from a
recorded payload. A payload of another shape is denied, never allowed.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SETTINGS = REPO_ROOT / "src/adapters/claude/settings.json"
GUARD = REPO_ROOT / "src/overlay/hooks/front_door_guard.py"
HOOKS_DOC = REPO_ROOT / "src/overlay/hooks/README.md"
SH = shutil.which("sh") or "/bin/sh"


def _commands(matcher_part: str) -> list[str]:
    entries = json.loads(SETTINGS.read_text(encoding="utf-8"))["hooks"]["PreToolUse"]
    return [
        h["command"]
        for e in entries
        if matcher_part in e["matcher"]
        for h in e["hooks"]
        if "front_door_guard.py" in h["command"]
    ]


@pytest.fixture
def project(tmp_path: Path) -> Path:
    hooks = tmp_path / ".trazo" / "hooks"
    hooks.mkdir(parents=True)
    shutil.copy(GUARD, hooks / "front_door_guard.py")
    (tmp_path / ".trazo" / "project" / "adr").mkdir(parents=True)
    (tmp_path / "src").mkdir()
    return tmp_path


def _run(project_dir: Path, matcher_part: str, payload: object) -> subprocess.CompletedProcess[str]:
    commands = _commands(matcher_part)
    assert len(commands) == 1, f"settings.json must register the guard once for {matcher_part}"
    stdin = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run(  # noqa: S603 - fixed argv; the command comes from the repo's settings.json
        [SH, "-c", commands[0]],
        input=stdin,
        capture_output=True,
        text=True,
        env={"CLAUDE_PROJECT_DIR": str(project_dir), "PATH": "/usr/bin:/bin:/usr/local/bin"},
        check=False,
    )


def _bash(project: Path, command: str, **extra: object) -> subprocess.CompletedProcess[str]:
    payload = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(project)}
    payload.update(extra)
    return _run(project, "Bash", payload)


def _edit(project: Path, path: str, tool: str = "Edit", key: str = "file_path", **extra: object):
    payload = {"tool_name": tool, "tool_input": {key: path}, "cwd": str(project)}
    payload.update(extra)
    return _run(project, "Edit", payload)


SUBAGENT = {"agent_id": "a1b2", "agent_type": "engineer"}

# What the front door did in the field report, plus the routes around the obvious one.
BLOCKED_BASH = [
    "gh pr edit 12 --body 'Fail-first output: x'",
    "gh pr edit 12 --add-label x",
    "gh --repo o/r pr edit 12 --body x",
    "git commit --allow-empty -m 'rerun ci'",
    "git -C . commit --allow-empty -m x",
    "git add -A && git commit --allow-empty -m x",
    "git apply fix.patch",
    "sed -i 's/a/b/' src/x.py",
    "sed -i.bak 's/a/b/' src/x.py",
    "sed --in-place 's/a/b/' src/x.py",
    "perl -pi -e 's/a/b/' src/x.py",
    "echo hi | tee src/x.py",
    "echo hi > src/x.py",
    "echo hi >> src/x.py",
    "cat <<EOF > src/x.py\nhi\nEOF",
    "bash -c 'sed -i s/a/b/ src/x.py'",
    'sh -lc "gh pr edit 1 --body x"',
    "eval 'gh pr edit 1 --body x'",
    "echo $(gh pr edit 1 --body x)",
    "env FOO=1 gh pr edit 1 --body x",
    "if true; then gh pr edit 1 --body x; fi",
]


@pytest.mark.parametrize("command", BLOCKED_BASH)
def test_main_session_engineer_work_is_blocked(project, command):
    r = _bash(project, command)
    assert r.returncode == 2, (command, r.stderr)
    assert "/work" in r.stderr and "#319" in r.stderr


ALLOWED_BASH = [
    "git status",
    "git log --oneline -5",
    "git diff origin/main",
    "gh pr view 12",
    "gh pr checks 12",
    "gh pr comment 12 --body 'verdict'",
    "gh issue comment 5 --body 'Decided: x'",
    "gh issue create --title t --body b",
    "gh workflow run owner-merge.yml -f pr=12",
    "git commit -m 'Closes #5: status' && git push origin wrapup",
    "gh pr create --title t --body 'a > b'",
    "ls -la 2>&1 | head",
    "echo ok > /dev/null",
    "python3 -m pytest -q 2>&1 | tail -5",
    "cat README.md | grep -i foo",
]


@pytest.mark.parametrize("command", ALLOWED_BASH)
def test_main_session_reading_and_dispatching_is_allowed(project, command):
    r = _bash(project, command)
    assert r.returncode == 0, (command, r.stderr)


@pytest.mark.parametrize("command", BLOCKED_BASH)
def test_subagent_bash_is_not_this_guards_business(project, command):
    assert _bash(project, command, **SUBAGENT).returncode == 0


@pytest.mark.parametrize("tool", ["Edit", "Write", "MultiEdit"])
def test_main_session_cannot_edit_code(project, tool):
    r = _edit(project, str(project / "src" / "x.py"), tool=tool)
    assert r.returncode == 2, r.stderr
    assert "/work" in r.stderr and "#319" in r.stderr


def test_main_session_cannot_edit_notebooks(project):
    r = _edit(project, str(project / "n.ipynb"), tool="NotebookEdit", key="notebook_path")
    assert r.returncode == 2, r.stderr


@pytest.mark.parametrize(
    "rel",
    [
        ".trazo/project/STATUS.md",
        "/".join((".trazo", "project", "adr", "0099-x.md")),
        "/".join((".trazo", "project", "workstreams", "new.md")),
    ],
)
def test_main_session_may_write_project_state(project, rel):
    assert _edit(project, str(project / rel), tool="Write").returncode == 0


@pytest.mark.parametrize(
    "rel",
    [
        ".trazo/rules.md",
        ".trazo/hooks/front_door_guard.py",
        ".claude/settings.json",
        "/".join((".trazo", "project", "..", "hooks", "x.py")),
        "/".join((".trazo", "projectile", "x.md")),
    ],
)
def test_project_state_allowance_is_narrow(project, rel):
    assert _edit(project, str(project / rel)).returncode == 2


def test_symlink_out_of_project_state_is_blocked(project):
    (project / "src").mkdir(exist_ok=True)
    link = project / ".trazo" / "project" / "link"
    link.symlink_to(project / "src")
    assert _edit(project, str(link / "x.py")).returncode == 2


def test_relative_or_missing_path_is_blocked(project):
    assert _edit(project, ".trazo/project/STATUS.md").returncode == 2
    r = _run(project, "Edit", {"tool_name": "Write", "tool_input": {}})
    assert r.returncode == 2


@pytest.mark.parametrize("tool", ["Edit", "Write", "MultiEdit"])
def test_subagent_edits_are_allowed(project, tool):
    r = _edit(project, str(project / "src" / "x.py"), tool=tool, **SUBAGENT)
    assert r.returncode == 0, r.stderr


def test_either_subagent_field_marks_a_subagent(project):
    only_type = _edit(project, str(project / "src/x.py"), agent_type="engineer")
    only_id = _edit(project, str(project / "src/x.py"), agent_id="a1")
    assert only_type.returncode == 0 and only_id.returncode == 0


@pytest.mark.parametrize("blank", ["", "  ", None, 5])
def test_blank_agent_fields_are_the_main_session(project, blank):
    r = _edit(project, str(project / "src/x.py"), agent_id=blank, agent_type=blank)
    assert r.returncode == 2


@pytest.mark.parametrize("tool", ["Read", "Grep", "Glob", "Agent", "WebFetch"])
def test_other_tools_pass_through(project, tool):
    r = _run(project, "Bash", {"tool_name": tool, "tool_input": {}})
    assert r.returncode == 0


@pytest.mark.parametrize("payload", ["", "not json", "[]", "null", '"x"'])
def test_unparseable_input_fails_closed(project, payload):
    assert _run(project, "Bash", payload).returncode == 2
    assert _run(project, "Edit", payload).returncode == 2


def test_bash_without_command_or_unbalanced_quote_fails_closed(project):
    assert _run(project, "Bash", {"tool_name": "Bash", "tool_input": {}}).returncode == 2
    assert _bash(project, "echo 'unterminated").returncode == 2


def test_missing_script_blocks(tmp_path):
    for matcher in ("Bash", "Edit"):
        r = _run(tmp_path, matcher, {"tool_name": "Bash", "tool_input": {"command": "ls"}})
        assert r.returncode == 2


def test_registered_for_bash_and_every_edit_tool():
    assert len(_commands("Bash")) == 1
    entries = json.loads(SETTINGS.read_text(encoding="utf-8"))["hooks"]["PreToolUse"]
    edit = [e for e in entries if any("front_door_guard.py" in h["command"] for h in e["hooks"])]
    matchers = {m for e in edit for m in e["matcher"].split("|")}
    assert {"Bash", "Edit", "Write", "MultiEdit", "NotebookEdit"} <= matchers
    assert all(c.rstrip().endswith("|| exit 2") for c in _commands("Bash") + _commands("Edit"))


def test_readme_documents_the_guard_and_its_unverified_parts():
    text = HOOKS_DOC.read_text(encoding="utf-8")
    assert "front_door_guard.py" in text and "#319" in text
    assert "UNVERIFIED" in text[text.index("front_door_guard.py") :]


MEMORY = Path.home() / ".claude" / "projects" / "-some-project" / "memory"


def test_main_session_may_write_its_memory_notes(project):
    assert _edit(project, str(MEMORY / "note.md"), "Write").returncode == 0
    assert _bash(project, f"echo note >> {MEMORY}/note.md").returncode == 0


@pytest.mark.parametrize(
    "rel",
    [
        ".claude/settings.json",
        ".claude/projects/-some-project/settings.json",
        ".claude/projects/-some-project/memory/../settings.json",
        ".claude/projects/memory/note.md",
    ],
)
def test_memory_allowance_is_narrow(project, rel):
    assert _edit(project, str(Path.home() / rel), "Write").returncode == 2


def test_repo_files_stay_locked_and_issue_text_is_open(project):
    assert _edit(project, str(project / "src" / "x.py"), "Write").returncode == 2
    assert _bash(project, "echo hi > src/x.py").returncode == 2
    assert _bash(project, 'gh issue comment 5 --body "$(date)"').returncode == 0


def test_settings_allow_memory_writes_and_keep_the_claude_read_deny():
    perms = json.loads(SETTINGS.read_text(encoding="utf-8"))["permissions"]
    assert "Write(~/.claude/projects/*/memory/**)" in perms["allow"]
    assert "Read(~/.claude/**)" in perms["deny"]


def test_roles_state_the_permissive_policy_and_drop_the_old_construct_ban():
    root = Path(__file__).resolve().parents[1] / "src"
    for role in ("reviewer", "security"):
        text = (root / "overlay/roles" / f"{role}.md").read_text(encoding="utf-8")
        assert "Use no `$(...)`" not in text and "no heredocs" not in text
        assert "ADR 0032" in text
    pm = (root / "adapters/claude/agents/pm.md").read_text(encoding="utf-8")
    assert "close and reopen" in pm and "add or remove labels" in pm
    assert "## Permissive by default" in (root / "overlay/rules.md").read_text(encoding="utf-8")
