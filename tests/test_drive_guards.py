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
        [sys.executable, str(SCRIPT), "cap", "merges", "abc"], capture_output=True, text=True
    )
    assert r.stdout.strip() == "5"
    r = subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT), "cap", "merges", "99999"], capture_output=True, text=True
    )
    assert r.stdout.strip() == "10"
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
    # ANTHROPIC_API_KEY, plus the builder App id and key read only by the token-minting step (#252)
    assert sorted(re.findall(r"\$\{\{ secrets\.(\w+) \}\}", t)) == [
        "ANTHROPIC_API_KEY",
        "BUILDER_APP_ID",
        "BUILDER_APP_PRIVATE_KEY",
    ]


# --- security round 1 (PR #284) -------------------------------------------------------------


def test_caps_have_hard_ceilings_a_variable_cannot_exceed():
    g = guard()
    assert g.cap("merges", "999999") == 10
    assert g.cap("runs", "999999") == 8
    assert g.cap("usd", "999999") == 5
    assert g.cap("merges", "7") == 7
    for name, default in (("merges", 5), ("runs", 4), ("usd", 2)):
        assert g.cap(name, None) == default
        assert g.cap(name, "junk") == default
        assert default <= g.CEILINGS[name]
    assert g.cap("usd", "0") >= 1  # a zero dollar budget is not a cap, it is a broken run


def issue(state, closed_by=None, closed_at=None):
    return {"state": state, "closed_by": closed_by, "closed_at": closed_at}


def test_halt_holds_until_the_owner_closes_the_halt_issue():
    g = guard()
    assert g.halt_status([], "owner") == (False, "")
    assert g.halt_status([issue("open")], "owner")[0] is True
    assert g.halt_status([issue("closed", "owner", "2026-01-02T00:00:00Z")], "owner") == (
        False,
        "2026-01-02T00:00:00Z",
    )
    # closed by anyone else, or by nobody we can identify, is still a halt
    assert g.halt_status([issue("closed", "someone-else", "2026-01-02T00:00:00Z")], "owner")[0]
    assert g.halt_status([issue("closed", None, "2026-01-02T00:00:00Z")], "owner")[0]
    assert g.halt_status("junk", "owner")[0] is True
    assert g.halt_status([issue("closed", "owner", "x")], "")[0] is True


def test_breaker_ignores_failures_from_before_the_owner_cleared_the_halt():
    g = guard()
    old = [ev("2026-01-01T00:00:00Z", "fail"), ev("2026-01-01T01:00:00Z", "fail")]
    assert g.breaker(old) is True
    assert g.breaker(old, since="2026-01-02T00:00:00Z") is False
    assert (
        g.breaker(old + [ev("2026-01-03T00:00:00Z", "fail")], since="2026-01-02T00:00:00Z") is False
    )


def test_run_cap_and_breaker_count_cancelled_and_timed_out_runs():
    work = job("work")
    guard_step = work[work.index("id: guard") : work.index("id: pick")]
    assert "cancelled" in guard_step and "timed_out" in guard_step
    b = job("breaker")
    assert "cancelled" in b and "timed_out" in b
    assert "needs.work.result != 'cancelled'" not in b
    assert '"cancelled"' in b and "needs.work.result" in b  # this run's own timeout counts


def test_stuck_runs_for_a_cancelled_work_job():
    stuck = job("stuck")
    assert "needs.work.result != 'cancelled'" not in stuck
    assert "needs.work.result == 'cancelled'" in stuck


def test_halt_is_read_through_the_owner_check_in_every_job_that_acts():
    for name in ("work", "merge", "breaker"):
        assert "scripts/drive_guard.py halt" in job(name), name
    assert "/events" in SCRIPT.read_text()  # the closer is read from the issue events API


def test_digest_reports_halt_through_the_owner_closed_check():
    d = job("digest")
    assert "scripts/drive_guard.py halt" in d
    assert "--label drive-halt" not in d


# --- first live run: placeholder files and decision issues (issue #315, PR #312) ------------

# PR #312 added exactly these nine files, all 0 bytes, to a change called "no code change".
PLACEHOLDERS = [
    ".gitmodules",
    ".npmrc",
    ".yarnrc",
    ".yarnrc.yml",
    "bunfig.toml",
    "package-lock.json",
    "package.json",
    "pnpm-lock.yaml",
    "yarn.lock",
]


def test_placeholder_files_are_empty_manifests_only():
    g = guard()
    sizes = {name: 0 for name in PLACEHOLDERS}
    sizes["sub/package.json"] = 0  # nested ones count too
    sizes["tests/__init__.py"] = 0  # an empty Python package marker is legitimate
    sizes["notes.md"] = 0
    sizes["bunfig.toml"] = 12  # not empty: a real edit, left for the reviewer
    got = set(g.placeholder_files(list(sizes), lambda p: sizes[p]))
    expected = (set(PLACEHOLDERS) | {"sub/package.json"}) - {"bunfig.toml"}
    assert got == expected


def test_cli_placeholders_lists_only_untracked_empty_manifests(tmp_path):
    def git(*args):
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)  # noqa: S603, S607

    git("init", "-q")
    for name in PLACEHOLDERS[:3] + ["tests/__init__.py", "sub/yarn.lock"]:
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text("")
    (tmp_path / "bunfig.toml").write_text("real = 1\n")
    git("add", ".gitmodules")  # tracked already: not the agent's addition, never listed
    r = subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT), "placeholders", str(tmp_path)], capture_output=True
    )
    assert r.returncode == 0
    assert set(r.stdout.decode().split("\0")) - {""} == {".npmrc", ".yarnrc", "sub/yarn.lock"}


def test_collect_step_drops_placeholders_before_staging_the_patch():
    collect = job("work").split("name: collect the change as a patch", 1)[1]
    call = '"$RUNNER_TEMP/drive_guard.py" placeholders clean'
    assert call in collect
    assert collect.index(call) < collect.index("safe_git add -A")


def test_collect_runs_a_trusted_copy_of_the_script_not_the_agents_workspace_copy():
    work = job("work")
    # After the agent has edited the workspace, scripts/drive_guard.py is the agent's file.
    after_agent = work.split("name: work the issue", 1)[1]
    assert "scripts/drive_guard.py" not in after_agent.split("--allowedTools", 1)[1]
    copy = 'cp scripts/drive_guard.py "$RUNNER_TEMP/drive_guard.py"'
    assert copy in work
    assert work.index(copy) < work.index("name: work the issue")
    # The agent may not write where the trusted copy lives.
    for tool in ("Edit", "Write"):
        assert f"{tool}(//home/runner/work/_temp/**)" in work


def test_picker_skips_issues_titled_decide():
    pick = job("work").split("candidates=$(", 1)[1].split('issue=""', 1)[0]
    assert "title" in pick.split("-q", 1)[0]  # the title is fetched
    assert re.search(r"Decide", pick)  # and a "Decide:" title is filtered out
