"""Pin issue #150's PM evidence and escalation guidance in the shipped advisor role."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ADVISOR = REPO_ROOT / "src/overlay/ADVISOR.md"


def test_pm_leaves_unsupported_questions_open_and_escalates_owner_decisions() -> None:
    advisor = " ".join(ADVISOR.read_text(encoding="utf-8").split())

    decisions = advisor.split("**Decisions and escalation:**", 1)[1].split(" - **", 1)[0]
    assert "cite that source" in decisions
    assert "present it as a question, not a decision" in decisions
    assert "only when the choice is genuinely the owner's" in decisions
    assert "decide the rest yourself" in decisions


def test_pm_sends_engineer_provided_numbers_to_the_skeptic_first() -> None:
    advisor = " ".join(ADVISOR.read_text(encoding="utf-8").split())

    assert "Send engineer-provided numbers to the `skeptic` subagent" in advisor
    assert "before using them in a decision or repeating them to the owner" in advisor


def test_pm_owns_issue_based_dates_and_explains_revisions() -> None:
    advisor = " ".join(ADVISOR.read_text(encoding="utf-8").split())
    dates = advisor.split("**Own dates:**", 1)[1].split(" - **", 1)[0]

    assert "work remaining on the issues" in dates
    assert "state each estimate once" in dates
    assert "only when the work changes" in dates
    assert "why the date moved" in dates


def test_owner_time_pressure_does_not_drop_a_gate() -> None:
    advisor = " ".join(ADVISOR.read_text(encoding="utf-8").split())
    pressure = advisor.split("**Pressure:**", 1)[1].split("## How to respond", 1)[0]

    assert "request for a date" in pressure
    assert "never permission to drop an agreed check or gate" in pressure
    assert "explicit owner decision" in pressure
    assert "recorded on the issue" in pressure


def test_pm_agent_points_to_the_single_canonical_role() -> None:
    agent = (REPO_ROOT / "src/adapters/claude/agents/pm.md").read_text(encoding="utf-8")

    assert "`.trazo/ADVISOR.md`" in agent
    assert "canonical PM role" in agent
    assert "Claude-specific tool and workflow constraints" in agent


def test_shared_rules_are_the_only_home_for_the_production_boundary() -> None:
    rules = (REPO_ROOT / "src/overlay/rules.md").read_text(encoding="utf-8")
    advisor = ADVISOR.read_text(encoding="utf-8")
    engineer = (REPO_ROOT / "src/overlay/roles/engineer.md").read_text(encoding="utf-8")

    assert "Neither role (engineer or PM) accesses production" in rules
    assert "deploying, querying, or" in rules
    assert "production" not in advisor
    assert "production" not in engineer


def test_engineer_routes_scope_calls_through_work_handoff() -> None:
    engineer = (REPO_ROOT / "src/overlay/roles/engineer.md").read_text(encoding="utf-8")
    work = (REPO_ROOT / "src/overlay/skills/work.md").read_text(encoding="utf-8")
    command = (REPO_ROOT / "src/adapters/claude/commands/eng.md").read_text(encoding="utf-8")

    assert "sequencing, priority, and scope questions" in engineer
    assert "`needs-pm`" in engineer and "`/work` workflow" in engineer
    assert "Questions about sequencing, priority, or scope" in work
    assert "same `needs-pm` handoff" in work
    assert "`needs-pm` handoff" in command


def _open_items_section() -> str:
    advisor = " ".join(ADVISOR.read_text(encoding="utf-8").split())
    return advisor.split("## Open items", 1)[1].split("## How to respond", 1)[0]


def test_pm_leaves_no_open_item_unowned() -> None:
    """Issue #194: every open item ends the turn dispatched, as an owner question, or blocked."""
    section = _open_items_section()

    assert "No turn ends with an unowned open item" in section
    assert "*dispatched*" in section and "recorded on the issue" in section
    assert "*owner question*" in section and "`needs-decision`" in section
    assert "*blocked*" in section and "what unblocks it" in section


def test_pm_dispatch_table_routes_each_kind_of_item() -> None:
    section = _open_items_section()

    assert "fact about code or real data -> eng" in section
    assert "skeptic" in section and "number" in section
    assert "reviewer" in section
    assert "security" in section and "secrets" in section
    assert "owner-level choice" in section and "needs-decision" in section


def test_pm_posts_dispatches_and_answers_on_the_issue() -> None:
    section = _open_items_section()

    assert "answer is posted on the issue" in section
    assert "dispatch is posted when it starts" in section


def test_pm_does_not_ask_permission_to_file_clear_work() -> None:
    section = _open_items_section()

    assert "Do not ask permission to file" in section
    assert "clear and reversible" in section
    assert "If the owner says they are exploring" in section and "file nothing" in section


def test_pm_limits_batch_sequence_and_cap_dispatch() -> None:
    section = _open_items_section()

    assert "batch related questions into one eng session" in section
    assert "cap concurrent spawned agents" in section
    assert "sequence the skeptic after the evidence exists" in section
    assert "never investigates or edits code" in section
