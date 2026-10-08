"""Keep project decision discovery in the always-loaded startup path (#113)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_core_rule_reads_referenced_project_decisions_before_writing():
    rules = _read("src/overlay/rules.md")
    assert "Before the first file write" in rules
    assert "document map" in rules
    assert "read applicable standing records" in rules
    assert all(path in rules for path in ("decisions/", "rules/", "adr/"))


def test_startup_workflow_and_adapters_surface_decision_discovery():
    start = _read("src/overlay/skills/start.md")
    agents_adapter = _read("src/adapters/AGENTS.md")
    claude_adapter = _read("src/adapters/CLAUDE.md")

    assert "before the first file write" in start.lower()
    assert "document map" in start.lower()
    assert "before the first file write" in agents_adapter.lower()
    assert "document map" in agents_adapter.lower()
    assert "before the first file write" in claude_adapter.lower()
    assert "document map" in claude_adapter.lower()
