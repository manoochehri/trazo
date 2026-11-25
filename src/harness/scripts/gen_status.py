"""Print the generated STATUS block from live `gh` data (issue #328, step 1).

No LLM and no writes: it reads GitHub with `gh`, prints Markdown to stdout, and exits. Nothing
here edits a file, opens a pull request or sets a status.

  gen_status.py   prints the block (GITHUB_REPOSITORY, or the gh default repo; DRIVE_ENABLED is
                  the repository variable of the same name)

`same_ignoring_stamp(a, b)` compares two blocks without the `generated at` line, so a later step
can open a pull request only when something other than the clock changed.
"""

import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime

MAX_LISTED = 10
STAMP_RE = re.compile(r"^_?generated at .*$", re.M)


def _gh(*args):
    out = subprocess.run(  # noqa: S603
        ["gh", *args],  # noqa: S607
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout


def _version_key(tag):
    return tuple(int(n) for n in re.findall(r"\d+", tag))


def check_state(rollup):
    """FAILURE, PENDING, SUCCESS or NONE from a statusCheckRollup list (gh pr list --json)."""
    if not rollup:
        return "NONE"
    failed = {"FAILURE", "ERROR", "TIMED_OUT", "CANCELLED", "ACTION_REQUIRED", "STARTUP_FAILURE"}
    pending = False
    for c in rollup:
        result = str(c.get("conclusion") or c.get("state") or "").upper()
        if result in failed:
            return "FAILURE"
        if str(c.get("status", "COMPLETED")).upper() != "COMPLETED" or result in (
            "",
            "PENDING",
            "EXPECTED",
        ):
            pending = True
    return "PENDING" if pending else "SUCCESS"


def collect(repo, drive_enabled):
    """Read-only gh calls; returns the dict build_block takes."""
    tags = json.loads(_gh("api", f"repos/{repo}/tags?per_page=100") or "[]")
    names = [t["name"] for t in tags if re.fullmatch(r"v\d+\.\d+\.\d+", t.get("name", ""))]
    miles = json.loads(_gh("api", f"repos/{repo}/milestones?state=open&per_page=100") or "[]")
    miles.sort(key=lambda m: _version_key(m["title"]))
    milestone = None
    if miles:
        m = miles[0]
        milestone = {
            "title": m["title"],
            "open": m["open_issues"],
            "closed": m["closed_issues"],
            "url": m["html_url"],
        }
    prs = json.loads(
        _gh("pr", "list", "--state", "open", "--limit", "100",
            "--json", "number,title,url,statusCheckRollup") or "[]"
    )  # fmt: skip
    halt = json.loads(
        _gh("issue", "list", "--state", "open", "--label", "drive-halt", "--json", "number") or "[]"
    )
    waiting = {}
    for label in ("needs-decision", "needs-pm"):
        found = json.loads(
            _gh("issue", "list", "--state", "open", "--label", label, "--limit", "100",
                "--json", "number,title,url") or "[]"
        )  # fmt: skip
        for i in found:
            waiting[i["number"]] = i
    return {
        "tag": max(names, key=_version_key) if names else "",
        "milestone": milestone,
        "prs": [
            {
                "number": p["number"],
                "title": p["title"],
                "url": p["url"],
                "checks": check_state(p.get("statusCheckRollup")),
            }
            for p in prs
        ],
        "halt_issues": [h["number"] for h in halt],
        "drive_enabled": drive_enabled,
        "waiting": [waiting[n] for n in sorted(waiting)],
    }


def build_block(d, now, sha):
    """The generated block as Markdown. Pure: same data in, same text out."""
    lines = ["## Generated state", ""]
    lines.append(f"- Latest release: {d['tag'] or 'none'}")
    m = d["milestone"]
    if m:
        lines.append(
            f"- Open milestone: [{m['title']}]({m['url']}) - {m['open']} open, {m['closed']} closed"
        )
    else:
        lines.append("- Open milestone: no open milestone")
    if d["halt_issues"]:
        links = ", ".join(f"#{n}" for n in d["halt_issues"])
        lines.append(f"- Drive: halted (drive-halt issue open: {links})")
    elif str(d["drive_enabled"]) != "true":
        lines.append("- Drive: halted (DRIVE_ENABLED is not true)")
    else:
        lines.append("- Drive: running")
    prs = d["prs"]
    lines.append(f"- Open pull requests: {len(prs)} open")
    for p in prs[:MAX_LISTED]:
        lines.append(f"  - [#{p['number']}]({p['url']}) checks {p['checks']}")
    if len(prs) > MAX_LISTED:
        lines.append(f"  - and {len(prs) - MAX_LISTED} more")
    waiting = d["waiting"]
    if waiting:
        lines.append(f"- Waiting on the owner or PM: {len(waiting)}")
        for i in waiting[:MAX_LISTED]:
            lines.append(f"  - [#{i['number']}]({i['url']})")
        if len(waiting) > MAX_LISTED:
            lines.append(f"  - and {len(waiting) - MAX_LISTED} more")
    else:
        lines.append("- Waiting on the owner or PM: none")
    lines += ["", f"_generated at {now} from main@{sha[:7]}_", ""]
    return "\n".join(lines)


def same_ignoring_stamp(a, b):
    """True when two blocks differ only in the `generated at` line."""
    return STAMP_RE.sub("", a).strip() == STAMP_RE.sub("", b).strip()


def main():
    repo = (
        os.environ.get("GITHUB_REPOSITORY")
        or _gh("repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner").strip()
    )
    sha = _gh("api", f"repos/{repo}/commits/main", "-q", ".sha").strip()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    data = collect(repo, os.environ.get("DRIVE_ENABLED", ""))
    sys.stdout.write(build_block(data, now, sha))


if __name__ == "__main__":
    main()
