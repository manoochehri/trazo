"""Guards for the agent-to-agent handoff protocol (issues #35, #36).

The protocol is prose in `.claude/`, so nothing but a test stops it from being
edited back into "ask the owner in chat" — the failure mode #35 was opened for.
These checks assert the load-bearing pieces are still there, not the exact wording.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORK = REPO_ROOT / ".claude" / "commands" / "work.md"
PM_AGENT = REPO_ROOT / ".claude" / "agents" / "pm.md"
PM_ROLE = REPO_ROOT / ".claude" / "commands" / "pm.md"
KICKOFF = REPO_ROOT / ".claude" / "commands" / "kickoff.md"

# The scoped grant lives in exactly one file. Restating it is how the two PM surfaces
# drifted apart in the first place (see #36).
GRANT_FLAGS = (
    "--add-label",
    "--remove-label",
    "--parent",
    "--add-sub-issue",
    "--add-blocked-by",
    "--add-blocking",
    "--milestone",
    "--add-assignee",
    "gh label create",
)


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


def _bullet(text: str, marker: str) -> str:
    """The one line of `text` carrying `marker`, so a flag can't satisfy a test from
    the wrong bullet — presence in the file says nothing about grant vs prohibition."""
    lines = [ln for ln in text.splitlines() if marker in ln]
    assert len(lines) == 1, f"expected exactly one {marker!r} bullet, found {len(lines)}"
    return lines[0]


def test_pm_may_maintain_the_issue_graph() -> None:
    pm = _text(PM_AGENT)
    grant = _bullet(pm, "Issue-graph edits you may make:")
    assert "gh issue edit" in grant
    for flag in ("--add-label", "--remove-label", "--parent", "--add-blocked-by", "--milestone"):
        assert flag in grant, f"{flag} missing from the grant bullet"
    assert "gh label create" in grant


def test_pm_may_not_rewrite_specs_or_close_issues() -> None:
    """Assert the denial, not the mention: `--body` appearing anywhere would otherwise
    keep this green even if the file were rewritten to grant it."""
    denial = _bullet(_text(PM_AGENT), "Not yours:")
    assert "--body" in denial
    assert "gh issue close" in denial
    grant = _bullet(_text(PM_AGENT), "Issue-graph edits you may make:")
    assert "--body" not in grant
    assert "gh issue close" not in grant


def test_pm_clears_the_owners_gate_only_with_a_quoted_decision() -> None:
    """`needs-decision` is the owner's gate; escalation is one-way, and the PM may clear
    the label only in the same step as a comment quoting the owner's decision."""
    pm = _text(PM_AGENT)
    rule = _bullet(pm, "`needs-decision` is the owner's gate")
    assert "Owner decision (" in rule
    assert "quotes the owner" in rule and "verbatim" in rule
    assert "immediately after" in rule
    for forbidden in ("your own judgment", "say-so", "inferred decision"):
        assert forbidden in rule, f"must still forbid clearing on {forbidden}"
    assert re.search(r"[Nn]ever remove it on", rule)
    assert "says where they were given" in rule
    assert '"in session"' in rule and "URL of an owner-authored" in rule
    assert "removal with no such comment right before it is a rule violation" in rule
    assert "subagent" in rule
    assert "relayed by another agent never counts" in rule
    for relay in ("engineer's prompt", "subagent report", "agent-written text"):
        assert relay in rule, f"must still reject a relayed quote in {relay}"
    assert "never the reverse" in pm
    # The role command must not restate the old absolute ban.
    assert not re.search(r"never remove `needs-decision`", _text(PM_ROLE))
    assert "Owner decision (" in _text(PM_ROLE)


def test_pm_escalation_matches_what_work_md_promises() -> None:
    """work.md tells the engineer what the PM will do on escalation; if only one of the
    two files is updated they disagree -- the defect this whole PR exists to prevent."""
    classify = _bullet(_text(PM_AGENT), "Classify blockers")
    assert "needs-decision" in classify
    assert "remove `needs-pm`" in classify, "escalation must leave the issue in one queue"
    assert ".github/CODEOWNERS" in classify, "no way to resolve the owner's handle otherwise"
    assert "never the reverse" in classify, "escalation is one-way"


def test_pm_has_the_handoff_duties() -> None:
    pm = _text(PM_AGENT)
    assert re.search(r"Classify blockers", pm)
    assert re.search(r"never hand the owner text to paste", pm, re.IGNORECASE)
    assert "GitHub state" in pm


def test_pm_role_command_forbids_file_edits() -> None:
    """Load-bearing here: the role command runs in the main session, which has Edit/Write.

    The subagent's frontmatter grants no editing tools at all, so the same sentence is
    only belt-and-braces on that surface.
    """
    role = _text(PM_ROLE)
    assert re.search(r"do NOT edit code or config", role)
    assert "`Edit`" in role and "`Write`" in role


def test_pm_role_command_defers_rather_than_restating_the_grant() -> None:
    """Guarding only the subagent would have passed while the two files contradicted."""
    role = _text(PM_ROLE)
    assert ".claude/agents/pm.md" in role
    for flag in GRANT_FLAGS:
        assert flag not in role, f"{flag} belongs only in .claude/agents/pm.md"


def test_kickoff_creates_the_labels_the_protocol_runs_on() -> None:
    """Without these, `--add-label needs-pm` fails in a derived project and the engineer
    falls back to stopping in chat -- the failure #35 was opened for."""
    kickoff = _bullet(_text(KICKOFF), "Create GitHub labels")
    for label in ("needs-pm", "needs-decision", "P0", "P1", "P2", "epic"):
        assert label in kickoff, f"kickoff does not create the {label} label"
