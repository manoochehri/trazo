"""Behaviour of the report job's verdict decision (issue #213, ADR 0020).

The report job turns a bot review into trazo/verdict. These tests pin the decision on
fixtures, so the rule is checked without running GitHub Actions.
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


def review(body, login=BOT, commit=HEAD, submitted="2026-10-13T10:05:00Z", rid=1):
    return {
        "id": rid,
        "body": body,
        "commit_id": commit,
        "submitted_at": submitted,
        "user": {"login": login},
    }


def decide(reviews):
    return report_verdict.decide(reviews, HEAD, STARTED, BOT)


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


def test_security_review_with_pass_does_not_override_a_merge_verdict():
    reviewer = review("merge", submitted="2026-10-13T10:05:00Z", rid=1)
    security = review("pass\n\nNo findings.", submitted="2026-10-13T10:10:00Z", rid=2)
    assert decide([reviewer, security])[0] == "success"


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
