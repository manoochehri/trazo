"""The `gh repo create --template` install path is retired (#107); the installer replaces it.

That path was the one vector by which a host received this repository's own charter, ADRs,
STATUS and PLAN (#77). These assertions keep it from quietly coming back in a rewrite of the
user-facing docs.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS = [
    "README.md",
    "CONTRIBUTING.md",
    *sorted(str(p.relative_to(REPO_ROOT)) for p in (REPO_ROOT / "handbook").glob("*.md")),
]
# Historical records describe the old path; they are not instructions.
EXEMPT = {"handbook/changelog.md", "handbook/lessons.md"}


def test_no_template_install_instruction() -> None:
    for rel in DOCS:
        if rel in EXEMPT:
            continue
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        assert not re.search(r"gh repo create[^\n]*--template", text), (
            f"{rel}: template install command"
        )
        assert "/generate" not in text, f"{rel}: 'Use this template' /generate link"
        assert "Use this template" not in text, f"{rel}: 'Use this template' button"


def test_retired_template_tooling_is_gone() -> None:
    assert not (REPO_ROOT / "scripts" / "publish_template.sh").exists()


def test_guide_has_no_cloud_specific_remnants() -> None:
    guide = (REPO_ROOT / "handbook" / "guide.md").read_text(encoding="utf-8")
    assert "OIDC" not in guide
    assert "fly secrets" not in guide
