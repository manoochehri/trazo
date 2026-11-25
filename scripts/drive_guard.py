"""Decision helpers for the drive workflow's guardrails (issues #249, #258, ADR 0024).

The workflow gathers facts with `gh`; the decisions live here so they can be tested on fixtures.

  cap NAME RAW        prints RAW (NAME: merges, runs or usd) under a hard ceiling; bad input gives
                      the default
  halt                prints halted=true|false and since=<time>; halted until the repository owner
                      closes every halt issue (open, or closed by anyone else); any error is halted
  autoclear           reads {halt, merged, ci, prior, head, now} as JSON on stdin; prints clear=,
                      pr= and reason=: a halt may clear itself once (#332, ADR 0030); bad input
                      prints clear=false
  limit RAW DEFAULT  prints RAW if it is a whole number, else DEFAULT (a bad repo variable never
                      loosens a limit into something unbounded)
  breaker [--since T] reads a JSON list of {"time", "kind"} events on stdin ("ok" or "fail"), and
                      prints trip=true when the latest two are both failures; unreadable input trips
  digest [--halted]   reads a JSON list of merged pull requests ({number, title, url}) on stdin and
                      prints the daily digest comment
  placeholders DIR    prints, NUL-separated, the new (untracked) files in the git checkout DIR that
                      are empty and named like a package-manager or submodule config file (#315)
"""

import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime, timedelta

# Hard ceilings: a repository variable can lower a limit or raise it up to here, never past it.
DEFAULTS = {"merges": 5, "runs": 4, "usd": 2}
CEILINGS = {"merges": 10, "runs": 8, "usd": 5}


def limit(raw, default):
    if isinstance(raw, str) and re.fullmatch(r"[0-9]+", raw):
        return int(raw)
    return default


def cap(name, raw):
    value = min(limit(raw, DEFAULTS[name]), CEILINGS[name])
    return max(value, 1) if name == "usd" else value


AUTO_LABEL = "auto-cleared"
AUTO_MARK = "Auto-cleared"


def _is_auto_clear(issue, app):
    """True only for the automatic clear: closed by the builder App, labeled, with its comment."""
    if not app or issue.get("closed_by") != app:
        return False
    if AUTO_LABEL not in (issue.get("labels") or []):
        return False
    return any(
        isinstance(c, dict)
        and c.get("author") == app
        and str(c.get("body", "")).startswith(AUTO_MARK)
        for c in issue.get("comments") or []
    )


def halt_status(issues, owner, app=""):
    """Return (halted, since). Halted until the repository owner closes every halt issue.

    since is the latest owner close time: failures at or before it no longer count. A halt closed
    by the builder App `app` counts as cleared only with the auto-cleared label and the App's own
    Auto-cleared comment (#332); a close by anyone else stays a halt.
    """
    if not isinstance(issues, list) or not owner:
        return True, ""
    since = ""
    for i in issues:
        if not isinstance(i, dict) or i.get("state") != "closed" or not i.get("closed_at"):
            return True, ""
        if i.get("closed_by") != owner and not _is_auto_clear(i, app):
            return True, ""
        since = max(since, str(i["closed_at"]))
    return False, since


def _time(raw):
    return datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def auto_clear(halt, merged, ci, prior, head, now):
    """Decide whether the open halt issue may clear itself: (clear, pr_number, reason).

    All must hold: a pull request merged after the halt issue was opened; the latest CI run is
    completed with success and is for `head`, the default branch head; no halt was auto-cleared in
    the last 24 hours. Anything malformed refuses.
    """
    try:
        opened = _time(halt["created_at"])
        current = _time(now)
        fixes = [(_time(m["merged_at"]), int(m["number"])) for m in merged if m.get("merged_at")]
        recent = [_time(p["closed_at"]) for p in prior]
        if not head or not isinstance(ci, dict) or ci.get("sha") != head:
            return False, None, "no CI run for the default branch head"
        if ci.get("status") != "completed" or ci.get("conclusion") != "success":
            return False, None, "CI on the default branch head is not green"
        if any(current - t < timedelta(hours=24) for t in recent):
            return False, None, "a halt was auto-cleared in the last 24 hours"
        after = sorted(f for f in fixes if f[0] > opened)
        if not after:
            return False, None, "no pull request merged after the halt was opened"
        return True, after[-1][1], "fix merged and CI green"
    except Exception:
        return False, None, "unreadable input"


def breaker(events, since=""):
    if not isinstance(events, list):
        return True
    try:
        known = sorted(
            (
                e
                for e in events
                if isinstance(e, dict)
                and e.get("kind") in ("ok", "fail")
                and str(e.get("time", "")) > since
            ),
            key=lambda e: str(e.get("time", "")),
        )
    except Exception:
        return True
    return len(known) >= 2 and known[-1]["kind"] == "fail" and known[-2]["kind"] == "fail"


# The first live run (PR #312, issue #315) added these nine files, all 0 bytes, to a change that
# the agent called "no code change". UNVERIFIED: that the agent runtime creates them; the cause
# is not known.
PLACEHOLDER_NAMES = frozenset(
    {
        ".gitmodules",
        ".npmrc",
        ".yarnrc",
        ".yarnrc.yml",
        "bunfig.toml",
        "package-lock.json",
        "package.json",
        "pnpm-lock.yaml",
        "yarn.lock",
    }
)


def placeholder_files(paths, size_of):
    """Return the paths that are empty files named like a package-manager or submodule config file.

    Only emptiness plus the name qualifies: a real edit to one of these is not empty and is left for
    the reviewer, and an empty file with any other name (an `__init__.py`) is a legitimate change.
    """
    return [p for p in paths if p.rsplit("/", 1)[-1] in PLACEHOLDER_NAMES and size_of(p) == 0]


def untracked_placeholders(root):
    out = subprocess.run(  # noqa: S603
        [  # noqa: S607
            "git",
            "-c",
            "core.fsmonitor=false",
            "-C",
            root,
            "ls-files",
            "--others",
            "--exclude-standard",
            "-z",
        ],
        capture_output=True,
        check=True,
    ).stdout
    paths = [p for p in os.fsdecode(out).split("\0") if p]

    def size_of(p):
        full = os.path.join(root, p)
        return os.path.getsize(full) if os.path.isfile(full) and not os.path.islink(full) else -1

    return placeholder_files(paths, size_of)


def _plain(s):
    # Titles come from agent text: no mentions, no cross-issue links, one line.
    s = str(s).replace("@", "").replace("#", "")
    return " ".join(s.split())[:100]


def digest(merged, halted):
    lines = [f"Drive digest: {len(merged)} merged in the last 24 hours."]
    for pr in merged:
        lines.append(f"- #{int(pr['number'])} {_plain(pr.get('title', ''))}")
    if halted:
        lines.append("")
        lines.append("The driver is halted until the repository owner closes the drive-halt issue.")
    else:
        lines.append("")
        lines.append("The driver is not halted.")
    lines += ["", "🛠️ Posted by eng via Claude Code (drive workflow)"]
    return "\n".join(lines)


def _gh(*args):
    out = subprocess.run(  # noqa: S603
        ["gh", *args],  # noqa: S607
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout


def gather_halt():
    """Halt issues: any open issue labeled drive-halt, and every issue the workflow opened as one.

    The closer is the actor of the issue's last "closed" event. UNVERIFIED against live GitHub:
    https://docs.github.com/en/rest/issues/events
    """
    repo = os.environ["GITHUB_REPOSITORY"]
    owner = _gh("api", f"repos/{repo}", "-q", ".owner.login").strip()
    app = os.environ.get("DRIVE_BUILDER_APP_LOGIN", "")
    labeled = json.loads(
        _gh("issue", "list", "--state", "open", "--label", "drive-halt", "--json", "number")
    )
    issues = [{"state": "open"} for _ in labeled]
    listed = json.loads(
        _gh(
            "issue", "list", "--state", "all", "--author", "app/github-actions",
            "--search", "Drive halted in:title", "--limit", "100",
            "--json", "number,title,state,closedAt,labels",
        )
    )  # fmt: skip
    for i in listed:
        if not str(i.get("title", "")).startswith("Drive halted:"):
            continue
        if i["state"] != "CLOSED":
            issues.append({"state": "open"})
            continue
        pages = json.loads(
            _gh("api", "--paginate", "--slurp", f"repos/{repo}/issues/{i['number']}/events")
        )
        closed = [e for page in pages for e in page if e.get("event") == "closed"]
        who = closed[-1].get("actor", {}).get("login") if closed else None
        row = {"state": "closed", "closed_by": who, "closed_at": i.get("closedAt")}
        if app and who == app:
            row["labels"] = [x.get("name") for x in i.get("labels", [])]
            comments = json.loads(_gh("api", f"repos/{repo}/issues/{i['number']}/comments"))
            row["comments"] = [
                {"author": c.get("user", {}).get("login"), "body": c.get("body", "")}
                for c in comments
            ]
        issues.append(row)
    return halt_status(issues, owner, app)


def main(argv):
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "limit" and len(argv) == 4:
        print(limit(argv[2], int(argv[3])))
        return 0
    if cmd == "cap" and len(argv) == 4:
        print(cap(argv[2], argv[3]))
        return 0
    if cmd == "halt":
        try:
            halted, since = gather_halt()
        except Exception:
            halted, since = True, ""  # fail closed
        print("halted=" + ("true" if halted else "false"))
        print("since=" + since)
        return 0
    if cmd == "autoclear":
        try:
            d = json.load(sys.stdin)
            ok, pr, why = auto_clear(
                d["halt"], d["merged"], d["ci"], d["prior"], d["head"], d["now"]
            )
        except Exception:
            ok, pr, why = False, None, "unreadable input"
        print("clear=" + ("true" if ok else "false"))
        print(f"pr={pr or ''}")
        print("reason=" + why)
        return 0
    if cmd == "breaker":
        try:
            events = json.load(sys.stdin)
        except Exception:
            events = None
        since = argv[3] if len(argv) == 4 and argv[2] == "--since" else ""
        print("trip=" + ("true" if breaker(events, since) else "false"))
        return 0
    if cmd == "digest":
        print(digest(json.load(sys.stdin), "--halted" in argv))
        return 0
    if cmd == "placeholders" and len(argv) == 3:
        sys.stdout.write("".join(p + "\0" for p in untracked_placeholders(argv[2])))
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
