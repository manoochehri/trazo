"""Review output shape for reviewer, skeptic and security roles (issue #195).

Reviews were long prose: process narration sat above the actions, and rule-mandated
items landed under Suggestions. The role files now prescribe one shape: the verdict
word on line 1, Must-fix bullets, at most three Suggestions, and the audit trail in a
collapsed `<details>` block. These tests hold the template in place in the canonical
role files, which are the only operative source (the adapters point at them).
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return " ".join((ROOT / path).read_text(encoding="utf-8").split())


def test_reviewer_replies_in_the_bulleted_template():
    reviewer = _read("src/overlay/roles/reviewer.md")
    assert "verdict word as line 1" in reviewer
    assert "**Must-fix:**" in reviewer
    assert "one line each" in reviewer
    assert "at most 3 **Suggestions**" in reviewer
    assert "<details>" in reviewer
    assert "about 15 lines" in reviewer


def test_skeptic_replies_with_failed_bar_items_and_folded_evidence():
    skeptic = _read("src/overlay/roles/skeptic.md")
    assert "failed bar items by number" in skeptic
    assert "one-line fix" in skeptic
    assert "<details>" in skeptic
    assert "about 15 lines" in skeptic


def test_security_replies_in_the_same_shape_when_posting_on_a_pr():
    security = _read("src/overlay/roles/security.md")
    assert "verdict word as line 1" in security
    assert "**Must-fix:**" in security
    assert "at most 3 **Suggestions**" in security
    assert "<details>" in security
    assert "about 15 lines" in security
