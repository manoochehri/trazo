"""Behaviour of the liveness sweeper (issue #262, ADR 0024).

The sweeper decides, from a snapshot read with `gh`, which stalled reviews to re-run and which
stalls to alert on. It never sets a status: only the reviewer path sets trazo/verdict.

Fixture fields follow GitHub's REST objects: workflow run (id, status, conclusion, run_attempt,
head_sha, event) https://docs.github.com/en/rest/actions/workflow-runs and combined commit status.
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "drive_sweep.py"

spec = importlib.util.spec_from_file_location("drive_sweep", SCRIPT)
drive_sweep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(drive_sweep)

NOW = "2026-11-01T12:00:00Z"
OLD = "2026-11-01T11:30:00Z"  # 30 min before NOW
FRESH = "2026-11-01T11:55:00Z"  # 5 min before NOW


def pr(number=7, pushed=OLD, verdict="", verdict_at="", run=None, labels=(), sha="a" * 40):
    return {
        "number": number,
        "head_sha": sha,
        "head_pushed_at": pushed,
        "draft": False,
        "fork": False,
        "verdict": verdict,
        "verdict_at": verdict_at,
        "review_run": run,
        "labels": list(labels),
    }


def run(status="completed", conclusion="success", attempt=1, run_id=99):
    return {"id": run_id, "status": status, "conclusion": conclusion, "run_attempt": attempt}


def snap(prs=(), issues=(), halt=False, alerts=(), alerts_today=0):
    return {
        "now": NOW,
        "halt": halt,
        "prs": list(prs),
        "ready_issues": list(issues),
        "open_alerts": list(alerts),
        "alerts_today": alerts_today,
    }


def test_stalled_review_is_rerun():
    out = drive_sweep.sweep(snap([pr(run=run())]))
    assert out["rerun"] == [{"pr": 7, "run_id": 99}]
    assert out["alerts"] == []


def test_fresh_head_is_left_alone():
    assert drive_sweep.sweep(snap([pr(pushed=FRESH, run=run())]))["rerun"] == []


def test_head_with_verdict_is_not_rerun():
    for state in ("success", "failure"):
        assert (
            drive_sweep.sweep(snap([pr(verdict=state, verdict_at=FRESH, run=run())]))["rerun"] == []
        )


def test_running_review_is_not_rerun():
    out = drive_sweep.sweep(snap([pr(run=run(status="in_progress", conclusion=None))]))
    assert out["rerun"] == [] and out["alerts"] == []


def test_rerun_is_capped_per_head():
    out = drive_sweep.sweep(snap([pr(run=run(attempt=3))]))
    assert out["rerun"] == []
    assert [a["key"] for a in out["alerts"]] == ["review-stalled-pr-7"]


def test_no_review_run_alerts_instead_of_dispatching():
    out = drive_sweep.sweep(snap([pr(run=None)]))
    assert out["rerun"] == []
    assert [a["key"] for a in out["alerts"]] == ["review-stalled-pr-7"]


def test_drafts_and_forks_are_skipped():
    d = pr(run=run())
    d["draft"] = True
    f = pr(number=8, run=run())
    f["fork"] = True
    out = drive_sweep.sweep(snap([d, f]))
    assert out["rerun"] == [] and out["alerts"] == []


def test_halt_does_nothing():
    out = drive_sweep.sweep(snap([pr(run=run())], [{"number": 5, "ready_since": OLD}], halt=True))
    assert out["rerun"] == [] and out["alerts"] == []


def test_green_pr_unmerged_after_one_run_alerts():
    out = drive_sweep.sweep(snap([pr(verdict="success", verdict_at=OLD)]))
    assert [a["key"] for a in out["alerts"]] == ["merge-stalled-pr-7"]


def test_green_pr_with_blocking_label_does_not_alert():
    out = drive_sweep.sweep(snap([pr(verdict="success", verdict_at=OLD, labels=["needs-pm"])]))
    assert out["alerts"] == []


def test_ready_issue_without_pr_alerts_when_nothing_in_flight():
    out = drive_sweep.sweep(snap(issues=[{"number": 5, "ready_since": OLD}]))
    assert [a["key"] for a in out["alerts"]] == ["no-pr-issue-5"]


def test_ready_issue_waits_while_a_pr_is_in_flight():
    out = drive_sweep.sweep(
        snap([pr(pushed=FRESH, run=run())], [{"number": 5, "ready_since": OLD}])
    )
    assert out["alerts"] == []


def test_recent_ready_issue_is_not_flagged():
    assert drive_sweep.sweep(snap(issues=[{"number": 5, "ready_since": FRESH}]))["alerts"] == []


def test_existing_alert_is_not_duplicated():
    out = drive_sweep.sweep(
        snap(issues=[{"number": 5, "ready_since": OLD}], alerts=["no-pr-issue-5"])
    )
    assert out["alerts"] == []


def test_daily_alert_cap():
    issues = [{"number": n, "ready_since": OLD} for n in range(1, 20)]
    out = drive_sweep.sweep(snap(issues=issues, alerts_today=drive_sweep.MAX_ALERTS_PER_DAY - 1))
    assert len(out["alerts"]) == 1


def test_digest_lists_what_moved():
    out = drive_sweep.sweep(snap([pr(run=run())]))
    assert "re-ran review on #7" in out["digest"]


def test_sweeper_never_emits_a_status_write():
    out = drive_sweep.sweep(snap([pr(run=run())]))
    assert set(out) == {"rerun", "alerts", "digest"}


def test_cli_reads_json_and_prints_json():
    p = subprocess.run(  # noqa: S603 - fixed argv, our own script
        [sys.executable, str(SCRIPT)],
        input=json.dumps(snap([pr(run=run())])),
        capture_output=True,
        text=True,
    )
    assert p.returncode == 0
    assert json.loads(p.stdout)["rerun"] == [{"pr": 7, "run_id": 99}]


def test_cli_bad_input_fails_closed():
    p = subprocess.run(  # noqa: S603 - fixed argv, our own script
        [sys.executable, str(SCRIPT)], input="not json", capture_output=True, text=True
    )
    assert p.returncode != 0
    assert p.stdout == ""


def test_workflow_sweep_job_is_guarded_and_cannot_set_statuses():
    text = (REPO_ROOT / ".github" / "workflows" / "drive.yml").read_text()
    job = text[text.index("\n  sweep:") :]
    assert "vars.DRIVE_ENABLED == 'true'" in job
    assert "scripts/drive_sweep.py" in job
    assert "statuses: write" not in job
    assert "/statuses/" not in job


def test_reruns_per_sweep_are_capped_by_max_reruns():
    s = snap([pr(number=n, run=run(run_id=n)) for n in range(1, 7)])
    s["max_reruns"] = 2
    out = drive_sweep.sweep(s)
    assert len(out["rerun"]) == 2


def test_max_reruns_cannot_exceed_the_guard_ceiling():
    s = snap([pr(number=n, run=run(run_id=n)) for n in range(1, 30)])
    s["max_reruns"] = 1000
    assert len(drive_sweep.sweep(s)["rerun"]) == drive_sweep.RERUN_CEILING


def test_bad_max_reruns_falls_back_to_default():
    s = snap([pr(number=n, run=run(run_id=n)) for n in range(1, 30)])
    s["max_reruns"] = "lots"
    assert len(drive_sweep.sweep(s)["rerun"]) == drive_sweep.RERUN_DEFAULT


def test_workflow_sweep_uses_the_guard_halt_check_not_a_variable():
    text = (REPO_ROOT / ".github" / "workflows" / "drive.yml").read_text()
    assert "DRIVE_HALT" not in text
    job = text[text.index("\n  sweep:") :]
    assert "scripts/drive_guard.py halt" in job
    assert "scripts/drive_guard.py cap runs" in job
