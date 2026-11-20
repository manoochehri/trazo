"""Decision helpers for the drive workflow's guardrails (issues #249, #258, ADR 0024).

The workflow gathers facts with `gh`; the decisions live here so they can be tested on fixtures.

  limit RAW DEFAULT   prints RAW if it is a whole number, else DEFAULT (a bad repo variable never
                      loosens a limit into something unbounded)
  breaker             reads a JSON list of {"time", "kind"} events on stdin ("ok" or "fail"), and
                      prints trip=true when the latest two are both failures; unreadable input trips
  digest [--halted]   reads a JSON list of merged pull requests ({number, title, url}) on stdin and
                      prints the daily digest comment
"""

import json
import re
import sys


def limit(raw, default):
    if isinstance(raw, str) and re.fullmatch(r"[0-9]+", raw):
        return int(raw)
    return default


def breaker(events):
    if not isinstance(events, list):
        return True
    try:
        known = sorted(
            (e for e in events if isinstance(e, dict) and e.get("kind") in ("ok", "fail")),
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
        lines.append("The driver is halted: an open issue carries the drive-halt label.")
    else:
        lines.append("")
        lines.append("The driver is not halted.")
    lines += ["", "🛠️ Posted by eng via Claude Code (drive workflow)"]
    return "\n".join(lines)


def main(argv):
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "limit" and len(argv) == 4:
        print(limit(argv[2], int(argv[3])))
        return 0
    if cmd == "breaker":
        try:
            events = json.load(sys.stdin)
        except Exception:
            events = None
        print("trip=" + ("true" if breaker(events) else "false"))
        return 0
    if cmd == "digest":
        print(digest(json.load(sys.stdin), "--halted" in argv))
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
