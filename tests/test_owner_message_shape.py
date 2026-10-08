"""Owner handoffs stay short and decision-first (issue #152)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_core_rule_defines_short_decision_first_owner_messages():
    rules = _read("src/overlay/rules.md")
    assert "short and decision-first" in rules
    assert "at most one command" in rules
    assert "do not assign homework" in rules
    assert "multi-step instructions" in rules
    assert "linked issue or pull request" in rules


def test_owner_facing_routines_follow_the_rule():
    start = _read("src/overlay/skills/start.md")
    brief = _read("src/overlay/skills/brief.md")
    wrapup = _read("src/overlay/skills/wrapup.md")
    work = _read("src/overlay/skills/work.md")

    assert "compact issue links" in start
    for routine in (brief, wrapup, work):
        assert "at most one command" in routine
        assert "multi-step instructions" in routine
    assert "supporting evidence in the linked PR" in wrapup
    assert "supporting evidence in the linked PR" in work
