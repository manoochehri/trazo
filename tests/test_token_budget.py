"""Keep the shared token budget rule and fresh-session guidance explicit (#151)."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RULES = REPO_ROOT / "src" / "overlay" / "rules.md"
START = REPO_ROOT / "src" / "overlay" / "skills" / "start.md"
WRAPUP = REPO_ROOT / "src" / "overlay" / "skills" / "wrapup.md"


def test_token_budget_rule_and_fresh_session_guidance_exist() -> None:
    rules = re.sub(r"\s+", " ", RULES.read_text(encoding="utf-8"))
    assert "## Token budget" in rules
    for guidance in (
        "one fresh working session per task",
        "Do not poll another session",
        "tests, PR reports, and issue comments",
        "only when a rule requires a separate context",
        "issue tracker",
    ):
        assert guidance in rules, f"token budget rule is missing {guidance!r}"

    assert "fresh session for each task" in START.read_text(encoding="utf-8")
    assert "fresh session for the\n  next task to stay within the token budget" in WRAPUP.read_text(
        encoding="utf-8"
    )
