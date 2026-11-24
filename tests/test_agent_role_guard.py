"""Issue #326: only the pinned Trazo roles may be started as subagents, enforced by a hook.

Prompt text did not stop the front door from starting generic agents with a role in the prompt.
These tests run the exact command the shipped settings.json declares for the Agent tool, the way
the harness does: JSON on stdin, exit code 2 blocks the call.

UNVERIFIED live: the hook input shape (`tool_name`, `tool_input.subagent_type`) comes from the
Claude Code hooks documentation, not from a recorded payload. The guard fails closed, so a payload
of another shape is denied, never allowed.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SETTINGS = REPO_ROOT / "src/adapters/claude/settings.json"
GUARD = REPO_ROOT / "src/overlay/hooks/agent_role_guard.py"
HOOKS_DOC = REPO_ROOT / "src/overlay/hooks/README.md"
SH = shutil.which("sh") or "/bin/sh"


def _agent_entry() -> dict:
    entries = json.loads(SETTINGS.read_text(encoding="utf-8"))["hooks"]["PreToolUse"]
    matching = [e for e in entries if "agent_role_guard.py" in json.dumps(e)]
    assert len(matching) == 1, "settings.json must register the agent role guard exactly once"
    return matching[0]


def _hook_command() -> str:
    return _agent_entry()["hooks"][0]["command"]


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A host-shaped project: the guard installed at .trazo/hooks/ (overlay -> .trazo)."""
    hooks = tmp_path / ".trazo" / "hooks"
    hooks.mkdir(parents=True)
    shutil.copy(GUARD, hooks / "agent_role_guard.py")
    return tmp_path


def _run(project_dir: Path, stdin: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed argv; the command comes from the repo's settings.json
        [SH, "-c", _hook_command()],
        input=stdin,
        capture_output=True,
        text=True,
        env={"CLAUDE_PROJECT_DIR": str(project_dir), "PATH": "/usr/bin:/bin:/usr/local/bin"},
        check=False,
    )


def _agent_call(kind: object, tool: str = "Agent", **extra: object) -> str:
    tool_input: dict = {"description": "x", "prompt": "Act as the architect role."}
    if kind is not None:
        tool_input["subagent_type"] = kind
    tool_input.update(extra)
    return json.dumps(
        {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input}
    )


# The dispatches the front door made in the session that produced #326: generic agents given a
# role in the prompt, instead of the pinned agents or the role commands.
GENERIC_DISPATCHES = ["general-purpose", "Explore", "Plan", "claude-code-guide", "statusline-setup"]
PINNED = ["pm", "reviewer", "security", "skeptic", "trazo-pm", "trazo-reviewer", "trazo-security"]


@pytest.mark.parametrize("kind", GENERIC_DISPATCHES)
def test_generic_agents_are_blocked(project, kind):
    r = _run(project, _agent_call(kind))
    assert r.returncode == 2, r.stderr
    assert "/architect" in r.stderr and "/eng" in r.stderr and "#326" in r.stderr


@pytest.mark.parametrize("kind", GENERIC_DISPATCHES)
def test_generic_agents_are_blocked_under_the_earlier_tool_name(project, kind):
    assert _run(project, _agent_call(kind, tool="Task")).returncode == 2


@pytest.mark.parametrize("kind", PINNED)
def test_pinned_roles_are_allowed(project, kind):
    r = _run(project, _agent_call(kind))
    assert r.returncode == 0, r.stderr


@pytest.mark.parametrize(
    "kind",
    ["", "   ", None, 7, ["pm"], {"pm": 1}, "PM", "pm ", "pm\n", "general-purpose,pm", "../pm"],
)
def test_missing_or_odd_subagent_type_is_blocked(project, kind):
    assert _run(project, _agent_call(kind)).returncode == 2


@pytest.mark.parametrize(
    "stdin",
    [
        "",
        "not json",
        "[]",
        "null",
        '"Agent"',
        json.dumps({"tool_name": "Agent"}),
        json.dumps({"tool_name": "Agent", "tool_input": None}),
        json.dumps({"tool_name": "Agent", "tool_input": "pm"}),
        json.dumps({"tool_name": "Agent", "tool_input": []}),
    ],
)
def test_unparseable_or_oddly_shaped_input_fails_closed(project, stdin):
    assert _run(project, stdin).returncode == 2


def test_other_tools_are_not_this_hooks_business(project):
    for tool in ("Bash", "Read", "Edit", "Write", "WebSearch"):
        payload = json.dumps({"tool_name": tool, "tool_input": {"command": "ls"}})
        assert _run(project, payload).returncode == 0, tool


def test_a_missing_guard_script_blocks_rather_than_allows(tmp_path):
    """The declared command ends `|| exit 2`, so an absent script cannot fail open."""
    r = _run(tmp_path, _agent_call("pm"))
    assert r.returncode == 2


def test_the_hook_is_registered_for_the_agent_tool_and_only_blocks():
    entry = _agent_entry()
    assert set(entry["matcher"].split("|")) >= {"Agent", "Task"}
    (hook,) = entry["hooks"]
    assert hook["type"] == "command"
    assert hook["command"].rstrip().endswith("|| exit 2")
    assert ".trazo/hooks/agent_role_guard.py" in hook["command"]


def test_the_pinned_set_matches_the_shipped_agents():
    """The allowlist is the subagents the Claude adapter ships, nothing more."""
    shipped = {p.stem for p in (REPO_ROOT / "src/adapters/claude/agents").glob("*.md")}
    allowed = set(json.loads(json.dumps(sorted(_pinned_from_script()))))
    assert allowed == shipped, (allowed, shipped)


def _pinned_from_script() -> set[str]:
    namespace: dict = {}
    exec(  # noqa: S102 - reads constants from the repo's own guard script, no input
        compile(GUARD.read_text(encoding="utf-8"), str(GUARD), "exec"),
        {"__name__": "agent_role_guard"},
        namespace,
    )
    return set(namespace["PINNED"])


def test_the_hook_is_documented_with_its_limits():
    text = HOOKS_DOC.read_text(encoding="utf-8")
    assert "agent_role_guard.py" in text
    assert "UNVERIFIED" in text
    assert "existing" in text and "settings.json" in text
