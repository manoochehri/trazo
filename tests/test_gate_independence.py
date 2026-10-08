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

    assert "If code depends on an outside service" in rules
    assert "write the regression test first" in rules
    assert "A reviewer treats missing fail-first evidence as must-fix" in rules
    assert "source supports the implementation" in reviewer
    assert "test's failing" in reviewer and "before the fix" in reviewer
    assert "UNVERIFIED" in work
    assert "Review rounds" in template
    assert "defects found and fixed" in template


def test_external_api_rules_require_sources_for_assumptions_and_fakes():
    rules = _read("src/overlay/rules.md")
    work = _read("src/overlay/skills/work.md")
    reviewer = _read("src/overlay/roles/reviewer.md")

    assert "check its documentation or a real response" in rules
    assert "link" in rules and "what you checked" in rules
    assert "Base tests and fakes on that evidence" in rules
    assert "Use the service's original documentation" in rules
    assert "mark the issue" in rules and "`needs-pm`" in rules
    assert "list each assumed behavior with its source or `UNVERIFIED`" in work
    assert "UNVERIFIED` behavior the code depends on blocks the change" in work
    assert "new or changed fakes, fixtures, or mocks cite" in reviewer
    assert "An uncited fake of an external system is must-fix" in reviewer


def test_pm_boundaries_and_owner_message_shape_are_durable():
    rules = _read("src/overlay/rules.md")
    advisor = _read("src/overlay/ADVISOR.md")
    assert "Neither role" in rules and "production" in rules
    assert "Time pressure is a request for a date" in rules
    assert "cites the issue, project document" in rules
    assert "at most one command" in rules
    assert "estimates them from remaining" in rules
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
