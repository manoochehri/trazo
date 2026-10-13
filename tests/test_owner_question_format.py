"""Owner-facing roles state their questions in one plain shape (issue #218)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Each file that can put a choice in front of the owner must carry the format.
OWNER_FACING = [
    "src/overlay/ADVISOR.md",
    "src/overlay/skills/work.md",
    "src/overlay/skills/wrapup.md",
    "src/overlay/skills/start.md",
    "src/overlay/skills/brief.md",
    "src/overlay/skills/decide.md",
    "src/overlay/roles/engineer.md",
    "src/overlay/roles/reviewer.md",
    "src/overlay/roles/security.md",
    "src/overlay/roles/skeptic.md",
]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_every_owner_facing_file_requires_plain_question_with_pros_and_cons():
    for path in OWNER_FACING:
        text = _read(path)
        assert "no unexplained jargon or issue shorthand" in text, f"{path} lacks the jargon rule"
        assert "pro and a con" in text, f"{path} lacks pros and cons for options"
        assert "(Recommended)" in text, f"{path} lacks a marked recommendation"


def test_pm_and_decision_routines_name_the_format_where_they_ask_the_owner():
    advisor = _read("src/overlay/ADVISOR.md")
    decide = _read("src/overlay/skills/decide.md")
    start = _read("src/overlay/skills/start.md")

    assert "owner question" in advisor
    assert "pro and a con" in advisor
    assert "pro and a con" in decide
    assert "two or three options" in decide
    assert "question awaiting an answer" in start
    assert "pro and a con" in start
