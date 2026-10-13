"""Decide trazo/verdict from the automatic review on a pull request head (issue #213, ADR 0020).

The report job runs this script from the base branch.

Decide mode (default): reads the pull request's reviews as JSON on stdin (one or more arrays, as
`gh api --paginate` prints them) and writes `state=` and `reason=` lines for GITHUB_OUTPUT.
Success needs a review from the bot login that is on the head commit, was submitted after this run
started, and whose first line is exactly `merge`. The latest such reviewer verdict decides. A
security review on the head that starts with FAIL always fails the gate. A pull request that
changes a sensitive path never gets success from the bot: a person sets the status through
/check-pr. Anything else is failure, including unreadable input. The reason text is fixed, never
copied from a review or an exception.

Classify mode (`--sensitive <CODEOWNERS file>`): reads the changed files as tab-separated
`filename<TAB>previous_filename` lines on stdin and prints `sensitive=true|false`. Both names count,
so a file renamed out of a sensitive path is still sensitive. The check uses the CODEOWNERS file
of the base branch, plus the extra paths below. The count of lines must equal CHANGED_FILES, or the
listing is treated as sensitive and the gate fails closed.
"""

import json
import os
import re
import sys
from datetime import datetime
from fnmatch import fnmatch

DEFAULT_BOT_LOGIN = "github-actions[bot]"
SECURITY_CLEAR = "pass"
SECURITY_BLOCK = "fail"

# Paths the project treats as sensitive beyond the CODEOWNERS list: the gate itself, the scripts,
# the agent definitions, and the build and infrastructure files. Matched case-insensitively.
EXTRA_SENSITIVE_PREFIXES = ("scripts/", ".claude/")
EXTRA_SENSITIVE_FILES = (
    "makefile",
    "dockerfile",
    ".pre-commit-config.yaml",
    "pyproject.toml",
    "uv.lock",
    ".env.example",
)


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def first_line(body):
    if not body or not body.strip():
        return ""
    return body.strip().splitlines()[0].strip()


def first_word(body):
    # Security reviews start `PASS (security re-review at <sha>)` or `FAIL (...)`. Leading markup
    # such as `**` or `` ` `` is skipped, and the word ends at the first non-letter.
    match = re.match(r"[\W_]*([A-Za-z]+)", first_line(body))
    return match.group(1).lower() if match else ""


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
    if sensitive:
        return "failure", "changed paths need a person to set the status, through /check-pr"
    started = parse_time(run_started_at)
    verdicts = []
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
        if word == SECURITY_BLOCK:
            return "failure", "a security review on this head failed"
        if word == SECURITY_CLEAR:
            continue
        verdicts.append((parse_time(submitted), review.get("id") or 0, first_line(body)))
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


def codeowners_patterns(text):
    patterns = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        pattern = line.split()[0].lstrip("/").lower()
        patterns.append(pattern)
    return patterns


def pattern_matches(path, pattern):
    # CODEOWNERS: a pattern names a file, or a directory with or without a trailing slash, and
    # may hold globs. Globs are matched loosely, which only ever marks more paths sensitive.
    if any(char in pattern for char in "*?["):
        base = path.rsplit("/", 1)[-1]
        return fnmatch(path, pattern) or fnmatch(path, "*/" + pattern) or fnmatch(base, pattern)
    return path == pattern or path.startswith(pattern.rstrip("/") + "/")


def is_sensitive_path(path, patterns):
    path = path.lower()
    if path.startswith(EXTRA_SENSITIVE_PREFIXES) or path in EXTRA_SENSITIVE_FILES:
        return True
    if "secret" in path:
        return True
    return any(pattern_matches(path, pattern) for pattern in patterns)


def classify(listing, changed_files, codeowners_text):
    """Return True when any listed file, old name or new, is sensitive or the listing is short."""
    lines = [line for line in listing.splitlines() if line.strip()]
    try:
        expected = int(changed_files)
    except (TypeError, ValueError):
        return True
    if len(lines) != expected:
        return True
    patterns = codeowners_patterns(codeowners_text)
    for line in lines:
        for name in line.split("\t"):
            if name and is_sensitive_path(name, patterns):
                return True
    return False


def main(argv):
    if len(argv) == 3 and argv[1] == "--sensitive":
        with open(argv[2], encoding="utf-8") as handle:
            codeowners_text = handle.read()
        sensitive = classify(sys.stdin.read(), os.environ.get("CHANGED_FILES", ""), codeowners_text)
        print(f"sensitive={'true' if sensitive else 'false'}")
        return 0
    state, reason = run(
        sys.stdin.read(),
        os.environ.get("HEAD_SHA", ""),
        os.environ.get("RUN_STARTED_AT", ""),
        os.environ.get("BOT_LOGIN", DEFAULT_BOT_LOGIN),
        # Anything but an explicit "false" is sensitive, so an unset or garbled value fails closed.
        sensitive=os.environ.get("SENSITIVE") != "false",
    )
    print(f"state={state}")
    print(f"reason={reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
