"""Pin ADR 0018 routing and ADR 0019 delegation in the shipped source."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _flat(path: str) -> str:
    return " ".join((ROOT / path).read_text(encoding="utf-8").split())


def test_senior_routing_is_consistent_across_advisor_and_engineer_adapters() -> None:
    advisor = _flat("src/overlay/ADVISOR.md")
    rules = _flat("src/overlay/rules.md")
    engineer = _flat("src/overlay/roles/engineer.md")
    pm = _flat("src/overlay/roles/pm.md")
    eng_command = _flat("src/adapters/claude/commands/eng.md")
    work_command = _flat("src/adapters/claude/commands/work.md")

    for text in (advisor, rules, engineer, pm, eng_command, work_command):
        assert "`tier:senior`" in text
    for text in (advisor, rules, engineer, eng_command, work_command):
        assert "two consecutive" in text.lower() or "2 consecutive" in text.lower()
    assert "CODEOWNERS" in advisor and ".github/workflows/" in advisor
    assert "dependency" in advisor.lower() and "cross-workstream" in advisor
    assert "reviewer" in engineer.lower() and "security" in engineer.lower()
    assert "skeptic" in engineer.lower()
    assert "UNVERIFIED" in advisor


def test_advisor_may_dispatch_any_subagent_but_keeps_independent_gates() -> None:
    advisor = _flat("src/overlay/ADVISOR.md")
    rules = _flat("src/overlay/rules.md")
    pm_adapter = _flat("src/adapters/claude/agents/pm.md")

    assert "may spawn arbitrary subagents" in advisor.lower()
    assert "never investigates or edits code itself" in advisor
    assert "reviewer, security and skeptic" in advisor
    assert "arbitrary subagents" in rules.lower()
    assert "reviewer, security and skeptic" in rules
    assert "Read-path denies for secret files only" in pm_adapter
