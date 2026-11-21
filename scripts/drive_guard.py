"""Decision helpers for the drive workflow's guardrails (issues #249, #258, ADR 0024).

The workflow gathers facts with `gh`; the decisions live here so they can be tested on fixtures.

  cap NAME RAW        prints RAW (NAME: merges, runs or usd) under a hard ceiling; bad input gives
                      the default
  halt                prints halted=true|false and since=<time>; halted until the repository owner
                      closes every halt issue (open, or closed by anyone else); any error is halted
  limit RAW DEFAULT   prints RAW if it is a whole number, else DEFAULT (a bad repo variable never
                      loosens a limit into something unbounded)
  breaker [--since T] reads a JSON list of {"time", "kind"} events on stdin ("ok" or "fail"), and
                      prints trip=true when the latest two are both failures; unreadable input trips
  digest [--halted]   reads a JSON list of merged pull requests ({number, title, url}) on stdin and
                      prints the daily digest comment
"""

import json
import os
import re
import subprocess
import sys

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


def halt_status(issues, owner):
    """Return (halted, since). Halted until the repository owner closes every halt issue.

    since is the latest owner close time: failures at or before it no longer count.
    """
    if not isinstance(issues, list) or not owner:
        return True, ""
    since = ""
    for i in issues:
        if not isinstance(i, dict) or i.get("state") != "closed":
            return True, ""
        if i.get("closed_by") != owner or not i.get("closed_at"):
            return True, ""
        since = max(since, str(i["closed_at"]))
    return False, since


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
    labeled = json.loads(
        _gh("issue", "list", "--state", "open", "--label", "drive-halt", "--json", "number")
    )
    issues = [{"state": "open"} for _ in labeled]
    listed = json.loads(
        _gh(
            "issue", "list", "--state", "all", "--author", "app/github-actions",
            "--search", "Drive halted in:title", "--limit", "100",
            "--json", "number,title,state,closedAt",
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
        issues.append({"state": "closed", "closed_by": who, "closed_at": i.get("closedAt")})
    return halt_status(issues, owner)


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
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
