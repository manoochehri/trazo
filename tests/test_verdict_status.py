"""Guards for the trazo/verdict commit-status merge gate (issue #115, phase 1)."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CLAUDE = REPO_ROOT / ".claude"
ADAPTER = REPO_ROOT / "src" / "adapters" / "claude"


def read(base, sub, name):
    return (base / sub / name).read_text()


def test_reviewer_sets_verdict_status():
    t = read(CLAUDE, "agents", "reviewer.md")
    assert "context=trazo/verdict" in t
    assert "headRefOid" in t
    for state in ("pending", "success", "failure"):
        assert f"state={state}" in t
    assert "After, and only after, the review comment" in t


def test_security_sets_security_status():
    t = read(CLAUDE, "agents", "security.md")
    assert "context=trazo/security" in t
    assert "context=trazo/verdict" not in t
    assert "headRefOid" in t
    for state in ("pending", "success", "failure"):
        assert f"state={state}" in t


def test_engineer_and_pm_are_forbidden():
    for sub, name in (("commands", "eng.md"), ("commands", "pm.md"), ("agents", "pm.md")):
        t = read(CLAUDE, sub, name)
        assert "Never set the `trazo/verdict` or `trazo/security`" in t, name
    assert "engineer never sets these contexts" in read(CLAUDE, "commands", "work.md")


def test_work_and_check_pr_explain_gate():
    for name in ("work.md", "check-pr.md"):
        t = read(CLAUDE, "commands", name)
        assert "trazo/verdict" in t
        assert "resets" in t


def test_runbook_has_owner_step_and_caveat():
    t = (REPO_ROOT / ".trazo/project/RUNBOOK.md").read_text()
    assert "Require status checks" in t
    assert "`trazo/verdict`" in t
    assert "#44" in t


def test_adapter_copies_identical():
    for sub in ("agents", "commands"):
        for f in (CLAUDE / sub).glob("*.md"):
            assert (ADAPTER / sub / f.name).read_bytes() == f.read_bytes(), f.name
