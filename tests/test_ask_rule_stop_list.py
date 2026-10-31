"""The stop list in rules.md must keep naming every category the security review required (#266)."""

from pathlib import Path

RULES = Path(__file__).resolve().parent.parent / "src" / "overlay" / "rules.md"

# Hosts do not receive scripts/report_verdict.py, so the rule text itself must name these.
REQUIRED = [
    "CODEOWNERS",
    "the charter",
    "agent rules",
    "role definitions",
    "decision records",
    "CLAUDE.md",
    "AGENTS.md",
    ".claude/",
    ".codex/",
    ".agents/",
    ".trazo/",
    "agent instruction files and skills",
    "build, CI and test configuration",
    "secrets",
    "spend",
    "production",
    "permissions",
    "dependencies",
    "infrastructure",
    "repository settings",
    "data or an external system",
    "scope, priority, sequencing or acceptance criteria",
    "Anything not done through a pull request is never reversible",
    "never enables auto-merge",
    "or adds a file for a listed file to use later",
    "Ordinary source, test and documentation files are not on the list",
    "Check again before you push",
]


def _section() -> str:
    text = RULES.read_text(encoding="utf-8")
    start = text.index("## Ask before guessing")
    end = text.index("## Session budget")
    return " ".join(text[start:end].split())


def test_the_ask_rule_names_every_stop_list_category() -> None:
    section = _section()
    missing = [item for item in REQUIRED if item not in section]
    assert not missing, f"the stop list in rules.md no longer names: {missing}"
