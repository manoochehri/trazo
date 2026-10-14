"""Decide trazo/verdict from the automatic review on a pull request head (issue #213, ADR 0020).

The report job runs this script from the base branch.

Decide mode (default): reads the pull request's reviews as JSON on stdin (one or more arrays, as
`gh api --paginate` prints them) and writes `state=` and `reason=` lines for GITHUB_OUTPUT.
Success needs a review from the bot login that is on the head commit, was submitted after the review
job started, names that exact head with one `Reviewed-Head` line, and whose first line is exactly
`merge`. The latest such reviewer verdict decides. A
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

# Paths the project treats as sensitive beyond the base CODEOWNERS list. This list is the authority;
# ADR 0020 and the RUNBOOK point here. Matching is case-insensitive.
#   - the gate, scripts and agent definitions, and the governance the agents read (rules, roles,
#     ADRs, charter, overlay, the CLAUDE.md and AGENTS.md adapters);
#   - the build, dependency, index and secret-scanning config that CI and `make` read;
#   - the docs build, which runs the hooks in mkdocs.yml, and the dependency bot.
EXTRA_SENSITIVE_PREFIXES = (
    "scripts/",
    ".claude/",
    ".github/",
    ".trazo/rules.md",
    ".trazo/roles/",
    ".trazo/project/adr/",
    ".trazo/project/charter/",
    "src/overlay/",
    "src/adapters/",
)
# Matched against the file's base name, so a stand-in at any depth counts.
EXTRA_SENSITIVE_BASENAMES = (
    "makefile",
    "gnumakefile",
    "dockerfile",
    ".dockerignore",
    ".gitignore",
    ".gitleaks.toml",
    ".gitleaksignore",
    ".pre-commit-config.yaml",
    ".python-version",
    "pyproject.toml",
    "uv.lock",
    "uv.toml",
    ".env.example",
    "mkdocs.yml",
    "claude.md",
    "agents.md",
    "codeowners",
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


def reviewed_head(body):
    """Return a single well-formed Reviewed-Head marker, or empty for missing/ambiguous data."""
    if not isinstance(body, str):
        return ""
    markers = [
        line.strip() for line in body.splitlines() if line.strip().startswith("Reviewed-Head:")
    ]
    if len(markers) != 1:
        return ""
    match = re.fullmatch(r"Reviewed-Head:\s*([0-9a-f]{40})", markers[0])
    return match.group(1) if match else ""


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


def decide(reviews, head_sha, review_started_at, bot_login, sensitive=False):
    if sensitive:
        return "failure", "changed paths need a person to set the status, through /check-pr"
    started = parse_time(review_started_at)
    verdicts = []
    for review in reviews:
        if (review.get("user") or {}).get("login") != bot_login:
            continue
        if review.get("commit_id") != head_sha:
            continue
        submitted = review.get("submitted_at")
        if not submitted or parse_time(submitted) <= started:
            continue
        body = review.get("body")
        word = first_word(body)
        if word == SECURITY_BLOCK:
            return "failure", "a security review on this head failed"
        if word == SECURITY_CLEAR:
            continue
        if reviewed_head(body) != head_sha:
            continue
        verdicts.append((parse_time(submitted), review.get("id") or 0, first_line(body)))
    if not verdicts:
        return (
            "failure",
            "no bot review for this head was submitted after the review job started",
        )
    _, _, verdict = max(verdicts)
    if verdict == "merge":
        return "success", "bot review on this head says merge"
    return "failure", "bot review on this head does not say exactly merge"


def run(text, head_sha, review_started_at, bot_login, sensitive=False):
    if not review_started_at:
        return "failure", "no reviewer job start time"
    try:
        reviews = read_reviews(text)
        return decide(reviews, head_sha, review_started_at, bot_login, sensitive)
    except Exception:
        # Fixed text on purpose: the exception message can carry review content.
        return "failure", "could not read the bot reviews"


def codeowners_patterns(text):
    """Return (pattern, anchored) pairs from a CODEOWNERS file.

    A line with syntax this parser does not model (an escape) becomes a catch-all, so an
    unrecognised line marks every path sensitive instead of none.
    """
    patterns = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        if "\\" in line:
            patterns.append(("*", False))
            continue
        token = line.split()[0]
        patterns.append((token.lstrip("/").lower(), token.startswith("/")))
    return patterns


def pattern_matches(path, pattern, anchored):
    # A pattern owns a path when it matches the path itself or any directory above it, so a
    # directory pattern covers its files and a glob that names a directory covers what is in it.
    # An anchored pattern starts at the repository root; an unanchored one may start at any segment.
    # Globs match loosely, which only ever marks more paths sensitive.
    segments = path.split("/")
    name = pattern.rstrip("/")
    is_glob = any(char in pattern for char in "*?[")
    starts = [0] if anchored else range(len(segments))
    for start in starts:
        for end in range(start + 1, len(segments) + 1):
            candidate = "/".join(segments[start:end])
            if is_glob:
                if fnmatch(candidate, name):
                    return True
            elif candidate == name:
                return True
    return False


def is_sensitive_path(path, patterns):
    path = path.lower()
    base = path.rsplit("/", 1)[-1]
    if path.startswith(EXTRA_SENSITIVE_PREFIXES) or base in EXTRA_SENSITIVE_BASENAMES:
        return True
    if base.startswith("requirements") and base.endswith(".txt"):
        return True
    if "secret" in path:
        return True
    return any(pattern_matches(path, pattern, anchored) for pattern, anchored in patterns)


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


def git_diff_paths(diff: bytes) -> list[tuple[str, ...]]:
    """Parse NUL-delimited `git diff --name-status`; reject malformed or partial output."""
    if not diff:
        return []
    if not diff.endswith(b"\0"):
        raise ValueError("truncated git diff output")
    fields = diff[:-1].split(b"\0")
    paths: list[tuple[str, ...]] = []
    index = 0
    while index < len(fields):
        status = fields[index].decode("ascii")
        index += 1
        if status.startswith(("R", "C")) and status[1:].isdigit():
            count = 2
        elif status in {"A", "D", "M", "T", "U", "X", "B"}:
            count = 1
        else:
            raise ValueError("unknown git diff status")
        if index + count > len(fields):
            raise ValueError("truncated git diff path")
        if any(not path for path in fields[index : index + count]):
            raise ValueError("empty git diff path")
        paths.append(
            tuple(
                path.decode("utf-8", errors="surrogateescape")
                for path in fields[index : index + count]
            )
        )
        index += count
    return paths


def classify_git_diff(diff: bytes, codeowners_text: str) -> bool:
    """Classify both sides of renames from an immutable git diff, failing closed on bad data."""
    try:
        paths = git_diff_paths(diff)
    except (UnicodeDecodeError, ValueError):
        return True
    patterns = codeowners_patterns(codeowners_text)
    return any(is_sensitive_path(path, patterns) for record in paths for path in record)


def main(argv):
    if len(argv) == 3 and argv[1] == "--sensitive-git-diff":
        with open(argv[2], encoding="utf-8") as handle:
            codeowners_text = handle.read()
        sensitive = classify_git_diff(sys.stdin.buffer.read(), codeowners_text)
        print(f"sensitive={'true' if sensitive else 'false'}")
        return 0
    if len(argv) == 3 and argv[1] == "--sensitive":
        with open(argv[2], encoding="utf-8") as handle:
            codeowners_text = handle.read()
        sensitive = classify(sys.stdin.read(), os.environ.get("CHANGED_FILES", ""), codeowners_text)
        print(f"sensitive={'true' if sensitive else 'false'}")
        return 0
    state, reason = run(
        sys.stdin.read(),
        os.environ.get("HEAD_SHA", ""),
        os.environ.get("REVIEW_STARTED_AT", ""),
        os.environ.get("BOT_LOGIN", DEFAULT_BOT_LOGIN),
        # Anything but an explicit "false" is sensitive, so an unset or garbled value fails closed.
        sensitive=os.environ.get("SENSITIVE") != "false",
    )
    print(f"state={state}")
    print(f"reason={reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
