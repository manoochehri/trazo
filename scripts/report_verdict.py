"""Decide trazo/verdict from the automatic review on a pull request head (issue #213, ADR 0020).

The report job runs this script from the base branch. It reads the pull request's reviews as
JSON on stdin (one or more arrays, as `gh api --paginate` prints them) and writes `state=` and
`reason=` lines for the workflow's GITHUB_OUTPUT.

Success needs a review from the bot login that is on the head commit, was submitted after this
run started, and whose first line is exactly `merge`. The latest such reviewer verdict decides.
A security review on the head whose first word is `FAIL` always fails the gate, whatever the
order. A security `PASS` is ignored. Anything else is failure, including unreadable input. The
reason text is fixed, never copied from a review or an exception, so nothing from a review can
reach the workflow's output or the status description.
"""

import json
import os
import sys
from datetime import datetime

DEFAULT_BOT_LOGIN = "github-actions[bot]"
SECURITY_CLEAR = "pass"
SECURITY_BLOCK = "fail"


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def first_line(body):
    if not body or not body.strip():
        return ""
    return body.strip().splitlines()[0].strip()


def first_word(body):
    # Security reviews start `PASS (security re-review at <sha>)` or `FAIL (...)`.
    words = first_line(body).split()
    return words[0].strip("*:").lower() if words else ""


def read_reviews(text):
    decoder = json.JSONDecoder()
    reviews = []
    index = 0
    text = text.strip()
    while index < len(text):
        page, index = decoder.raw_decode(text, index)
        if not isinstance(page, list):
            raise ValueError("expected a JSON array of reviews")
        reviews.extend(page)
        while index < len(text) and text[index].isspace():
            index += 1
    return reviews


def decide(reviews, head_sha, run_started_at, bot_login, sensitive=False):
    started = parse_time(run_started_at)
    verdicts = []
    security_fail = False
    security_pass = False
    for review in reviews:
        if (review.get("user") or {}).get("login") != bot_login:
            continue
        if review.get("commit_id") != head_sha:
            continue
        submitted = review.get("submitted_at")
        if not submitted or parse_time(submitted) < started:
            continue
        body = review.get("body")
        word = first_word(body)
        if word == SECURITY_CLEAR:
            security_pass = True
            continue
        if word == SECURITY_BLOCK:
            security_fail = True
            continue
        verdicts.append((parse_time(submitted), review.get("id") or 0, first_line(body)))
    if security_fail:
        return "failure", "a security review on this head failed"
    if sensitive and not security_pass:
        # A change to workflows, CODEOWNERS or dependencies needs a security pass on this head.
        return "failure", "changed paths need a security review on this head, and there is none"
    if not verdicts:
        return "failure", "no bot review on this head was submitted after the review run started"
    _, _, verdict = max(verdicts)
    if verdict == "merge":
        return "success", "bot review on this head says merge"
    return "failure", "bot review on this head does not say exactly merge"


def run(text, head_sha, run_started_at, bot_login, sensitive=False):
    if not run_started_at:
        return "failure", "no review run start time"
    try:
        reviews = read_reviews(text)
        return decide(reviews, head_sha, run_started_at, bot_login, sensitive)
    except Exception:
        # Fixed text on purpose: the exception message can carry review content.
        return "failure", "could not read the bot reviews"


def main():
    state, reason = run(
        sys.stdin.read(),
        os.environ.get("HEAD_SHA", ""),
        os.environ.get("RUN_STARTED_AT", ""),
        os.environ.get("BOT_LOGIN", DEFAULT_BOT_LOGIN),
        sensitive=os.environ.get("SENSITIVE") == "true",
    )
    print(f"state={state}")
    print(f"reason={reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
