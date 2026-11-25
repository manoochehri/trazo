"""#328 step 1: the status workflow is manual-only, read-only, and ships to hosts."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WF = REPO_ROOT / ".github/workflows/status.yml"


def test_workflow_is_dispatch_only_and_read_only():
    text = WF.read_text()
    assert "workflow_dispatch" in text
    for trigger in ("schedule:", "pull_request", "push:"):
        assert trigger not in text
    assert "contents: read" in text and "issues: read" in text and "pull-requests: read" in text
    assert ": write" not in text
    assert "persist-credentials: false" in text
    assert "scripts/gen_status.py" in text and "upload-artifact" in text


def test_shipped_copies_are_identical():
    for rel in (".github/workflows/status.yml", "scripts/gen_status.py"):
        a = (REPO_ROOT / "src/harness" / rel).read_bytes()
        assert a == (REPO_ROOT / rel).read_bytes(), rel
