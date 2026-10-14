"""Guards for the trazo/verdict commit-status merge gate (issue #115, phase 1)."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ADAPTER = REPO_ROOT / "src" / "adapters" / "claude"
ROLES = REPO_ROOT / "src" / "overlay" / "roles"


def read(base, sub, name):
    return (base / sub / name).read_text()


def test_reviewer_sets_verdict_status():
    t = read(ROLES, "", "reviewer.md")
    assert "context=trazo/verdict" in t
    assert "headRefOid" in t
    for state in ("pending", "success", "failure"):
        assert f"state={state}" in t
    assert "After, and only after, the review comment" in t


def test_security_sets_security_status():
    t = read(ROLES, "", "security.md")
    assert "context=trazo/security" in t
    assert "context=trazo/verdict" not in t
    assert "headRefOid" in t
    for state in ("pending", "success", "failure"):
        assert f"state={state}" in t


def test_engineer_and_pm_are_forbidden():
    for sub, name in (("commands", "eng.md"), ("commands", "pm.md"), ("agents", "pm.md")):
        assert ".trazo/roles/" in read(ADAPTER, sub, name) or ".trazo/ADVISOR.md" in read(
            ADAPTER, sub, name
        )
    work_skill = (REPO_ROOT / "src/overlay/skills/work.md").read_text()
    assert "engineer never sets these contexts" in work_skill


def test_work_and_check_pr_explain_gate():
    for name in ("work.md", "check-pr.md"):
        t = read(REPO_ROOT / "src/overlay/skills", "", name)
        assert "trazo/verdict" in t
        assert "resets" in t


def test_work_uses_reviewer_without_requiring_hosted_automation():
    work_skill = (REPO_ROOT / "src/overlay/skills/work.md").read_text()

    assert "open a **draft** pull request" in work_skill
    assert "gh pr ready <number>" in work_skill
    assert "after each push that addresses review findings" in work_skill
    assert "optional" in work_skill
    assert "must not block `/work`" in work_skill
    assert "reviewer subagent available in this working session" in work_skill
    assert "exact current head" in work_skill
    assert "trazo/verdict" in work_skill
    assert "failure" in work_skill
    assert "2 consecutive failed review rounds" in work_skill
    assert "tier:senior" in work_skill
    assert "Do not require an API key for native reviewer subagents" in work_skill


def test_work_preserves_owner_question_guidance():
    work_skill = (REPO_ROOT / "src/overlay/skills/work.md").read_text()
    assert "Write the question in plain language" in work_skill
    assert "two or three options each with a pro and a con" in work_skill


def test_runbook_has_owner_step_and_caveat():
    t = (REPO_ROOT / ".trazo/project/RUNBOOK.md").read_text()
    assert "Require status checks" in t
    assert "`trazo/verdict`" in t
    assert "#44" in t


def test_status_write_exception_is_narrow():
    for name, ctx, other in (
        ("reviewer.md", "trazo/verdict", "trazo/security"),
        ("security.md", "trazo/security", "trazo/verdict"),
    ):
        t = read(ROLES, "", name)
        assert "exactly two writes allowed" in t, name
        assert f"for your own context (`{ctx}`) and no other" in t, name
        assert "gh pr review --comment" in t, name
        assert other not in t.split("Commit status")[0], name
        assert "gh repo view --json nameWithOwner" in t, name


def test_security_status_only_after_review_comment():
    assert "After, and only after, the review comment" in read(ROLES, "", "security.md")
