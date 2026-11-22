"""Guards for automatic PR review (issue #204, ADR 0017).

The workflow is text, not parsed YAML: the project has no YAML dependency, so jobs are
read by their two-space indentation.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "review.yml"
ADR = REPO_ROOT / ".trazo/project/adr/0017-automatic-review-on-push.md"

REVIEWER_ACTION_PIN = "anthropics/claude-code-action@1d6de8cb0c237e7c15e9e1bdf973826ebae490cc"
CHECKOUT_PIN = "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"


def workflow_text():
    return WORKFLOW.read_text()


def job(name):
    lines = workflow_text().splitlines()
    start = lines.index(f"  {name}:")
    end = next(
        (i for i in range(start + 1, len(lines)) if re.match(r"^  \S", lines[i])),
        len(lines),
    )
    return "\n".join(lines[start:end])


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


def test_agent_settings_come_from_base_and_pr_head_is_data_only():
    # The PR cannot supply the reviewer's settings, hooks or agent instructions.
    review = job("review")
    assert "ref: ${{ github.event.pull_request.base.sha }}" in review
    assert "persist-credentials: false" in review
    assert "--setting-sources project" in review


def test_reviewer_diff_uses_the_requested_immutable_head_sha():
    review = job("review")
    prompt = review.split("prompt: |")[1].split("claude_args")[0]
    assert "ref: ${{ github.event.pull_request.head.sha }}" in review
    assert "path: reviewed-head" in review
    assert "fetch-depth: 0" in review
    assert 'git -C reviewed-head diff --no-ext-diff "$BASE_SHA...$HEAD_SHA"' in prompt
    assert "gh pr diff" not in prompt


def test_agent_loads_only_base_settings():
    # The checkout is the trusted base SHA, so project settings are the base's own.
    review = job("review")
    assert "--setting-sources project" in review
    assert "--setting-sources user" not in review


def allowed_tools():
    m = re.search(r'--allowedTools "([^"]*)"', job("review"))
    assert m, "review job has no --allowedTools list"
    return [t.strip() for t in m.group(1).split(",")]


def test_agent_allowlist_has_no_bare_file_tools_or_git_history():
    tools = allowed_tools()
    for bare in ("Read", "Grep", "Glob"):
        assert bare not in tools, f"bare {bare} lets the agent read outside the workspace"
    for scoped in ("Read(./**)", "Grep(./**)", "Glob(./**)"):
        assert scoped in tools
    assert "Bash(git -C reviewed-head diff:*)" in tools
    assert not any("gh pr diff" in tool for tool in tools)
    review = job("review")
    assert "git log" not in review
    assert "git show" not in review


def test_agent_denies_host_secrets_and_runner_temp_reads():
    review = job("review")
    m = re.search(r'--disallowedTools "([^"]*)"', review)
    assert m, "review job has no --disallowedTools list"
    denied = m.group(1)
    for rule in (
        "Read(//proc/**)",
        "Read(//sys/**)",
        "Read(//home/runner/work/_temp/**)",
        "Read(~/**)",
        "Read(//tmp/**)",
    ):
        assert rule in denied


def test_agent_prompt_never_reads_pr_comments():
    prompt = job("review").split("prompt: |")[1].split("claude_args")[0]
    assert "gh pr view --comments" in prompt  # named only as a command the agent must not run
    stripped = prompt.replace("gh pr view --comments", "").replace("gh pr review --comment", "")
    assert "comments" not in stripped
    assert "do not run" in prompt.lower()


def test_agent_job_cannot_write_commit_statuses():
    review = job("review")
    assert "statuses: write" not in review
    assert "gh api" not in review


def test_agent_job_has_no_pytest_or_pr_code_execution_in_its_allowlist():
    review = job("review")
    assert "uv run pytest" not in review
    assert 'CLAUDE_CODE_SUBPROCESS_ENV_SCRUB: "1"' in review


def test_adr_0020_supersedes_the_success_clause_and_keeps_0017():
    adr = (REPO_ROOT / ".trazo/project/adr/0020-verdict-success-from-bot-review.md").read_text()
    assert "Supersedes" in adr
    assert "0017" in adr
    assert "What the workflow may write" in adr
    assert "#213" in adr
    assert "github-actions[bot]" in adr
    assert "accepted" in adr.lower()


def test_review_timeout_sits_on_the_job_that_can_be_cancelled_not_a_step_that_never_runs():
    assert "timeout-minutes:" in job("review")


def test_actions_are_pinned_to_commits():
    t = workflow_text()
    assert REVIEWER_ACTION_PIN in t
    assert CHECKOUT_PIN in t
    assert "@v7" not in t
    assert "@v1" not in t


def test_sensitive_paths_trigger_the_security_subagent():
    prompt = job("review")
    for path in (".github/workflows", "CODEOWNERS", "pyproject.toml", "uv.lock"):
        assert path in prompt
    assert "security subagent" in prompt


def test_adr_states_security_never_sets_the_verdict_context():
    text = ADR.read_text()
    assert "trazo/security" in text
    assert "security subagent sets `trazo/verdict`" not in text


def test_adr_states_every_push_to_a_non_draft_pr_is_reviewed():
    assert "every push to a non-draft pr" in ADR.read_text().lower()
