"""The senior engineer tier ships on every adapter it is mapped to (issue #203, ADR 0016, 0018).

ADR 0016 maps `senior-eng` to Sonnet on Claude Code and `gpt-6.1-sol` on Codex. ADR 0018
routes work to it with the `tier:senior` label and makes the reviewer check that label until
labeling is automated. These tests hold each of those in place, so the mapping cannot drift
from the decision record.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ROLE = REPO_ROOT / "src/overlay/roles/senior-engineer.md"
ROLES_README = REPO_ROOT / "src/overlay/roles/README.md"
REVIEWER = REPO_ROOT / "src/overlay/roles/reviewer.md"
CLAUDE_COMMAND = REPO_ROOT / "src/adapters/claude/commands/senior-eng.md"
CODEX_AGENT = REPO_ROOT / "src/adapters/codex/agents/senior-engineer.toml"


def _flat(path: Path) -> str:
    return re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))


def test_canonical_senior_role_exists_and_is_listed() -> None:
    assert ROLE.is_file(), "src/overlay/roles/senior-engineer.md is missing"
    assert "[Senior Engineer](senior-engineer.md)" in ROLES_README.read_text(encoding="utf-8")


def test_senior_role_keeps_eng_default_and_the_review_separation() -> None:
    role = _flat(ROLE)
    assert "`tier:senior`" in role
    assert "eng" in role and "default" in role
    assert "does not review" in role or "do not review" in role
    assert "reviewer" in role and "security" in role and "skeptic" in role
    assert "Do not merge" in role or "do not merge" in role
    assert "trazo/verdict" in role and "trazo/security" in role


def test_senior_role_escalates_on_the_issue_and_never_through_the_owner() -> None:
    role = _flat(ROLE)
    assert "2 consecutive" in role or "two consecutive" in role
    assert "on the issue" in role
    assert "never by asking the owner" in role
    assert "`needs-pm`" in role and "`needs-decision`" in role


def test_claude_senior_command_runs_sonnet_on_the_canonical_role() -> None:
    text = CLAUDE_COMMAND.read_text(encoding="utf-8")
    frontmatter = text.split("---", 2)[1]
    assert re.search(r"^model: sonnet$", frontmatter, re.MULTILINE)
    assert ".trazo/roles/senior-engineer.md" in text


def test_codex_senior_agent_runs_sol_on_the_canonical_role() -> None:
    text = CODEX_AGENT.read_text(encoding="utf-8")
    assert 'model = "gpt-6.1-sol"' in text
    assert ".trazo/roles/senior-engineer.md" in text


def test_reviewer_checks_the_tier_senior_label_and_path_rules() -> None:
    reviewer = _flat(REVIEWER)
    assert "`tier:senior`" in reviewer
    for path in ("CODEOWNERS", ".github/workflows/", "src/", ".trazo/"):
        assert path in reviewer, path
    assert "until labeling is automated" in reviewer
