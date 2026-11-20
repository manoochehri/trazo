"""Spend cap and runaway guardrails for the drive workflow (issues #249, #258, ADR 0024).

The workflow is read as text (no YAML dependency); the decision logic lives in
scripts/drive_guard.py and is tested on fixtures. UNVERIFIED: live Actions behavior, and whether
claude-code-action passes --max-budget-usd through (print mode only, per
https://code.claude.com/docs/en/cli-reference); #247 checks it live.
"""

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "drive.yml"
SCRIPT = REPO_ROOT / "scripts" / "drive_guard.py"


def text():
    return WORKFLOW.read_text()


def job(name):
    lines = text().splitlines()
    start = lines.index(f"  {name}:")
    end = next(
        (i for i in range(start + 1, len(lines)) if re.match(r"^  \S", lines[i])), len(lines)
    )
    return "\n".join(lines[start:end])


def guard():
    spec = importlib.util.spec_from_file_location("drive_guard", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def ev(t, kind):
    return {"time": t, "kind": kind}


# --- decision logic -------------------------------------------------------------------------


def test_limit_uses_a_whole_number_and_falls_back_to_the_default():
    g = guard()
    assert g.limit("3", 5) == 3
    assert g.limit("0", 5) == 0
    for bad in ("", None, "-1", "2.5", "five", "3; rm -rf", "1e3"):
        assert g.limit(bad, 5) == 5


def test_breaker_trips_on_two_consecutive_failures_ordered_by_time():
    g = guard()
    assert (
        g.breaker([ev("2026-01-01T00:00:00Z", "fail"), ev("2026-01-01T01:00:00Z", "fail")]) is True
    )
    assert (
        g.breaker([ev("2026-01-01T02:00:00Z", "fail"), ev("2026-01-01T01:00:00Z", "fail")]) is True
    )


def test_breaker_resets_on_a_success_and_needs_two():
    g = guard()
    assert g.breaker([]) is False
    assert g.breaker([ev("2026-01-01T00:00:00Z", "fail")]) is False
    assert (
        g.breaker([ev("2026-01-01T00:00:00Z", "fail"), ev("2026-01-01T01:00:00Z", "ok")]) is False
    )
    assert (
        g.breaker([ev("2026-01-01T00:00:00Z", "ok"), ev("2026-01-01T01:00:00Z", "fail")]) is False
    )
    assert (
        g.breaker(
            [
                ev("2026-01-01T00:00:00Z", "fail"),
                ev("2026-01-01T01:00:00Z", "ok"),
                ev("2026-01-01T02:00:00Z", "fail"),
            ]
        )
        is False
    )


def test_breaker_ignores_unknown_kinds_and_fails_closed_on_junk():
    g = guard()
    junk = [
        ev("2026-01-01T00:00:00Z", "fail"),
        {"kind": "weird"},
        ev("2026-01-01T01:00:00Z", "fail"),
    ]
    assert g.breaker(junk) is True
    assert g.breaker("not a list") is True


def test_digest_lists_merges_and_halt_state_without_mentions():
    g = guard()
    out = g.digest([{"number": 7, "title": "Fix @bob #9", "url": "https://x/7"}], halted=False)
    assert "#7" in out and "1 merged" in out and "@bob" not in out
    none = g.digest([], halted=True)
    assert "0 merged" in none and "drive-halt" in none


def test_cli_limit_and_breaker():
    r = subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT), "limit", "abc", "5"], capture_output=True, text=True
    )
    assert r.stdout.strip() == "5"
    events = '[{"time":"1","kind":"fail"},{"time":"2","kind":"fail"}]'
    r = subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT), "breaker"], input=events, capture_output=True, text=True
    )
    assert r.stdout.strip() == "trip=true"


# --- workflow wiring ------------------------------------------------------------------------


def test_agent_has_turn_and_dollar_bounds_and_a_shorter_timeout():
    work = job("work")
    assert "--max-turns 60" in work
    assert "--max-budget-usd" in work
    m = re.search(r"timeout-minutes: (\d+)", work)
    assert m and int(m.group(1)) <= 30  # was 45: tighten only


def test_work_job_guard_runs_before_the_picker_and_before_the_agent():
    work = job("work")
    g = work.index("id: guard")
    pick = work.index("id: pick")
    assert g < pick < work.index("claude-code-action")
    guard_step = work[g:pick]
    for needle in (
        "drive-halt",
        "DRIVE_MAX_MERGES_PER_DAY",
        "DRIVE_MAX_RUNS_PER_DAY",
        "DRIVE_MAX_USD_PER_RUN",
        "scripts/drive_guard.py",
        "issue-[0-9]+-drive-",
        "set -euo pipefail",
        "ok=false",
    ):
        assert needle in guard_step, needle
    assert "steps.guard.outputs.ok == 'true'" in work[pick - 200 : pick + 200]


def test_merge_job_stops_on_halt_and_caps_merges():
    merge = job("merge")
    for needle in ("drive-halt", "DRIVE_MAX_MERGES_PER_DAY", "scripts/drive_guard.py"):
        assert needle in merge, needle
    assert merge.index("drive-halt") < merge.index("while IFS")


def test_breaker_job_opens_a_drive_halt_issue_without_an_llm():
    b = job("breaker")
    assert "claude-code-action" not in b
    assert "drive-halt" in b and "gh issue create" in b
    assert "scripts/drive_guard.py breaker" in b
    assert "vars.DRIVE_ENABLED == 'true'" in b
    assert "issues: write" in b


def test_digest_job_runs_daily_and_comments():
    assert text().count("- cron:") == 2
    d = job("digest")
    assert "claude-code-action" not in d
    assert "scripts/drive_guard.py digest" in d
    assert "gh issue comment" in d


def test_every_new_job_is_gated_by_the_kill_switch_and_default_branch():
    for name in ("breaker", "digest"):
        j = job(name)
        assert "vars.DRIVE_ENABLED == 'true'" in j
        assert "github.event.repository.default_branch" in j


def test_no_action_is_unpinned_and_no_new_secret():
    t = text()
    for use in re.findall(r"^\s*(?:- )?uses: (\S+)", t, re.M):
        assert re.search(r"@[0-9a-f]{40}$", use), use
    assert t.count("${{ secrets.") == 1  # still only ANTHROPIC_API_KEY
