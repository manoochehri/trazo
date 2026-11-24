"""CODEOWNERS protects what governs agents, and the drive classifier agrees (issue #281).

Owner decision 2026-11-19: agents may not change their own prompts and roles; everything else is
agentic. Until #212 lands, workflows, scripts/install.sh and the charter stay protected too.
"""

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


report_verdict = _load("report_verdict", REPO_ROOT / "scripts" / "report_verdict.py")
_helpers = _load("codeowners_helpers", REPO_ROOT / "tests" / "test_codeowners.py")
_rules = _helpers._rules


def _covers(pattern, path):
    """A directory pattern covers everything under it; a file pattern covers that file."""
    return _helpers._covers(pattern, path) or (
        pattern.endswith("/") and path.startswith(pattern.lstrip("/"))
    )


# A representative file under each protected location.
PROTECTED = {
    "src/overlay/rules.md",
    "src/adapters/CLAUDE.md",
    ".trazo/rules.md",
    ".trazo/roles/engineer.md",
    ".trazo/skills/work.md",
    ".trazo/ADVISOR.md",
    ".trazo/ARCHITECTURE.md",
    ".trazo/templates/skeptic_bar.md",
    ".trazo/project/SKEPTIC_BAR.md",
    ".trazo/hooks/pm_bash_guard.py",
    ".trazo/hooks/agent_role_guard.py",
    ".gitleaks.toml",
    ".claude/agents/pm.md",
    ".claude/commands/eng.md",
    ".claude/settings.json",
    ".codex/config.toml",
    ".agents/skills/work.md",
    "AGENTS.md",
    "CLAUDE.md",
    ".github/CODEOWNERS",
    # Kept until #212 lands (a PR that edits review.yml runs its own copy).
    ".github/workflows/review.yml",
    ".github/workflows/report.yml",
    "scripts/install.sh",
    ".trazo/project/charter/charter.md",
}


def test_every_protected_path_is_in_codeowners():
    patterns = [pattern for pattern, _ in _rules()]
    missing = [p for p in sorted(PROTECTED) if not any(_covers(x, p) for x in patterns)]
    assert not missing, f"not covered by CODEOWNERS: {missing}"


def test_classifier_agrees_with_codeowners():
    """Each protected path is sensitive to the drive classifier even without CODEOWNERS."""
    not_sensitive = [p for p in sorted(PROTECTED) if not report_verdict.is_sensitive_path(p, [])]
    assert not not_sensitive, f"classifier misses: {not_sensitive}"


def test_classifier_is_stricter_than_codeowners_on_purpose():
    """The drive classifier is the authority for auto-merge and stays stricter: ADRs and
    scripts/ are agentic in CODEOWNERS but the drive never auto-merges them."""
    for path in (".trazo/project/adr/0001-record-decisions.md", "scripts/report_verdict.py"):
        assert report_verdict.is_sensitive_path(path, []), path


def test_agentic_paths_are_not_protected():
    patterns = [pattern for pattern, _ in _rules()]
    for path in (
        ".trazo/project/adr/0001-record-decisions.md",
        ".trazo/project/STATUS.md",
        "tests/test_x.py",
    ):
        assert not any(_covers(x, path) for x in patterns), f"{path} should be agentic"
