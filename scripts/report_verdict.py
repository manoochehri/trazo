"""Decide trazo/verdict from the automatic review on a pull request head (issue #213, ADR 0020).

The report job runs this script from the base branch. It reads the pull request's reviews as
JSON on stdin (one or more arrays, as `gh api --paginate` prints them) and writes `state=` and
`reason=` lines for the workflow's GITHUB_OUTPUT.

Success needs a review from the bot login that is on the head commit, was submitted after this
run started, and whose first line is exactly `merge`. The latest such review decides. Anything
else is failure, including unreadable input. Security reviews use `pass` and `fail`, so they
are not counted and cannot overturn a reviewer's verdict. The reason text is fixed, never copied
from a review, so a review cannot inject text into the workflow.
"""

import json
import os
import sys
from datetime import datetime

DEFAULT_BOT_LOGIN = "github-actions[bot]"
SECURITY_WORDS = ("pass", "fail")


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def first_line(body):
    if not body or not body.strip():
        return ""
    return body.strip().splitlines()[0].strip()


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


def decide(reviews, head_sha, run_started_at, bot_login):
    started = parse_time(run_started_at)
    candidates = []
    for review in reviews:
        if (review.get("user") or {}).get("login") != bot_login:
            continue
        if review.get("commit_id") != head_sha:
            continue
        submitted = review.get("submitted_at")
        if not submitted or parse_time(submitted) < started:
            continue
        verdict = first_line(review.get("body"))
        if verdict.lower() in SECURITY_WORDS:
            continue
        candidates.append((parse_time(submitted), review.get("id") or 0, verdict))
    if not candidates:
        return "failure", "no bot review on this head was submitted after the review run started"
    _, _, verdict = max(candidates)
    if verdict == "merge":
        return "success", "bot review on this head says merge"
    return "failure", "bot review on this head does not say exactly merge"


def run(text, head_sha, run_started_at, bot_login):
    if not run_started_at:
        return "failure", "no review run start time"
    try:
        reviews = read_reviews(text)
        return decide(reviews, head_sha, run_started_at, bot_login)
    except (ValueError, TypeError, AttributeError, KeyError) as exc:
        return "failure", f"could not read reviews: {exc}"


def main():
    state, reason = run(
        sys.stdin.read(),
        os.environ.get("HEAD_SHA", ""),
        os.environ.get("RUN_STARTED_AT", ""),
        os.environ.get("BOT_LOGIN", DEFAULT_BOT_LOGIN),
    )
    print(f"state={state}")
    print(f"reason={reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
