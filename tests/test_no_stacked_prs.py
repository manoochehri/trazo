"""Issue #155: no stacked PR guidance or CI guard may drift away."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_no_stacked_pull_requests_are_checked_at_ci_and_workflow_layers() -> None:
    ci = _read(".github/workflows/ci.yml")
    work = _read("src/overlay/skills/work.md")
    review = _read("src/overlay/roles/reviewer.md")
    check_pr = _read("src/overlay/skills/check-pr.md")
    rules = _read("src/overlay/rules.md")

    assert "github.base_ref" in ci
    assert "github.event.repository.default_branch" in ci
    assert "origin/<default-branch>" in work
    assert "gh pr edit <number> --base <default-branch>" in work
    assert "A mismatch is must-fix" in review
    assert "differs from the repository's default branch is not mergeable" in check_pr
    assert "Do not\nstack pull requests" in rules


def test_automatic_branch_deletion_is_checked_and_left_to_the_owner() -> None:
    ci = _read(".github/workflows/ci.yml")
    kickoff = _read("src/overlay/skills/kickoff.md")
    start = _read("src/overlay/skills/start.md")
    security = _read("src/overlay/roles/security.md")
    installer = _read("scripts/install.sh")

    assert "delete_branch_on_merge=true" in kickoff
    assert ".delete_branch_on_merge" in start
    assert "do not change the setting yourself" in start
    assert "delete_branch_on_merge" in security
    assert "Automatically delete head branches" in installer
    assert "github.event_name == 'pull_request'" in ci
    assert "GH_TOKEN: ${{ github.token }}" in ci
    assert "gh api \"repos/$REPOSITORY\" --jq '.delete_branch_on_merge'" in ci
    assert '!= "true"' in ci
