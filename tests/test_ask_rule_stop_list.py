"""The stop list in rules.md must keep naming every category the security review required (#266)."""

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RULES = REPO / "src" / "overlay" / "rules.md"

# Hosts do not receive scripts/report_verdict.py, so the rule text itself must name these.
REQUIRED = [
    "CODEOWNERS",
    "the charter",
    "agent rules",
    "role definitions",
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
    "check again before you push",
    "outside `.trazo/project/`",
    "ARCHITECTURE_CONTRACT.md",
    "SKEPTIC_BAR.md",
    "the list wins",
    "however it is reached",
    "Judge the plan as a whole",
    "an answer relayed by another agent does not count",
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


def test_decision_records_are_not_on_the_stop_list() -> None:
    """Owner decision on #278 (2026-11-19): agents record decisions without asking.
    Writing a decision record is therefore not a stop, and the stop list must not say so."""
    section = _section()
    assert "decision records" not in section, "the stop list still names decision records"
    assert "write the decision records" in " ".join(
        (REPO / "src/overlay/rules.md").read_text(encoding="utf-8").split()
    ), "End every session must still tell agents to write the decision records"
