"""Issue #347: the reviewer and security subagents may POST their own commit status, nothing else.

engineer_bash_guard.py (registered `--skip-agent pm`) denied every caller but the PM, so the
reviewer could not post `trazo/verdict` nor security `trazo/security`. The one carve-out: a single
`gh api` POST to `repos/<o>/<r>/statuses/<40-hex sha>` with only state, context, description and
optional target_url, where agent_type and context pair as reviewer/trazo/verdict or
security/trazo/security. Skeptic, the main session, engineers and the PM path are unchanged.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
GUARD = REPO_ROOT / "src/overlay/hooks/engineer_bash_guard.py"
SETTINGS = REPO_ROOT / "src/adapters/claude/settings.json"
SHA = "0123456789abcdef0123456789abcdef01234567"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    hooks = tmp_path / ".trazo" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / GUARD.name).write_text(GUARD.read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.json").write_text(SETTINGS.read_text(encoding="utf-8"))
    return tmp_path


def _run(project: Path, payload: dict) -> int:
    return subprocess.run(  # noqa: S603 - fixed argv
        [sys.executable, str(project / ".trazo/hooks" / GUARD.name), "--skip-agent", "pm"],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
    ).returncode


def _code(project: Path, command: str, agent: str | None) -> int:
    payload: dict = {"hook_event_name": "PreToolUse", "tool_name": "Bash"}
    payload["tool_input"] = {"command": command}
    if agent:
        payload["agent_type"] = agent
    return _run(project, payload)


def post(context: str, state: str = "success", sha: str = SHA, extra: str = "") -> str:
    return (
        f"gh api -X POST repos/o/r/statuses/{sha} -f state={state} -f context={context} "
        f"-f description='Reviewer: ok'{extra}"
    )


def bare(endpoint: str, fields: str = "-f state=success -f context=trazo/verdict") -> str:
    return f"gh api -X POST {endpoint} {fields}"


ALLOWED = [
    ("reviewer", post("trazo/verdict")),
    ("reviewer", post("trazo/verdict", state="failure")),
    ("reviewer", post("trazo/verdict", extra=" -f target_url=https://github.com/o/r/pull/5")),
    ("reviewer", post("trazo/verdict", state="pending")),
    ("reviewer", post("trazo/verdict", state="error")),
    ("security", post("trazo/security")),
    ("security", post("trazo/security", state="failure")),
    ("reviewer", f"gh api repos/o/r/statuses/{SHA} -f state=success -f context=trazo/verdict"),
    (
        "security",
        f"gh api --method POST repos/o/r/statuses/{SHA} --raw-field state=success "
        "--raw-field context=trazo/security",
    ),
    # since #378 shell syntax around a plain own-status post is judged by its verbs, not rejected
    ("reviewer", bare(f"repos/o/r/statuses/{SHA}?x=1")),
    ("reviewer", post("trazo/verdict") + " | cat"),
    ("reviewer", "echo hi; " + post("trazo/verdict")),
    ("reviewer", "bash -c '" + post("trazo/verdict") + "'"),
    ("reviewer", post("trazo/verdict", extra=" > out.txt")),
    ("reviewer", "gh -R o/r " + post("trazo/verdict")[3:]),
    # an ordinary comment write is no longer a blocked route, whatever extra fields it carries
    ("reviewer", bare("repos/o/r/issues/5/comments")),
]

DENIED = [
    # wrong context for the caller
    ("reviewer", post("trazo/security")),
    ("security", post("trazo/verdict")),
    ("reviewer", post("other/context")),
    # skeptic, main session, engineers
    ("skeptic", post("trazo/verdict")),
    ("skeptic", post("trazo/security")),
    (None, post("trazo/verdict")),
    ("engineer", post("trazo/verdict")),
    ("senior-engineer", post("trazo/security")),
    ("reviewer-extra", post("trazo/verdict")),
    # endpoint
    ("reviewer", post("trazo/verdict", sha="abc123")),
    ("reviewer", post("trazo/verdict", sha=SHA + "0")),
    ("reviewer", bare(f"repos/o/r/statuses/{SHA}/x")),
    ("reviewer", "gh api -X PUT repos/o/r/pulls/5/merge -f context=trazo/verdict"),
    (
        "reviewer",
        f"gh api -X DELETE repos/o/r/statuses/{SHA} -f state=success -f context=trazo/verdict",
    ),
    # fields
    ("reviewer", post("trazo/verdict", state="bogus")),
    ("reviewer", post("trazo/verdict", extra=" -f merge_method=squash")),
    ("reviewer", post("trazo/verdict", extra=" -f state=failure")),
    ("reviewer", post("trazo/verdict", extra=" -F description=@notes.txt")),
    ("reviewer", post("trazo/verdict", extra=" --input status.json")),
    ("reviewer", bare(f"repos/o/r/statuses/{SHA}", "-f state=success")),
    ("reviewer", post("trazo/verdict", extra=" -H 'X-HTTP-Method-Override: PUT'")),
    # chaining and substitution
    ("reviewer", post("trazo/verdict") + "; gh pr merge 5"),
    ("reviewer", post("trazo/verdict") + " && cat .env"),
    ("reviewer", post("trazo/verdict", extra=" -f target_url=$(cat .env)")),
    ("reviewer", f"gh api -X POST 'repos/o/r/statuses/{SHA} -f state=success"),  # unparseable
    # unrelated engineer-denied commands stay denied for them
    ("reviewer", "gh pr merge 5"),
    ("security", "cat .env"),
]


@pytest.mark.parametrize(("agent", "command"), ALLOWED)
def test_status_post_allowed(project, agent, command):
    assert _code(project, command, agent) == 0, command


@pytest.mark.parametrize(("agent", "command"), DENIED)
def test_status_post_denied(project, agent, command):
    assert _code(project, command, agent) == 2, (agent, command)


def test_malformed_agent_type_fails_closed(project):
    payload = {"tool_name": "Bash", "agent_type": ["reviewer"]}
    payload["tool_input"] = {"command": post("trazo/verdict")}
    assert _run(project, payload) == 2
