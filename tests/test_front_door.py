"""The main session is the front door: it acts, it does not print a menu and wait (issue #304).

v0.3.0 shipped ADR 0025 ("the front door starts the agent") but never said what the front door is.
In the field the main session printed `/trazo`'s "You could say" menu and stopped, then asked
"so, ask the PM?" instead of dispatching. These tests pin the definition in the always-loaded
rules, the skill, both adapters' routing rows, and the decision record.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RULES = REPO_ROOT / "src" / "overlay" / "rules.md"
SKILL = REPO_ROOT / "src" / "overlay" / "skills" / "trazo.md"
CLAUDE = REPO_ROOT / "src" / "adapters" / "CLAUDE.md"
AGENTS = REPO_ROOT / "src" / "adapters" / "AGENTS.md"
CODEX_MENU = REPO_ROOT / "src" / "adapters" / "codex" / "skills" / "menu" / "SKILL.md"
ADR = REPO_ROOT / ".trazo" / "project" / "adr" / "0029-the-front-door.md"


def _text(path: Path) -> str:
    return re.sub(r"\s+", " ", path.read_text(encoding="utf-8")).casefold()


def _front_door_section(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"^## Front door\n(.*?)(?=^## |\Z)", text, re.DOTALL | re.MULTILINE)
    assert match, f"{path.relative_to(REPO_ROOT)} has no '## Front door' section"
    return re.sub(r"\s+", " ", match.group(1)).casefold()


def test_rules_define_the_front_door():
    section = _front_door_section(RULES)
    for needle in (
        "the main session is the front door",
        "dispatches the pm",
        "starts the agents the pm records on issues",
        "reviewer",
        "security",
        "skeptic",
    ):
        assert needle in section, f"front door section lacks: {needle}"


def test_front_door_is_ready_to_act_and_asks_only_owner_decisions():
    section = _front_door_section(RULES)
    for needle in (
        "ready to act",  # no menu step before it works
        "does not print a menu and wait",
        "briefly",  # succinct
        "ready to run",  # suggests an action it can run, not homework
        "owner decisions",  # the only things it asks the owner
    ):
        assert needle in section, f"front door section lacks: {needle}"


def test_front_door_routes_requests_by_kind():
    section = _front_door_section(RULES)
    for needle in ("planning", "engineer", "tier:senior", "architect", "security", "skeptic"):
        assert needle in section, f"front door routing lacks: {needle}"


def test_the_trazo_skill_acts_instead_of_waiting():
    text = _text(SKILL)
    assert "you could say" not in text, "the menu homework line is still there"
    assert "front door" in text
    assert "dispatch the pm" in text
    assert "ready to act" in text


def test_both_adapters_route_whats_next_and_menu_to_the_front_door():
    claude_rows = [
        line.casefold()
        for line in CLAUDE.read_text(encoding="utf-8").splitlines()
        if line.startswith("|") and ("what's next" in line.lower() or "menu" in line.lower())
    ]
    assert claude_rows and all("front door" in row for row in claude_rows), claude_rows
    agents_rows = [
        line.casefold()
        for line in AGENTS.read_text(encoding="utf-8").splitlines()
        if line.startswith("|")
        and ("what is next" in line.lower() or "what can i do" in line.lower())
    ]
    assert agents_rows and all("front door" in row for row in agents_rows), agents_rows
    assert "front door" in _text(CLAUDE).split("## ", 1)[-1] or "## Front door" in (
        CLAUDE.read_text(encoding="utf-8")
    )
    assert "## Front door" in AGENTS.read_text(encoding="utf-8")


def test_the_codex_menu_skill_opens_the_front_door():
    assert "front door" in _text(CODEX_MENU)


def test_adr_0029_defines_the_front_door_and_extends_0025():
    text = _text(ADR)
    assert "front door" in text
    assert "0025" in text
    rule = re.search(r"^\*\*Rule:\*\*\s*(.+)$", ADR.read_text(encoding="utf-8"), re.MULTILINE)
    assert rule and rule.group(1).strip().casefold() != "none"
    statement = re.sub(r"\s+", " ", rule.group(1)).strip().casefold()
    assert statement in _text(RULES), "the ADR's Rule sentence is not in src/overlay/rules.md"


def test_the_release_is_0_3_1_with_a_changelog_entry():
    assert (REPO_ROOT / ".template" / "VERSION").read_text(encoding="utf-8").strip() == "0.3.1"
    changelog = (REPO_ROOT / ".template" / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## 0.3.1" in changelog and "#304" in changelog
