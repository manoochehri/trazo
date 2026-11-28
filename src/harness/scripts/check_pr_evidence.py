"""Require review and fail-first evidence in pull request descriptions."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

EXPECTED_LAYOUT = """\
Expected layout, each line alone on its own line (no bullet, checkbox or bold):
  Review rounds: 1
  Defects found and fixed: none
  ## Fail-first output
  ```
  FAILED tests/test_x.py::test_y - AssertionError: expected 2
  ```
or, instead of the Fail-first section:
  Fail-first exemption: docs-only change, no behavior to test
See .github/pull_request_template.md."""


def validate(body: str) -> list[str]:
    errors: list[str] = []
    rounds = re.search(r"(?im)^Review rounds:\s*(\d+)\s*$", body)
    if rounds is None:
        bad = re.search(r"(?im)^Review rounds:.*$", body)
        if bad is None:
            errors.append("Add 'Review rounds: <number>' on its own line.")
        else:
            errors.append(
                f"Could not read '{bad.group(0).strip()}'. Expected 'Review rounds: <number>' "
                "on its own line, digits only (for example 'Review rounds: 1'); "
                "put any explanation on another line."
            )

    defects = re.search(r"(?im)^Defects found and fixed:\s*(.+?)\s*$", body)
    if defects is None or re.search(r"<[^>]+>", defects.group(1)):
        errors.append("Add 'Defects found and fixed: <summary or none>'.")

    exemption = re.search(r"(?im)^Fail-first exemption:\s*(.+?)\s*$", body)
    if (
        exemption
        and len(exemption.group(1).strip()) >= 20
        and not re.search(r"<[^>]+>", exemption.group(1))
    ):
        return errors

    output = re.search(r"(?im)^(?:#{2,3}\s*)?Fail-first output:?[ \t]*\n(.*)", body, re.DOTALL)
    if output is None or re.search(r"<[^>]+>", output.group(1)):
        errors.append("Add failing test output or a specific Fail-first exemption.")
    elif not re.search(r"(?im)^.*\b(FAILED|ERROR)\b|AssertionError|Traceback", output.group(1)):
        errors.append(
            "Fail-first output must show failing test output "
            "(for example, FAILED or AssertionError)."
        )
    return errors


# Dependabot exemption (#426). Narrowest rule: the author must be the Dependabot bot, taken
# from the pull request event's author field (never the body or branch name), and every changed
# file must be one of the exact root-level files the ecosystems in .github/dependabot.yml
# (uv, github-actions, docker; directory "/") can edit, changed in place. Anything else, or any
# error reading the diff, keeps the full evidence check.
DEPENDABOT_LOGIN = "dependabot[bot]"
MANIFEST_FILES = frozenset({"pyproject.toml", "uv.lock"})
DOCKERFILE = "Dockerfile"
WORKFLOW_RE = re.compile(r"^\.github/workflows/[^/]+\.ya?ml$")
USES_LINE_RE = re.compile(r"^\s*(?:-\s+)?uses:\s*\S+@\S+(?:\s+#.*)?$")
FROM_LINE_RE = re.compile(r"^FROM\s+\S+.*$", re.IGNORECASE)


def _git(*args: str) -> str:
    # Fixed git subcommands; the SHAs are validated as 40 hex digits by the caller.
    return subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def _changed_lines_all_match(base: str, head: str, path: str, pattern: re.Pattern[str]) -> bool:
    diff = _git("diff", "--no-color", "--no-renames", "-U0", f"{base}...{head}", "--", path)
    changed: list[str] = []
    in_hunk = False
    for line in diff.splitlines():
        if line.startswith("@@"):
            in_hunk = True
        elif in_hunk and line[:1] in "+-":
            changed.append(line[1:])
        elif in_hunk and line[:1] != "\\":
            return False  # unexpected content inside a hunk: fail closed
    return bool(changed) and all(pattern.match(line) for line in changed)


def is_dependency_only_dependabot_pr(pull_request: dict) -> bool:
    """True only for a Dependabot-authored PR that changes nothing but dependency pins."""
    user = pull_request.get("user")
    if not isinstance(user, dict):
        return False
    if user.get("login") != DEPENDABOT_LOGIN or user.get("type") != "Bot":
        return False
    base = (pull_request.get("base") or {}).get("sha")
    head = (pull_request.get("head") or {}).get("sha")
    sha = re.compile(r"[0-9a-f]{40}")
    if not (isinstance(base, str) and isinstance(head, str)):
        return False
    if not (sha.fullmatch(base) and sha.fullmatch(head)):
        return False
    try:
        raw = _git("diff", "--raw", "-z", "--no-renames", f"{base}...{head}")
        fields = raw.split("\0")
        if fields and fields[-1] == "":
            fields.pop()
        if not fields or len(fields) % 2:
            return False
        for meta, path in zip(fields[0::2], fields[1::2], strict=True):
            # ":<old mode> <new mode> <old sha> <new sha> <status>": in-place edit, regular file.
            parts = meta.split()
            if len(parts) != 5 or (parts[0], parts[1], parts[4]) != (":100644", "100644", "M"):
                return False
            if path in MANIFEST_FILES:
                continue
            if path == DOCKERFILE:
                pattern = FROM_LINE_RE
            elif WORKFLOW_RE.fullmatch(path):
                pattern = USES_LINE_RE
            else:
                return False
            if not _changed_lines_all_match(base, head, path, pattern):
                return False
    except (subprocess.CalledProcessError, OSError):
        return False
    return True


def main() -> int:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        print("GITHUB_EVENT_PATH is not set.", file=sys.stderr)
        return 2
    try:
        event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Could not read GitHub event payload: {exc}", file=sys.stderr)
        return 2
    pull_request = event.get("pull_request")
    if not isinstance(pull_request, dict):
        print("GitHub event does not contain a pull request.", file=sys.stderr)
        return 2
    if is_dependency_only_dependabot_pr(pull_request):
        print("Dependabot dependency-only pull request: evidence check not required.")
        return 0
    errors = validate(pull_request.get("body") or "")
    if errors:
        print("Pull request evidence is incomplete:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        print(EXPECTED_LAYOUT, file=sys.stderr)
        return 1
    print("Pull request evidence fields are present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
