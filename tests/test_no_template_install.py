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
    "AGENTS.md",
    "CONTRIBUTING.md",
    *sorted(str(p.relative_to(REPO_ROOT)) for p in (REPO_ROOT / "handbook").glob("*.md")),
]
# Historical records describe the old path; they are not instructions.
EXEMPT = {"handbook/changelog.md", "handbook/lessons.md"}

# `[^\n]*` would stop at a `\` line continuation; allow continuations explicitly.
TEMPLATE_CMD = re.compile(r"gh repo create(?:[^\n]|\\\n)*--template")


def _violations(rel: str, text: str) -> list[str]:
    found = []
    if TEMPLATE_CMD.search(text):
        found.append(f"{rel}: template install command")
    if "/generate" in text or "Use this template" in text:
        found.append(f"{rel}: 'Use this template' button or /generate link")
    return found


def test_no_template_install_instruction() -> None:
    for rel in DOCS:
        if rel in EXEMPT:
            continue
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        assert not _violations(rel, text)


def test_detector_matches_line_continuations() -> None:
    assert _violations("x", "gh repo create foo \\\n  --template x\n")
    assert _violations("x", "gh repo create foo --template x\n")
    assert not _violations("x", "gh repo create foo\n--template unrelated\n")


def test_install_docs_do_not_claim_the_released_tag_is_missing() -> None:
    """Once #100 releases v0.1.0, install docs must not say the tag is unavailable."""
    for rel in DOCS:
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        lowered = text.lower()
        if "install.sh install" in lowered:
            assert "no release exists yet" not in lowered, (
                f"{rel}: install instructions still say no release exists"
            )
            assert "works once `v0.1.0` is cut" not in lowered, (
                f"{rel}: install instructions still say v0.1.0 is not cut"
            )


def test_retired_template_tooling_is_gone() -> None:
    assert not (REPO_ROOT / "scripts" / "publish_template.sh").exists()


def test_guide_has_no_cloud_specific_remnants() -> None:
    guide = (REPO_ROOT / "handbook" / "guide.md").read_text(encoding="utf-8")
    assert "OIDC" not in guide
    assert "fly secrets" not in guide
