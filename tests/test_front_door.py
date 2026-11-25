"""The main session is the Coordinator: it acts, it does not print a menu and wait (issue #304).

v0.3.0 shipped ADR 0025 ("the front door starts the agent") but never defined the main session's
action loop. ADR 0029 is historical; the active name is Coordinator.
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


def _coordinator_section(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"^## Coordinator\n(.*?)(?=^## |\Z)", text, re.DOTALL | re.MULTILINE)
    assert match, f"{path.relative_to(REPO_ROOT)} has no '## Coordinator' section"
    return re.sub(r"\s+", " ", match.group(1)).casefold()


def test_rules_define_the_coordinator():
    section = _coordinator_section(RULES)
    for needle in (
        "the main session is the trazo coordinator",
        "dispatches the pm",
        "starts the agents the pm records on issues",
        "reviewer",
        "security",
        "skeptic",
    ):
        assert needle in section, f"front door section lacks: {needle}"


def test_coordinator_is_ready_to_act_and_escalates_only_irreversible_decisions():
    section = _coordinator_section(RULES)
    for needle in (
        "ready to act",  # no menu step before it works
        "does not print a menu and wait",
        "briefly",  # succinct
        "single command",  # at most one command, not homework
        "retry",
        "repair",
        "merge",
        "close-loop",
        "scope",
        "spend",
        "charter",
        "deploy",
        "permissions",
    ):
        assert needle in section, f"Coordinator section lacks: {needle}"
    assert "owner decisions (merge" not in section


def test_coordinator_routes_requests_by_kind():
    section = _coordinator_section(RULES)
    for needle in ("planning", "engineer", "tier:senior", "architect", "security", "skeptic"):
        assert needle in section, f"Coordinator routing lacks: {needle}"


def test_the_trazo_skill_acts_instead_of_waiting():
    text = _text(SKILL)
    assert "you could say" not in text, "the menu homework line is still there"
    assert "trazo coordinator" in text
    assert "dispatch the pm" in text
    assert "ready to act" in text
    assert "blocked on you" not in text
    assert "ask the owner only about scope" in text


def test_both_adapters_route_whats_next_and_menu_to_the_coordinator():
    claude_rows = [
        line.casefold()
        for line in CLAUDE.read_text(encoding="utf-8").splitlines()
        if line.startswith("|") and ("what's next" in line.lower() or "menu" in line.lower())
    ]
    assert claude_rows and all("coordinator" in row for row in claude_rows), claude_rows
    agents_rows = [
        line.casefold()
        for line in AGENTS.read_text(encoding="utf-8").splitlines()
        if line.startswith("|")
        and ("what is next" in line.lower() or "what can i do" in line.lower())
    ]
    assert agents_rows and all("coordinator" in row for row in agents_rows), agents_rows
    assert "## Coordinator" in CLAUDE.read_text(encoding="utf-8")
    assert "## Coordinator" in AGENTS.read_text(encoding="utf-8")


def test_the_codex_menu_skill_opens_the_coordinator():
    text = _text(CODEX_MENU)
    assert "coordinator" in text
    assert "routine work" in text


def test_adr_0029_remains_historical_and_the_active_rule_is_coordinator():
    text = _text(ADR)
    assert "front door" in text  # historical wording is preserved
    assert "0025" in text
    rule = re.search(r"^\*\*Rule:\*\*\s*(.+)$", ADR.read_text(encoding="utf-8"), re.MULTILINE)
    assert rule and rule.group(1).strip().casefold() != "none"
    assert "## Coordinator" in (RULES.read_text(encoding="utf-8"))


def test_coordinator_has_no_routine_owner_blocker_template():
    for path in (RULES, SKILL, CLAUDE, AGENTS, CODEX_MENU):
        text = _text(path)
        assert "blocked on you" not in text, f"stale blocker template in {path}"
        assert "owner merges" not in text, f"stale owner-merge guidance in {path}"


def test_the_0_3_1_release_has_a_changelog_entry_and_the_version_is_not_older():
    version = (REPO_ROOT / ".template" / "VERSION").read_text(encoding="utf-8").strip()
    assert tuple(int(part) for part in version.split(".")) >= (0, 3, 1)
    changelog = (REPO_ROOT / ".template" / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## 0.3.1" in changelog and "#304" in changelog
