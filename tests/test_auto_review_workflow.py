"""Guards for automatic PR review (issue #204, ADR 0017)."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "review.yml"


def workflow_text():
    return WORKFLOW.read_text()


def test_review_runs_on_pr_open_and_push_without_a_human_trigger():
    t = workflow_text()
    assert "pull_request:" in t
    for event in ("opened", "synchronize", "ready_for_review"):
        assert event in t


def test_drafts_are_not_reviewed():
    assert "github.event.pull_request.draft == false" in workflow_text()


def test_only_same_repo_branches_get_the_api_key():
    # Forked PRs must not run with the API key: their diff is untrusted input.
    assert "github.event.pull_request.head.repo.full_name == github.repository" in workflow_text()


def test_owner_kill_switch_disables_review_without_a_code_change():
    assert "vars.AUTO_REVIEW_ENABLED == 'true'" in workflow_text()


def test_a_review_that_errors_ends_red_never_pending():
    t = workflow_text()
    assert "if: failure()" in t
    assert "state=failure" in t


def test_the_workflow_never_sets_a_success_verdict():
    # Only the reviewer subagent may grant trazo/verdict success (#115).
    # The workflow may only tighten the gate: failure on error, pending on start.
    assert "state=success" not in workflow_text()
    assert "state=failure" in workflow_text()


def test_review_is_skipped_when_the_head_already_has_a_terminal_verdict():
    t = workflow_text()
    assert "context=trazo/verdict" in t
    assert "skip" in t


def test_sensitive_paths_trigger_the_security_subagent():
    t = workflow_text()
    for path in (".github/workflows", "CODEOWNERS", "pyproject.toml", "uv.lock"):
        assert path in t
    assert "security" in t
