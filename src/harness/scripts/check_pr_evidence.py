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


# Dependabot exemption (#426). Narrowest rule: the pull request author must be the Dependabot
# bot (taken from the event's author field, never the body or branch name), every commit in the
# range must be authored by it, and every changed file must be one of the exact root-level files
# the ecosystems in .github/dependabot.yml (uv, github-actions, docker; directory "/") edit, with
# only a version bump in it. Each removed line must pair with an added line that is identical
# once the version is masked; anything added-only, removed-only, re-sourced or new falls back to
# the full evidence check, as does any error reading the diff.
DEPENDABOT_LOGIN = "dependabot[bot]"
DEPENDABOT_EMAIL = "49699333+dependabot[bot]@users.noreply.github.com"
PYPROJECT = "pyproject.toml"
UV_LOCK = "uv.lock"
DOCKERFILE = "Dockerfile"
WORKFLOW_RE = re.compile(r"^\.github/workflows/[^/]+\.yml$")

_VER = r"\d+(?:\.\d+)*(?:(?:a|b|rc|post|dev)\d+)*"
_OPVER_RE = re.compile(rf"(==|>=|<=|~=|>|<)({_VER})(?=\")")
_DEP_ITEM = r'"[A-Za-z0-9][A-Za-z0-9._-]*(?:\[[A-Za-z0-9,._-]+\])?(?:==|>=|<=|~=|>|<)V"'
PYPROJECT_SHAPE = re.compile(
    rf"\s*(?:[A-Za-z0-9_-]+\s*=\s*\[)?\s*{_DEP_ITEM}(?:\s*,\s*{_DEP_ITEM})*\s*,?\s*\]?"
)
LOCK_VERSION_LINE = re.compile(rf'version = "({_VER})"')
LOCK_VERSION_SHAPE = re.compile(r'version = "V"')
LOCK_SPEC_SHAPE = re.compile(
    r'\s*\{ name = "[A-Za-z0-9][A-Za-z0-9._-]*", specifier = "(?:==|>=|<=|~=|>|<)V" \},?'
)
# sdist and wheel entries of a package: a PyPI URL, a sha256 and size. These may change in number.
LOCK_FILE_ENTRY = re.compile(
    r'(?:sdist = )?\s*\{ url = "https://files\.pythonhosted\.org/packages/[0-9a-f/]+/[^"/\s]+", '
    r'hash = "sha256:[0-9a-f]{64}", size = \d+(?:, upload-time = "[0-9TZ:.-]+")? \},?'
)
USES_RE = re.compile(
    r"(?P<pre>\s*(?:-\s+)?uses:\s*)(?P<action>[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9_.-]+"
    r"(?:/[A-Za-z0-9_.-]+)*)@(?P<ref>[0-9a-f]{40}|v\d+\.\d+\.\d+)(?P<cmt>\s+#.*)?"
)
FROM_RE = re.compile(
    r"FROM (?P<img>[a-z0-9][a-z0-9._/-]*)(?::[A-Za-z0-9_][A-Za-z0-9._-]*)?"
    r"(?:@sha256:[0-9a-f]{64})?(?P<alias> AS [A-Za-z0-9_.-]+)?"
)


def _git(*args: str) -> str:
    # Fixed git subcommands; the SHAs are validated as 40 hex digits by the caller.
    return subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def _hunks(base: str, head: str, path: str) -> list[tuple[list[str], list[str]]] | None:
    """Removed and added lines per hunk, or None for anything unexpected."""
    diff = _git("diff", "--no-color", "--no-renames", "-U0", f"{base}...{head}", "--", path)
    hunks: list[tuple[list[str], list[str]]] = []
    for line in diff.split("\n"):
        if line.startswith("@@"):
            hunks.append(([], []))
        elif not hunks:
            continue  # header before the first hunk
        elif line.startswith("-"):
            hunks[-1][0].append(line[1:])
        elif line.startswith("+"):
            hunks[-1][1].append(line[1:])
        elif line not in ("", "\\ No newline at end of file"):
            return None
    return hunks or None


def _pairs(hunks, pair_ok, free_ok=None) -> bool:
    for removed, added in hunks:
        pair_r = [x for x in removed if not (free_ok and free_ok(x))]
        pair_a = [x for x in added if not (free_ok and free_ok(x))]
        if len(pair_r) != len(pair_a) or not (pair_r or removed or added):
            return False
        if not all(pair_ok(r, a) for r, a in zip(pair_r, pair_a, strict=True)):
            return False
    return True


def _masked(line: str) -> str:
    return _OPVER_RE.sub(r"\1V", line)


def _pyproject_pair(old: str, new: str) -> bool:
    a, b = _masked(old), _masked(new)
    return old != new and a == b and PYPROJECT_SHAPE.fullmatch(a) is not None


def _lock_pair(old: str, new: str) -> bool:
    def mask(line: str) -> str:
        return re.sub(rf'^version = "{_VER}"$', 'version = "V"', _masked(line))

    a, b = mask(old), mask(new)
    shape = LOCK_VERSION_SHAPE.fullmatch(a) or LOCK_SPEC_SHAPE.fullmatch(a)
    return old != new and a == b and shape is not None


def _workflow_pair(old: str, new: str) -> bool:
    a, b = USES_RE.fullmatch(old), USES_RE.fullmatch(new)
    if a is None or b is None or old == new:
        return False
    return a["pre"] == b["pre"] and a["action"] == b["action"]


def _dockerfile_pair(old: str, new: str) -> bool:
    a, b = FROM_RE.fullmatch(old), FROM_RE.fullmatch(new)
    if a is None or b is None or old == new:
        return False
    return a["img"] == b["img"] and a["alias"] == b["alias"]


def _lock_is_version_bump(hunks) -> bool:
    """Version pairs, plus file entries whose filename carries one of those versions."""
    is_entry = lambda x: LOCK_FILE_ENTRY.fullmatch(x) is not None  # noqa: E731
    if not _pairs(hunks, _lock_pair, is_entry):
        return False
    old_versions: set[str] = set()
    new_versions: set[str] = set()
    for removed, added in hunks:
        old_versions |= {m[1] for x in removed if (m := LOCK_VERSION_LINE.fullmatch(x))}
        new_versions |= {m[1] for x in added if (m := LOCK_VERSION_LINE.fullmatch(x))}
    if not new_versions:
        return False

    def carries(line: str, versions: set[str]) -> bool:
        name = line.split('url = "', 1)[1].split('"', 1)[0].rsplit("/", 1)[1]
        return any(re.search(rf"-{re.escape(v)}(?=-|\.tar|\.zip|\.whl)", name) for v in versions)

    return all(carries(x, old_versions) for r, _ in hunks for x in r if is_entry(x)) and all(
        carries(x, new_versions) for _, a in hunks for x in a if is_entry(x)
    )


def _file_is_version_bump(base: str, head: str, path: str) -> bool:
    hunks = _hunks(base, head, path)
    if hunks is None:
        return False
    if path == PYPROJECT:
        return _pairs(hunks, _pyproject_pair)
    if path == UV_LOCK:
        return _lock_is_version_bump(hunks)
    if path == DOCKERFILE:
        return _pairs(hunks, _dockerfile_pair)
    return _pairs(hunks, _workflow_pair)


def is_dependency_only_dependabot_pr(pull_request: dict) -> bool:
    """True only for a Dependabot-authored PR that changes nothing but dependency versions."""
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
        # A person with write access can push to a Dependabot branch; their commits must not
        # inherit the exemption. (Author fields are self-declared, so this raises the bar only.)
        authors = _git("log", "--format=%an <%ae>", f"{base}..{head}").split("\n")
        authors = [a for a in authors if a]
        if not authors or any(a != f"{DEPENDABOT_LOGIN} <{DEPENDABOT_EMAIL}>" for a in authors):
            return False
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
            if path not in (PYPROJECT, UV_LOCK, DOCKERFILE) and not WORKFLOW_RE.fullmatch(path):
                return False
            if not _file_is_version_bump(base, head, path):
                return False
    except (subprocess.CalledProcessError, OSError, ValueError):
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
