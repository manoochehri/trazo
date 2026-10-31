"""CODEOWNERS must cover the files that define the review gates and agent authority (#231).

Security review of PRs #229, #251 and #267 found that rules, roles, ADRs, agent instruction files
and the verdict classifier were editable without the owner's review. This pins the paths that must
stay covered. It checks the file only; making GitHub enforce it is #45.
"""

from pathlib import Path

CODEOWNERS = Path(__file__).resolve().parent.parent / ".github" / "CODEOWNERS"

MUST_BE_COVERED = [
    "src/overlay/rules.md",
    "src/overlay/roles/reviewer.md",
    "src/overlay/skills/work.md",
    ".trazo/rules.md",
    ".trazo/roles/security.md",
    ".trazo/skills/work.md",
    ".trazo/project/adr/0003-review-security-github-tracked.md",
    ".claude/agents/security.md",
    "CLAUDE.md",
    "AGENTS.md",
    "scripts/report_verdict.py",
    "Makefile",
    "pyproject.toml",
]


def _patterns() -> list[str]:
    patterns = []
    for line in CODEOWNERS.read_text(encoding="utf-8").splitlines():
        parts = line.split("#", 1)[0].split()
        if parts:
            patterns.append(parts[0])
    return patterns


def _covered(pattern: str, path: str) -> bool:
    """A directory pattern (trailing slash) covers everything under it; otherwise the exact path."""
    anchored = pattern.lstrip("/")
    if anchored.endswith("/"):
        return path.startswith(anchored)
    return path == anchored


def test_review_gate_and_authority_files_are_covered() -> None:
    patterns = _patterns()
    uncovered = [p for p in MUST_BE_COVERED if not any(_covered(pat, p) for pat in patterns)]
    assert not uncovered, f"CODEOWNERS does not cover: {uncovered}"
