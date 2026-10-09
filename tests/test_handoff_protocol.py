"""Guards for the agent-to-agent handoff protocol (issues #35, #36).

The protocol is prose in the canonical Trazo skills and roles, so nothing but a test
stops it from being edited back into "ask the owner in chat" — the failure mode #35
was opened for.
These checks assert the load-bearing pieces are still there, not the exact wording.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORK = REPO_ROOT / "src" / "overlay" / "skills" / "work.md"
PM_AGENT = REPO_ROOT / "src" / "overlay" / "ADVISOR.md"
PM_ROLE = REPO_ROOT / "src" / "overlay" / "roles" / "pm.md"
PM_ADAPTER = REPO_ROOT / "src" / "adapters" / "claude" / "agents" / "pm.md"
KICKOFF = REPO_ROOT / "src" / "overlay" / "skills" / "kickoff.md"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_engineer_posts_blockers_to_the_issue() -> None:
    """The blocked path routes through GitHub, not chat."""
    work = _text(WORK)
    assert "gh issue comment" in work
    assert "--add-label needs-pm" in work
    assert re.search(r"`pm` subagent", work)


def test_engineer_has_the_does_it_block_progress_test() -> None:
    assert "progress stops" in _text(WORK)


def test_engineer_does_not_classify_owner_calls() -> None:
    """Under-labelling is silent, so this call belongs to the PM (#35)."""
    assert re.search(r"never classify", _text(WORK), re.IGNORECASE)


def test_pm_has_the_handoff_duties() -> None:
    """The tagged advisor keeps decisions in durable project and issue records."""
    advisor = _text(PM_AGENT)
    assert "Write outcomes **into the repo**" in advisor
    assert "tasks → GitHub issues" in advisor
    assert "Role boundary" in advisor


def test_pm_role_command_forbids_file_edits() -> None:
    """The Claude PM subagent is read-only and delegates policy to the canonical role."""
    adapter = _text(PM_ADAPTER)
    fm = adapter.split("\n---\n", 1)[0].removeprefix("---\n")
    tools = re.search(r"^tools: (.+)$", fm, re.MULTILINE)
    assert tools, "PM subagent adapter must declare its tool boundary"
    assert not {"Edit", "Write"} & set(tools.group(1).split(", "))
    assert ".trazo/ADVISOR.md" in adapter


def test_pm_role_command_defers_rather_than_restating_the_grant() -> None:
    """The canonical PM role is a pointer to the full advisor policy."""
    role = _text(PM_ROLE)
    assert ".trazo/ADVISOR.md" in role


def test_kickoff_creates_the_labels_the_protocol_runs_on() -> None:
    """Without these, `--add-label needs-pm` fails in a derived project and the engineer
    falls back to stopping in chat -- the failure #35 was opened for."""
    kickoff = _text(KICKOFF)
    assert "Set up GitHub labels" in kickoff
    assert "only after agreeing on the plan" in kickoff
