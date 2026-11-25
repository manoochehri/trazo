"""Automatic clear of a drive halt (#332, ADR 0030, amends ADR 0027).

The decision lives in scripts/drive_guard.py and is tested on fixtures; the workflow only gathers
facts with gh. UNVERIFIED: live GitHub behavior (the closed-event actor of an App token).
"""

import importlib.util
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "drive.yml"
SCRIPT = REPO_ROOT / "scripts" / "drive_guard.py"

NOW = "2026-01-10T12:00:00Z"
HALT = {"number": 9, "created_at": "2026-01-10T00:00:00Z"}
MERGED = [{"number": 41, "merged_at": "2026-01-10T06:00:00Z"}]
GREEN = {"sha": "abc", "status": "completed", "conclusion": "success", "url": "https://x/r/1"}
APP = "builder[bot]"
MARK = "Auto-cleared"


def guard():
    spec = importlib.util.spec_from_file_location("drive_guard", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def job(name):
    lines = WORKFLOW.read_text().splitlines()
    start = lines.index(f"  {name}:")
    end = next(
        (i for i in range(start + 1, len(lines)) if re.match(r"^  \S", lines[i])), len(lines)
    )
    return "\n".join(lines[start:end])


def clear(halt=HALT, merged=MERGED, ci=GREEN, prior=(), head="abc", now=NOW):
    return guard().auto_clear(halt, merged, ci, list(prior), head, now)


def test_clears_when_a_fix_merged_after_the_halt_and_ci_is_green():
    ok, pr, _ = clear()
    assert ok is True and pr == 41


def test_refuses_without_a_merge_after_the_halt():
    assert clear(merged=[])[0] is False
    assert clear(merged=[{"number": 1, "merged_at": "2026-01-09T23:59:59Z"}])[0] is False
    assert clear(merged=[{"number": 1, "merged_at": "2026-01-10T00:00:00Z"}])[0] is False


def test_refuses_when_ci_is_red_pending_or_for_another_head():
    for bad in (
        {**GREEN, "conclusion": "failure"},
        {**GREEN, "conclusion": None, "status": "in_progress"},
        {**GREEN, "status": "queued", "conclusion": None},
        {**GREEN, "conclusion": "cancelled"},
        {**GREEN, "sha": "old"},
        None,
        {},
    ):
        assert clear(ci=bad)[0] is False, bad


def test_refuses_within_24_hours_of_a_previous_clear():
    assert clear(prior=[{"closed_at": "2026-01-09T12:00:01Z"}])[0] is False
    assert clear(prior=[{"closed_at": "2026-01-09T12:00:00Z"}])[0] is True  # exactly 24h ago


def test_fails_closed_on_malformed_input():
    assert clear(halt=None)[0] is False
    assert clear(halt={"number": 9})[0] is False
    assert clear(halt={"number": 9, "created_at": "yesterday"})[0] is False
    assert clear(merged="junk")[0] is False
    assert clear(merged=[{"number": 1, "merged_at": "nope"}])[0] is False
    assert clear(merged=[{"merged_at": "2026-01-10T06:00:00Z"}])[0] is False
    assert clear(prior="junk")[0] is False
    assert clear(prior=[{"closed_at": "nope"}])[0] is False
    assert clear(head="")[0] is False
    assert clear(now="never")[0] is False


def auto_issue(by=APP, labels=("auto-cleared",), comments=None):
    if comments is None:
        comments = [{"author": APP, "body": MARK + ": merged #41, CI green"}]
    return {
        "state": "closed",
        "closed_by": by,
        "closed_at": "2026-01-10T12:00:00Z",
        "labels": list(labels),
        "comments": comments,
    }


def test_guard_accepts_exactly_the_auto_clear():
    got = guard().halt_status([auto_issue()], "owner", APP)
    assert got == (False, "2026-01-10T12:00:00Z")


def test_guard_still_halts_for_anything_short_of_the_auto_clear():
    g = guard()
    for bad in (
        auto_issue(by="someone-else"),  # label and comment, but not the App closing
        auto_issue(labels=()),  # App closed, no label
        auto_issue(comments=[]),  # App closed, label, no comment
        auto_issue(comments=[{"author": "someone-else", "body": MARK}]),
        auto_issue(comments=[{"author": APP, "body": "unrelated"}]),
        auto_issue(by=None),
    ):
        assert g.halt_status([bad], "owner", APP)[0] is True, bad
    # no App identity configured: the auto-clear is never recognised
    assert g.halt_status([auto_issue()], "owner", "")[0] is True
    assert g.halt_status([auto_issue()], "owner")[0] is True
    # the owner closing it still works
    assert g.halt_status([auto_issue(by="owner", labels=(), comments=[])], "owner", APP)[0] is False


def test_autoclear_job_closes_only_after_the_guard_says_so():
    a = job("autoclear")
    assert "scripts/drive_guard.py autoclear" in a
    assert "auto-cleared" in a and "gh issue close" in a
    assert "environment: trazo-apps" in a and "DRIVE_BUILDER_APP_LOGIN" in a
    assert a.index("scripts/drive_guard.py autoclear") < a.index("gh issue close")
