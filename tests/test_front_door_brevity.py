"""The front door's chat reply is at most 3 short lines (issue #278).

Evidence and reasoning belong on the issue or pull request, not in chat. The rule lives once in
the tool-neutral rules, and the skill and adapters must not restate a longer budget.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "src" / "overlay" / "rules.md"
SKILL = ROOT / "src" / "overlay" / "skills" / "trazo.md"
ADAPTERS = [ROOT / "src" / "adapters" / "CLAUDE.md", ROOT / "src" / "adapters" / "AGENTS.md"]


def _flat(path: Path) -> str:
    return re.sub(r"\s+", " ", path.read_text(encoding="utf-8")).casefold()


def _section(path: Path, heading: str) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(rf"^## {heading}\n(.*?)(?=^## |\Z)", text, re.DOTALL | re.MULTILINE)
    assert match, f"no '## {heading}' section"
    return re.sub(r"\s+", " ", match.group(1)).casefold()


def test_rules_cap_chat_replies_at_three_short_lines():
    section = _section(RULES, "Front door")
    assert "at most 3 short lines" in section
    assert "a decision, an answer to the owner's question, or a single command" in section
    assert "evidence, status and reasoning go on the issue or pull request" in section


def test_skill_matches_the_rule_and_drops_the_long_template():
    text = _flat(SKILL)
    assert "at most 3 short lines" in text
    assert "8 lines" not in text
    assert "**doing:**" not in text and "**blocked on you:**" not in text


def test_adapters_defer_to_the_rule_instead_of_a_longer_budget():
    for path in ADAPTERS:
        text = _flat(path)
        assert "at most 3 short lines" in text, path.name
        assert not re.search(r"\b([4-9]|1\d) (short )?lines", text), path.name


def test_front_door_owns_routing_labels_and_tells_after():
    section = _section(RULES, "Ask before guessing")
    assert "routing labels, tier assignments and milestone-neutral issue bookkeeping" in section
    assert "front door's own call" in section
