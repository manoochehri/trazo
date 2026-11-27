"""Scheduled audit of merges that did not meet the owner-merge.yml gate (#380, ADR 0031).

Run by .github/workflows/merge-audit.yml. For each pull request merged into the default branch in
the
last WINDOW_DAYS, it re-applies the gate owner-merge.yml applied, at the head that was merged:

  - every check run green (latest run per name, success or skipped)
  - a risky diff (the shared classifier in scripts/report_verdict.py, plus src/ and .trazo/ outside
    project/) has trazo/verdict AND trazo/security success
  - any diff: a trazo/verdict or trazo/security of failure, error or pending stands as an objection

and opens ONE issue listing the pull requests that fail, skipping any already named in a previous
"Merge audit:" issue. It changes nothing else: it never reverts (that is epic #327's job) and never
merges.
The audit cannot tell WHO set a status (#366); it detects merges that bypassed the gate, such as a
direct
admin merge or a merge made while a check was red.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timedelta

WINDOW_DAYS = 3
FOOTER = "🛡️ Posted by security via GitHub Actions (merge-audit.yml)"
BAD = {"failure", "error", "pending"}


def problems(sensitive: bool, verdict: str, security: str, runs: list[str]) -> list[str]:
    out = []
    if not runs or any(r not in ("success", "skipped") for r in runs):
        out.append("checks were not all green on the merged head")
    if sensitive:
        if verdict != "success":
            out.append(f"risky paths changed and trazo/verdict was {verdict or 'missing'}")
        if security != "success":
            out.append(f"risky paths changed and trazo/security was {security or 'missing'}")
    else:
        if verdict in BAD:
            out.append(f"trazo/verdict was {verdict} on the merged head")
        if security in BAD:
            out.append(f"trazo/security was {security} on the merged head")
    return out


AUDIT_AUTHOR = "github-actions[bot]"


def reported_numbers(issues: list[dict]) -> set[int]:
    """PR numbers named by earlier audit reports.

    Only issues the workflow itself opened count, so an outside account cannot file a
    "Merge audit:" issue that mentions a PR and suppress its report."""
    seen: set[int] = set()
    for issue in issues:
        if "pull_request" in issue or not issue["title"].startswith("Merge audit:"):
            continue
        if (issue.get("user") or {}).get("login") != AUDIT_AUTHOR:
            continue
        seen.update(int(n) for n in re.findall(r"#(\d+) ", issue.get("body") or ""))
    return seen


def audit(prs, facts, already_reported):
    """Return [(number, [reason, ...])] for merged PRs that fail the gate and are not yet
    reported."""
    found = []
    for pr in prs:
        if pr["number"] in already_reported:
            continue
        reasons = problems(**facts(pr))
        if reasons:
            found.append((pr["number"], reasons))
    return found


def issue_text(found, today: str):
    title = f"Merge audit: {len(found)} merged PR(s) did not meet the merge gate ({today})"
    lines = [
        "The scheduled audit re-applied the owner-merge.yml gate to pull requests merged recently "
        "and found these did not meet it. Review each; revert through a pull request "
        "if it was wrong.",
        "",
    ]
    for number, reasons in found:
        lines.append(f"- #{number} " + "; ".join(reasons))
    lines += ["", FOOTER]
    return title, "\n".join(lines)


# ---- GitHub access (everything above is pure and tested without it) ------------------------------


def _gh(*args: str) -> str:
    gh = shutil.which("gh")
    if gh is None:
        sys.exit("gh is required")
    r = subprocess.run([gh, *args], capture_output=True, text=True, check=False)  # noqa: S603
    if r.returncode != 0:
        sys.exit(f"gh {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout


def _pages(path: str):
    data = json.loads(_gh("api", "--paginate", "--slurp", path))
    return [item for page in data for item in (page if isinstance(page, list) else [page])]


def _classify(repo: str, pr: dict) -> bool:
    n = pr["number"]
    files = _pages(f"repos/{repo}/pulls/{n}/files")
    tsv = "".join(f"{f['filename']}\t{f.get('previous_filename') or ''}\n" for f in files)
    here = os.path.dirname(os.path.abspath(__file__))
    env = {**os.environ, "CHANGED_FILES": str(len(files))}
    # A short or oversized listing fails closed inside the classifier (count must equal
    # CHANGED_FILES).
    r = subprocess.run(  # noqa: S603
        [
            sys.executable,
            os.path.join(here, "report_verdict.py"),
            "--sensitive",
            ".github/CODEOWNERS",
        ],
        input=tsv,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    risky = r.stdout.strip() != "sensitive=false"
    names = [x for f in files for x in (f["filename"], f.get("previous_filename") or "") if x]
    for name in names:
        if re.match(r"(?i)^(src/|\.trazo/)", name) and not re.match(r"(?i)^\.trazo/project/", name):
            risky = True
    return risky


def _facts(repo: str):
    def facts(pr: dict) -> dict:
        sha = pr["head"]["sha"]
        status = json.loads(_gh("api", f"repos/{repo}/commits/{sha}/status?per_page=100"))
        by = {s["context"]: s["state"] for s in status.get("statuses", [])}
        runs = _pages(f"repos/{repo}/commits/{sha}/check-runs")
        latest: dict[str, tuple[int, str]] = {}
        for page in runs:
            for run in page.get("check_runs", []):
                if run["name"] not in latest or run["id"] > latest[run["name"]][0]:
                    latest[run["name"]] = (run["id"], run.get("conclusion") or "pending")
        return {
            "sensitive": _classify(repo, pr),
            "verdict": by.get("trazo/verdict", ""),
            "security": by.get("trazo/security", "none"),
            "runs": [c for _, c in latest.values()],
        }

    return facts


def main() -> int:
    repo = os.environ["GITHUB_REPOSITORY"]
    base = os.environ.get("DEFAULT_BRANCH", "main")
    since = datetime.now(UTC) - timedelta(days=WINDOW_DAYS)
    closed = json.loads(
        _gh(
            "api",
            f"repos/{repo}/pulls?state=closed&base={base}&sort=updated&direction=desc&per_page=100",
        )
    )
    merged = [
        p
        for p in closed
        if p.get("merged_at")
        and datetime.fromisoformat(p["merged_at"].replace("Z", "+00:00")) >= since
    ]
    seen = reported_numbers(json.loads(_gh("api", f"repos/{repo}/issues?state=all&per_page=100")))
    found = audit(merged, _facts(repo), seen)
    print(
        f"audited {len(merged)} merged PR(s) since {since:%Y-%m-%d}; {len(found)} failed the gate"
    )
    if not found:
        return 0
    title, body = issue_text(found, datetime.now(UTC).strftime("%Y-%m-%d"))
    print(_gh("issue", "create", "--title", title, "--body", body, "-R", repo).strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
