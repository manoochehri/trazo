"""Guards for the wait-for-CI, fix-obvious-failures, then review sequence (issue #216).

The sequence is prose in the canonical `/work` routine and engineer role, so nothing but a
test stops it from being edited back into "push and stop" -- the failure #215 exposed.
These checks assert the load-bearing pieces are still there, not the exact wording.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORK = REPO_ROOT / "src" / "overlay" / "skills" / "work.md"
ENGINEER = REPO_ROOT / "src" / "overlay" / "roles" / "engineer.md"


def _flat(path: Path) -> str:
    return re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))


def test_work_watches_checks_after_each_push() -> None:
    """The engineer waits for the PR's checks to finish instead of stopping at the push."""
    work = _flat(WORK)
    assert "## Watch CI, then wait for automatic review" in work
    assert "gh pr checks" in work
    assert "gh run watch" in work
    assert "gh run view" in work and "--log-failed" in work


def test_work_fixes_only_mechanical_failures() -> None:
    """Named mechanical causes are fixed on the same branch; the rest is not the engineer's call."""
    work = _flat(WORK)
    for cause in (
        "missing required field",
        "stale or colliding document number",
        "formatting or lint",
    ):
        assert cause in work, f"mechanical-failure list is missing {cause!r}"
    assert "same branch and pull request" in work


def test_work_fix_never_changes_scope_or_acceptance() -> None:
    work = _flat(WORK)
    assert re.search(
        r"change scope, behavior or acceptance criteria to make the check pass",
        work,
    )


def test_work_escalates_unclear_failures_to_needs_pm() -> None:
    """Unclear failures reuse the existing needs-pm handoff rather than a guessed fix."""
    work = _flat(WORK)
    assert "cause is not obvious" in work
    assert "--add-label needs-pm" in work
    assert "gh issue comment" in work
    assert "Do not guess at the fix" in work


def test_work_bounds_fix_attempts_per_check() -> None:
    assert re.search(r"at most 2 fix attempts per failing check", _flat(WORK))


def test_work_requests_review_only_after_checks_pass() -> None:
    """A complete, green change is marked ready to trigger automatic review."""
    work = _flat(WORK)
    assert re.search(r"All CI checks pass on a complete change.{0,80}automatic review loop", work)
    assert "mark the PR ready with `gh pr ready <number>`" in work


def test_work_waits_for_automatic_verdict_on_ready_and_fix_heads() -> None:
    """A ready PR and each fix push use the automatic workflow on their own SHA."""
    work = _flat(WORK)
    assert "marked ready" in work
    assert "after each fix push" in work
    assert "Never report the work complete while the exact head SHA has no terminal verdict" in work
    assert "If the workflow run is skipped" in work
    assert "Do not launch a manual reviewer fallback" in work


def test_work_does_not_review_an_incomplete_change() -> None:
    """Draft and intermediate work stay out of automatic review until the change is complete."""
    work = _flat(WORK)
    assert "return to step 5" in work
    assert "on a complete change" in work
    assert "open a **draft** pull request" in work
    assert "Draft and intermediate work is skipped" in work


def test_work_keeps_merge_gate_contexts_off_the_engineer() -> None:
    assert "Never set `trazo/verdict` or `trazo/security`" in _flat(WORK)


def test_engineer_role_states_the_ci_sequence() -> None:
    role = _flat(ENGINEER)
    assert "watch the pull request's checks" in role
    assert "Ask the reviewer only once checks pass" in role
    assert "needs-pm" in role
