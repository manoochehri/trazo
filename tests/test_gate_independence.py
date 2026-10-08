"""Always-on gates and request routing must survive skipped command workflows (#156)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_core_rule_applies_gates_outside_commands_and_skills():
    rules = _read("src/overlay/rules.md")
    assert "Gates hold regardless of how work starts" in rules
    assert "plain English" in rules
    assert "must not be its only enforcement" in rules
    assert "repository settings and rulesets, then CI and" in rules


def test_external_behavior_and_fail_first_are_checked_by_reviewers():
    rules = _read("src/overlay/rules.md")
    reviewer = _read("src/overlay/roles/reviewer.md")
    work = _read("src/overlay/skills/work.md")
    template = _read(".github/pull_request_template.md")

    assert "For external API behavior, cite the primary documentation" in rules
    assert "write the regression test first" in rules
    assert "A reviewer treats missing fail-first evidence as must-fix" in rules
    assert "source supports the implementation" in reviewer
    assert "test's failing" in reviewer and "before the fix" in reviewer
    assert "UNVERIFIED" in work
    assert "Review rounds" in template
    assert "defects found and fixed" in template


def test_pm_boundaries_and_owner_message_shape_are_durable():
    rules = _read("src/overlay/rules.md")
    advisor = " ".join(_read("src/overlay/ADVISOR.md").split())
    assert "Neither role" in rules and "production" in rules
    assert "Time pressure is a request for a date" not in rules
    assert "cite that source" in advisor
    assert "present it as a question, not a decision" in advisor
    assert "at most one command" in rules
    assert "work remaining on the issues" in advisor
    assert "never permission to drop an agreed check or gate" in advisor
    assert "at most one command" in advisor


def test_session_budget_and_owner_summary_rules_reach_routines():
    rules = _read("src/overlay/rules.md")
    for path in (
        "src/overlay/skills/work.md",
        "src/overlay/skills/start.md",
        "src/overlay/skills/wrapup.md",
    ):
        assert "fresh session" in _read(path).lower(), path
    assert "one working session per task" in rules
    assert "Do not poll another session" in rules
    assert "at most one command" in _read("src/overlay/skills/brief.md")
