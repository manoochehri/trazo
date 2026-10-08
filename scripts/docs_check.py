"""Check durable project docs for status, stale links, closed issues, and staleness."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

PROJECT = Path(".trazo/project")
STATUS_LINE = re.compile(
    r"^\*\*Status:\*\* (current|superseded by \[[^\]]+\]\([^)]+\))$",
    re.MULTILINE,
)
ISSUE_REF = re.compile(r"(?<![\w/])#(\d+)\b")
SUPERSEDED_LINK = re.compile(r"^\*\*Status:\*\* superseded by \[[^\]]+\]\(([^)]+)\)$")


class DocsCheckError(Exception):
    """An invariant in `.trazo/project/` is not satisfied."""


def project_docs(project_root: Path) -> list[Path]:
    """Return project Markdown files other than append-only decision records."""
    adr_root = project_root / "adr"
    return sorted(path for path in project_root.rglob("*.md") if adr_root not in path.parents)


def _status_line(path: Path) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    # The lifecycle marker belongs in the document header, before its first section.
    header = "\n".join(lines[:5])
    match = STATUS_LINE.search(header)
    if not match:
        raise DocsCheckError(
            f"{path}: add `**Status:** current` or `**Status:** superseded by [title](path)` "
            "in the header"
        )
    return match.group(0)


def check_status_headers(project_root: Path) -> None:
    for path in project_docs(project_root):
        status = _status_line(path)
        match = SUPERSEDED_LINK.match(status)
        if not match:
            continue
        target = match.group(1)
        if target.startswith(("https://", "http://", "#")):
            raise DocsCheckError(f"{path}: superseded-by link must point to a project file")
        resolved = (path.parent / target).resolve()
        if not resolved.is_file():
            raise DocsCheckError(f"{path}: superseded-by target does not exist: {target}")


def check_issue_refs(status_path: Path, issue_state: Callable[[int], str]) -> None:
    """Reject closed or unresolvable issues named in STATUS; lookup errors fail closed."""
    text = status_path.read_text(encoding="utf-8")
    for number in sorted({int(value) for value in ISSUE_REF.findall(text)}):
        try:
            state = issue_state(number).strip().lower()
        except Exception as exc:
            raise DocsCheckError(f"{status_path}: cannot verify issue #{number}: {exc}") from exc
        if state != "open":
            raise DocsCheckError(
                f"{status_path}: issue #{number} is {state or 'unavailable'}; "
                "remove or update the stale reference"
            )


def _git(root: Path, *args: str) -> str:
    executable = shutil.which("git")
    if executable is None:
        raise DocsCheckError("git is required to check STATUS freshness")
    result = subprocess.run(  # noqa: S603 - resolved executable, fixed read-only arguments
        [executable, *args], cwd=root, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def check_status_freshness(project_root: Path, base_ref: str) -> None:
    """Require STATUS to have changed on or after the supplied latest-main ref."""
    repo_root = project_root.parent.parent
    try:
        base_commit = _git(repo_root, "rev-parse", "--verify", "--end-of-options", base_ref)
        status_commit = _git(
            repo_root, "log", "-1", "--format=%H", "--", (project_root / "STATUS.md").as_posix()
        )
        if not status_commit:
            raise DocsCheckError(f"{project_root / 'STATUS.md'} is not committed")
        _git(repo_root, "merge-base", "--is-ancestor", base_commit, status_commit)
    except subprocess.CalledProcessError as exc:
        raise DocsCheckError(
            f"{project_root / 'STATUS.md'} predates {base_ref}; "
            "update STATUS after the latest merged change"
        ) from exc


def _gh_issue_state(number: int) -> str:
    gh = shutil.which("gh")
    if gh is None:
        raise DocsCheckError("gh is required to validate issue references")
    args = [gh, "issue", "view", str(number), "--json", "state", "--jq", ".state"]
    repository = os.environ.get("GITHUB_REPOSITORY")
    if repository:
        args.extend(("--repo", repository))
    result = subprocess.run(  # noqa: S603 - fixed gh command, numeric issue argument
        args,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def check_project(project_root: Path, base_ref: str, issue_state: Callable[[int], str]) -> None:
    check_status_headers(project_root)
    status_path = project_root / "STATUS.md"
    if not status_path.is_file():
        raise DocsCheckError(f"{status_path} is missing")
    check_issue_refs(status_path, issue_state)
    check_status_freshness(project_root, base_ref)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    project_root = repo_root / PROJECT
    base_ref = os.environ.get("DOCS_BASE_REF", "origin/main")
    if len(sys.argv) == 2:
        base_ref = sys.argv[1]
    elif len(sys.argv) > 2:
        print("usage: python scripts/docs_check.py [base-ref]", file=sys.stderr)
        return 2
    try:
        check_project(project_root, base_ref, _gh_issue_state)
    except DocsCheckError as exc:
        print(f"docs-check: {exc}", file=sys.stderr)
        return 1
    print("docs-check: project docs are current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
