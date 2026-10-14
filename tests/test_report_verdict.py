"""Behaviour of the report job's verdict decision (issue #213, ADR 0020).

The report job turns a bot review into trazo/verdict. These tests pin the decision on
fixtures, so the rule is checked without running GitHub Actions.

Fixture fields are the ones the script reads from GitHub's pull request review object
(https://docs.github.com/en/rest/pulls/reviews: id, body, commit_id, submitted_at, user.login).
The security first lines (`PASS (security re-review at <sha>)`, `FAIL (...)`) match the real
reviews on PR #210, checked with `gh api repos/manoochehri/trazo/pulls/210/reviews`.
"""

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "report_verdict.py"

spec = importlib.util.spec_from_file_location("report_verdict", SCRIPT)
report_verdict = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report_verdict)

HEAD = "a" * 40
OTHER = "b" * 40
STARTED = "2026-10-13T10:00:00Z"
BOT = "github-actions[bot]"
SECURITY_PASS = "PASS (security re-review at " + HEAD + ")\n\nNo findings."
SECURITY_FAIL = "FAIL (security re-review at " + HEAD + ")\n\n- must-fix"


def review(
    body,
    login=BOT,
    commit=HEAD,
    submitted="2026-10-13T10:05:00Z",
    rid=1,
    reviewed_head=HEAD,
):
    if reviewed_head is not None:
        body = f"{body}\n\nReviewed-Head: {reviewed_head}"
    return {
        "id": rid,
        "body": body,
        "commit_id": commit,
        "submitted_at": submitted,
        "user": {"login": login},
    }


def decide(reviews, sensitive=False):
    return report_verdict.decide(reviews, HEAD, STARTED, BOT, sensitive)


def test_bot_merge_on_head_after_run_start_sets_success():
    state, reason = decide([review("merge\n\nNo must-fix items.")])
    assert state == "success"
    assert reason


def test_merge_after_fixes_sets_failure():
    assert decide([review("merge after fixes\n\n- fix x")])[0] == "failure"


def test_dont_merge_sets_failure():
    assert decide([review("don't merge\n\n- broken")])[0] == "failure"


def test_no_review_sets_failure():
    assert decide([])[0] == "failure"


def test_stale_review_on_an_earlier_head_does_not_count():
    assert decide([review("merge", commit=OTHER)])[0] == "failure"


def test_merge_review_that_names_an_older_head_does_not_credit_current_head():
    stale_review = review("merge", reviewed_head=OTHER)
    assert decide([stale_review])[0] == "failure"


def test_merge_review_without_reviewed_head_marker_does_not_count():
    unbound_review = review("merge", reviewed_head=None)
    assert decide([unbound_review])[0] == "failure"


def test_review_submitted_before_this_run_started_does_not_count():
    assert decide([review("merge", submitted="2026-10-13T09:59:59Z")])[0] == "failure"


def test_non_bot_merge_review_does_not_count():
    assert decide([review("merge", login="someone-else")])[0] == "failure"


def test_owner_account_merge_review_does_not_count():
    assert decide([review("merge", login="manoochehri")])[0] == "failure"


def test_bold_or_padded_verdict_is_not_exact_merge():
    assert decide([review("**merge**")])[0] == "failure"
    assert decide([review("Merge")])[0] == "failure"


def test_empty_body_sets_failure():
    assert decide([review("")])[0] == "failure"
    assert decide([review(None)])[0] == "failure"


def test_latest_bot_review_wins():
    earlier_merge = review("merge", submitted="2026-10-13T10:05:00Z", rid=1)
    later_fixes = review("merge after fixes", submitted="2026-10-13T10:20:00Z", rid=2)
    assert decide([earlier_merge, later_fixes])[0] == "failure"
    assert decide([later_fixes, earlier_merge])[0] == "failure"


def test_later_merge_overrides_earlier_fixes():
    earlier_fixes = review("merge after fixes", submitted="2026-10-13T10:05:00Z", rid=1)
    later_merge = review("merge", submitted="2026-10-13T10:20:00Z", rid=2)
    assert decide([earlier_fixes, later_merge])[0] == "success"


def test_later_malformed_bot_review_fails_closed_after_an_earlier_merge():
    earlier_merge = review("merge", submitted="2026-10-13T10:05:00Z", rid=1)
    later_bold = review("**merge**", submitted="2026-10-13T10:20:00Z", rid=2)
    assert decide([earlier_merge, later_bold])[0] == "failure"


def test_pending_review_without_a_submit_time_does_not_count():
    assert decide([review("merge", submitted=None)])[0] == "failure"


def test_security_pass_does_not_override_a_merge_verdict():
    reviewer = review("merge", submitted="2026-10-13T10:05:00Z", rid=1)
    security = review(SECURITY_PASS, submitted="2026-10-13T10:10:00Z", rid=2)
    assert decide([reviewer, security])[0] == "success"


def test_security_fail_after_a_merge_verdict_fails_the_gate():
    reviewer = review("merge", submitted="2026-10-13T10:05:00Z", rid=1)
    security = review(SECURITY_FAIL, submitted="2026-10-13T10:10:00Z", rid=2)
    assert decide([reviewer, security])[0] == "failure"


def test_security_fail_before_a_merge_verdict_still_fails_the_gate():
    security = review(SECURITY_FAIL, submitted="2026-10-13T10:05:00Z", rid=1)
    reviewer = review("merge", submitted="2026-10-13T10:10:00Z", rid=2)
    assert decide([security, reviewer])[0] == "failure"


def test_sensitive_paths_never_get_success_from_the_bot():
    reviewer = review("merge", submitted="2026-10-13T10:05:00Z", rid=1)
    assert decide([reviewer], sensitive=True)[0] == "failure"
    assert decide([reviewer], sensitive=False)[0] == "success"


def test_sensitive_paths_stay_failure_even_with_a_security_pass_on_this_head():
    reviewer = review("merge", submitted="2026-10-13T10:05:00Z", rid=1)
    security = review(SECURITY_PASS, submitted="2026-10-13T10:10:00Z", rid=2)
    assert decide([reviewer, security], sensitive=True)[0] == "failure"


def test_security_fail_on_sensitive_paths_is_a_failure():
    reviewer = review("merge", submitted="2026-10-13T10:05:00Z", rid=1)
    security = review(SECURITY_FAIL, submitted="2026-10-13T10:10:00Z", rid=2)
    assert decide([reviewer, security], sensitive=True)[0] == "failure"


def test_security_fail_formats_are_all_a_veto():
    reviewer = review("merge", submitted="2026-10-13T10:05:00Z", rid=1)
    for body in ("`FAIL` (security)", "FAIL. see below", "**FAIL** (security)", "fail"):
        security = review(body, submitted="2026-10-13T10:10:00Z", rid=2)
        assert decide([reviewer, security])[0] == "failure", body


CODEOWNERS = (REPO_ROOT / ".github" / "CODEOWNERS").read_text()
CODEOWNERS_PATHS = [
    line.split("#", 1)[0].split()[0]
    for line in CODEOWNERS.splitlines()
    if line.split("#", 1)[0].strip()
]


def test_every_codeowners_pattern_is_sensitive():
    assert CODEOWNERS_PATHS, "CODEOWNERS has no patterns to check"
    patterns = report_verdict.codeowners_patterns(CODEOWNERS)
    for raw in CODEOWNERS_PATHS:
        path = raw.lstrip("/")
        if path.endswith("/"):
            path = path + "some-file.txt"
        assert report_verdict.is_sensitive_path(path, patterns), raw


def test_named_sensitive_paths_are_sensitive():
    patterns = report_verdict.codeowners_patterns(CODEOWNERS)
    for path in (
        ".github/workflows/review.yml",
        ".claude/settings.json",
        "src/adapters/claude/settings.json",
        "scripts/install.sh",
        "scripts/report_verdict.py",
        "scripts/put_secret.sh",
        ".trazo/project/charter/charter.md",
        "Makefile",
        "Dockerfile",
        ".pre-commit-config.yaml",
        "pyproject.toml",
        "uv.lock",
        "config/secrets.yaml",
    ):
        assert report_verdict.is_sensitive_path(path, patterns), path


def test_ordinary_paths_are_not_sensitive():
    patterns = report_verdict.codeowners_patterns(CODEOWNERS)
    for path in ("src/other/notes.md", "tests/test_x.py", "docs/guide.md"):
        assert not report_verdict.is_sensitive_path(path, patterns), path


def test_classify_flags_a_rename_out_of_a_sensitive_path():
    listing = "src/renamed.py\t.github/workflows/review.yml\n"
    assert report_verdict.classify(listing, "1", CODEOWNERS) is True


def test_classify_flags_a_listing_that_does_not_match_the_file_count():
    listing = "src/a.py\n"
    assert report_verdict.classify(listing, "2", CODEOWNERS) is True


def test_classify_passes_an_ordinary_complete_listing():
    listing = "src/a.py\ttests/old_a.py\n"
    assert report_verdict.classify(listing, "1", CODEOWNERS) is False


def test_classify_cli_prints_the_flag():
    import subprocess
    import sys

    codeowners = REPO_ROOT / ".github" / "CODEOWNERS"
    # Runs this repo's own script with fixed arguments.
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT), "--sensitive", str(codeowners)],
        input=".github/workflows/review.yml\n",
        capture_output=True,
        text=True,
        env={"CHANGED_FILES": "1", "PATH": "/usr/bin:/bin"},
        check=True,
    )
    assert result.stdout.strip() == "sensitive=true"


def test_a_failed_security_review_is_matched_by_its_first_word_not_the_whole_line():
    reviewer = review("merge", submitted="2026-10-13T10:05:00Z", rid=1)
    security = review(
        "FAIL (security re-review at 42cd655d6b4eb51af4a7eac0623988ac9aa032b0)\n\nSee below.",
        submitted="2026-10-13T10:10:00Z",
        rid=2,
    )
    assert decide([reviewer, security])[0] == "failure"


def test_run_reads_paginated_json_and_decides():
    page_one = json.dumps([review("merge", rid=1)])
    page_two = json.dumps([review("merge after fixes", submitted="2026-10-13T10:30:00Z", rid=2)])
    state, _ = report_verdict.run(page_one + "\n" + page_two, HEAD, STARTED, BOT)
    assert state == "failure"


def test_unreadable_input_sets_failure():
    state, reason = report_verdict.run("not json", HEAD, STARTED, BOT)
    assert state == "failure"
    assert reason


def test_missing_run_start_sets_failure():
    state, _ = report_verdict.run("[]", HEAD, "", BOT)
    assert state == "failure"


def test_codeowners_directory_without_trailing_slash_is_sensitive():
    assert report_verdict.is_sensitive_path("infra/main.tf", [("infra", True)])
    assert not report_verdict.is_sensitive_path("infrastructure/main.tf", [("infra", True)])


def test_codeowners_glob_is_matched_loosely():
    assert report_verdict.is_sensitive_path("deploy/app.yml", [("*.yml", False)])
    assert report_verdict.is_sensitive_path("deploy/app.yml", [("deploy/*.yml", True)])
    assert not report_verdict.is_sensitive_path("deploy/app.json", [("*.yml", False)])


def test_glob_naming_a_directory_covers_the_files_inside_it():
    assert report_verdict.is_sensitive_path("build/logs/a.txt", [("**/logs", False)])
    assert report_verdict.is_sensitive_path("src/a/config/x.yml", [("src/*/config", True)])


def test_unanchored_directory_matches_at_any_depth():
    assert report_verdict.is_sensitive_path("pkg/docs/readme.md", [("docs/", False)])
    assert not report_verdict.is_sensitive_path("pkg/mydocs/readme.md", [("docs/", False)])


def test_unsupported_codeowners_syntax_fails_closed():
    patterns = report_verdict.codeowners_patterns("/weird\\ name.txt @owner\n")
    assert report_verdict.is_sensitive_path("src/anything.py", patterns)


def test_extra_stand_ins_are_sensitive_at_any_depth():
    patterns = report_verdict.codeowners_patterns("")
    for path in (
        "GNUmakefile",
        "sub/uv.toml",
        "sub/.python-version",
        "docs/requirements-dev.txt",
        ".gitleaks.toml",
        ".gitleaksignore",
        ".gitignore",
        "mkdocs.yml",
        ".dockerignore",
        ".github/dependabot.yml",
        ".github/actions/setup/action.yml",
        "CLAUDE.md",
        "sub/AGENTS.md",
        ".trazo/rules.md",
        ".trazo/roles/reviewer.md",
        ".trazo/project/adr/0020-verdict-success-from-bot-review.md",
        "src/overlay/roles/reviewer.md",
    ):
        assert report_verdict.is_sensitive_path(path, patterns), path
    assert not report_verdict.is_sensitive_path("src/other/notes.md", [])


def test_unset_sensitive_flag_fails_closed_in_the_script():
    import subprocess
    import sys

    env = {"HEAD_SHA": HEAD, "RUN_STARTED_AT": STARTED, "PATH": "/usr/bin:/bin"}
    reviews = json.dumps([review("merge")])
    result = subprocess.run(  # noqa: S603 -- runs this repo's own script with fixed arguments
        [sys.executable, str(SCRIPT)],
        input=reviews,
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    assert "state=failure" in result.stdout
