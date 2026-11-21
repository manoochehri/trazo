"""Liveness sweeper for the unattended driver (issue #262, ADR 0024).

The sweep job in drive.yml reads a snapshot with `gh` and pipes it here as JSON on stdin;
this script prints JSON `{"rerun": [...], "alerts": [...], "digest": "..."}` and nothing else. It
decides; the workflow acts. It never emits a status write: only the reviewer path sets
trazo/verdict.

Targets (a breach is a bug): a ready issue has a PR within one driver run (30 minutes); a PR
head has a trazo/verdict within 15 minutes of its push; a green PR merges within one run.

Guards, tighten only: nothing happens while `halt` is true; drafts and fork PRs are skipped; a
head is re-run at most RERUN_LIMIT times; at most MAX_ALERTS_PER_DAY alert issues are opened per
day and an
alert whose key is already open is not repeated; a PR carrying a blocking label is left to a person.
Unreadable input exits non-zero with no output, so the workflow does nothing.

Snapshot fields: now (ISO time), halt, prs[{number, head_sha, head_pushed_at, draft, fork, verdict
("", pending, success, failure), verdict_at, review_run {id, status, conclusion, run_attempt} or
null, labels}], ready_issues[{number, ready_since}], open_alerts[keys],
alerts_today, max_reruns (from drive_guard cap runs; at most its ceiling).
"""

import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path

# The run ceiling is the guard's, the single source: a variable may lower it, never raise past it.
_spec = importlib.util.spec_from_file_location(
    "drive_guard", Path(__file__).resolve().parent / "drive_guard.py"
)
_guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_guard)
RERUN_DEFAULT = _guard.DEFAULTS["runs"]
RERUN_CEILING = _guard.CEILINGS["runs"]

REVIEW_DEADLINE_MIN = 15
ONE_RUN_MIN = 30
RERUN_LIMIT = (
    2  # re-runs beyond the first attempt: attempt numbers 1 and 2 may be re-run, 3 may not
)
MAX_ALERTS_PER_DAY = 5
BLOCKING_LABELS = {"needs-decision", "needs-pm", "unverified-in-engine"}


def _t(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _minutes(now, then):
    return (_t(now) - _t(then)).total_seconds() / 60


def sweep(snapshot):
    now = snapshot["now"]
    out = {"rerun": [], "alerts": [], "digest": ""}
    if snapshot.get("halt"):
        out["digest"] = "drive-halt is set; the sweeper did nothing."
        return out
    prs = [p for p in snapshot.get("prs", []) if not p.get("draft") and not p.get("fork")]
    lines = []
    raw = snapshot.get("max_reruns", RERUN_DEFAULT)
    max_reruns = min(raw, RERUN_CEILING) if isinstance(raw, int) and raw >= 0 else RERUN_DEFAULT
    candidates = []  # (key, title, body)

    for p in prs:
        n = p["number"]
        verdict = p.get("verdict") or ""
        if verdict in ("success", "failure"):
            if (
                verdict == "success"
                and p.get("verdict_at")
                and _minutes(now, p["verdict_at"]) >= ONE_RUN_MIN
                and not BLOCKING_LABELS & set(p.get("labels", []))
            ):
                candidates.append(
                    (
                        f"merge-stalled-pr-{n}",
                        f"Liveness: green PR #{n} has not merged within one driver run",
                        f"PR #{n} has had a passing trazo/verdict for over {ONE_RUN_MIN} "
                        "minutes and is still open. It may be waiting on CI, a security "
                        "status, or the owner (protected paths).",
                    )
                )
            continue
        if _minutes(now, p["head_pushed_at"]) < REVIEW_DEADLINE_MIN:
            continue
        r = p.get("review_run")
        if r and r.get("status") != "completed":
            continue  # a review is running or queued; let it finish
        if r and r.get("run_attempt", 1) <= RERUN_LIMIT:
            if len(out["rerun"]) >= max_reruns:
                lines.append(f"re-run cap reached; #{n} left for the next sweep")
                continue
            out["rerun"].append({"pr": n, "run_id": r["id"]})
            lines.append(f"re-ran review on #{n}")
            continue
        why = (
            "no review run exists for this head"
            if not r
            else "the review was re-run and still has no verdict"
        )
        candidates.append(
            (
                f"review-stalled-pr-{n}",
                f"Liveness: PR #{n} has no trazo/verdict {REVIEW_DEADLINE_MIN} minutes after push",
                f"PR #{n} head {p['head_sha']}: {why}. "
                "The built-in token may not be able to start review.yml (#252).",
            )
        )

    if not prs:
        for i in snapshot.get("ready_issues", []):
            if _minutes(now, i["ready_since"]) >= ONE_RUN_MIN:
                candidates.append(
                    (
                        f"no-pr-issue-{i['number']}",
                        f"Liveness: ready issue #{i['number']} has no PR after one driver run",
                        f"Issue #{i['number']} is ready, nothing is in flight, "
                        f"and no PR exists after {ONE_RUN_MIN} minutes.",
                    )
                )

    open_alerts = set(snapshot.get("open_alerts", []))
    room = max(0, MAX_ALERTS_PER_DAY - int(snapshot.get("alerts_today", 0)))
    for key, title, body in candidates:
        if key in open_alerts:
            continue
        if room == 0:
            lines.append(f"alert cap reached; {key} not opened")
            continue
        out["alerts"].append({"key": key, "title": title, "body": body})
        lines.append(f"alerted {key}")
        room -= 1
    out["digest"] = "; ".join(lines) if lines else "nothing stalled."
    return out


def main():
    try:
        result = sweep(json.load(sys.stdin))
    except Exception:
        print("could not read the snapshot; doing nothing.", file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
