"""Keep role attribution consistent wherever agents post to GitHub (#187)."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RULES = REPO_ROOT / "src/overlay/rules.md"
CLAUDE = REPO_ROOT / "src/adapters/CLAUDE.md"
CODEX = REPO_ROOT / "src/adapters/AGENTS.md"
CODEX_WORK = REPO_ROOT / "src/adapters/codex/skills/work/SKILL.md"
REVIEWER = REPO_ROOT / "src/overlay/roles/reviewer.md"
HANDBOOK_TEAM = REPO_ROOT / "handbook/team.md"


def _flat(path: Path) -> str:
    return re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))


def test_shared_rule_defines_footer_fields_sources_and_missing_metadata() -> None:
    rules = _flat(RULES)
    for required in (
        "## Attribute role-authored GitHub posts",
        "each role-authored issue description or comment",
        "`gh issue create`",
        "`gh issue edit --body`",
        "`gh issue comment`",
        "`gh pr review --comment`",
        "role",
        "adapter",
        "model",
        "session ID",
        "Omit unknown fields",
        "instead of guessing",
        "prefer a role's agent ID when exposed",
        "Label the included identifier as `agent` or `session`",
        "Do not append a second footer",
        "GitHub still records the shared account",
        "self-reported",
    ):
        assert required in rules, f"shared attribution rule is missing {required!r}"


def test_native_adapters_name_model_and_id_sources_and_fallbacks() -> None:
    claude = _flat(CLAUDE)
    codex = _flat(CODEX) + " " + _flat(CODEX_WORK)
    assert "session_id" in claude and "agent_id" in claude
    assert "Claude Code hook input includes `session_id`" in claude
    assert "Headless JSON output" in claude and "Agent SDK messages" in claude
    assert "active model" in claude and "only when" in claude
    assert "CODEX_THREAD_ID" not in codex, "do not rely on undocumented Codex internals"
    assert "CODEX_SESSION_ID" not in codex, "do not rely on undocumented Codex internals"
    assert "session or agent ID" in codex and "active model" in codex and "Omit" in codex
    assert "`AGENTS.md` as the adapter label" in codex


def test_reviewer_verdict_remains_first_line_before_footer() -> None:
    reviewer = _flat(REVIEWER)
    assert "verdict word as the first line" in reviewer
    assert "append the role attribution footer after the findings" in reviewer


def test_handbook_documents_adapter_coverage_and_attribution_limit() -> None:
    team = _flat(HANDBOOK_TEAM)
    assert "role attribution footer" in team
    for adapter in ("Claude Code", "Codex", "AGENTS.md"):
        assert adapter in team, f"handbook does not cover {adapter}"
    assert "not an independently verified identity" in team
