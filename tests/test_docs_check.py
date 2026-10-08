"""Mechanical checks for project-doc lifecycle and drift (#154)."""

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "docs_check.py"
SPEC = importlib.util.spec_from_file_location("docs_check", SCRIPT)
assert SPEC and SPEC.loader
DOCS_CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DOCS_CHECK)
DocsCheckError = DOCS_CHECK.DocsCheckError
_git = DOCS_CHECK._git
check_issue_refs = DOCS_CHECK.check_issue_refs
check_status_freshness = DOCS_CHECK.check_status_freshness
check_status_headers = DOCS_CHECK.check_status_headers


def test_missing_status_header_is_rejected(tmp_path: Path) -> None:
    doc = tmp_path / "STATUS.md"
    doc.write_text("# Status\n\nBody\n", encoding="utf-8")
    with pytest.raises(DocsCheckError, match=r"add `\*\*Status:\*\* current`"):
        check_status_headers(tmp_path)


def test_superseded_link_must_resolve_to_a_file(tmp_path: Path) -> None:
    doc = tmp_path / "old.md"
    doc.write_text("# Old\n**Status:** superseded by [new](new.md)\n", encoding="utf-8")
    with pytest.raises(DocsCheckError, match="superseded-by target does not exist"):
        check_status_headers(tmp_path)


def test_superseded_link_to_existing_file_passes(tmp_path: Path) -> None:
    doc = tmp_path / "old.md"
    doc.write_text("# Old\n**Status:** superseded by [new](new.md)\n", encoding="utf-8")
    (tmp_path / "new.md").write_text("# New\n**Status:** current\n", encoding="utf-8")
    check_status_headers(tmp_path)


def test_closed_status_issue_is_rejected(tmp_path: Path) -> None:
    status = tmp_path / "STATUS.md"
    status.write_text("See #123 for the old task.\n", encoding="utf-8")
    with pytest.raises(DocsCheckError, match="issue #123 is closed"):
        check_issue_refs(status, lambda _number: "CLOSED")


def test_issue_lookup_failure_fails_closed(tmp_path: Path) -> None:
    status = tmp_path / "STATUS.md"
    status.write_text("See #123 for the current task.\n", encoding="utf-8")
    with pytest.raises(DocsCheckError, match="cannot verify issue #123"):
        check_issue_refs(
            status, lambda _number: (_ for _ in ()).throw(RuntimeError("gh unavailable"))
        )


def test_open_status_issue_is_checked_once(tmp_path: Path) -> None:
    status = tmp_path / "STATUS.md"
    status.write_text("#42 is open; see #42 for details.\n", encoding="utf-8")
    checked: list[int] = []

    def issue_state(number: int) -> str:
        checked.append(number)
        return "open"

    check_issue_refs(status, issue_state)
    assert checked == [42]


def test_status_must_be_updated_after_latest_main_commit(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    project = repo / ".trazo" / "project"
    project.mkdir(parents=True)

    def git(*args: str) -> None:
        _git(repo, *args)

    git("init", "-b", "main")
    git("config", "user.email", "test@example.com")
    git("config", "user.name", "Docs Check Test")
    (project / "STATUS.md").write_text("# Status\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-m", "initial status")
    (repo / "unrelated.txt").write_text("new merged work\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-m", "latest merged change")

    with pytest.raises(DocsCheckError, match="predates main"):
        check_status_freshness(project, "main")

    (project / "STATUS.md").write_text("# Updated status\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-m", "refresh status")
    check_status_freshness(project, "main")


def test_shipped_project_doc_templates_have_lifecycle_headers() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    templates = [
        repo_root / "src/overlay/templates/charter.md",
        repo_root / "src/overlay/templates/workstream.md",
        *sorted((repo_root / "src/overlay/templates/docs").glob("*.md")),
    ]
    for path in templates:
        assert "**Status:** current" in "\n".join(
            path.read_text(encoding="utf-8").splitlines()[:5]
        ), path


def test_rules_define_one_home_and_cover_reports_and_research() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    rules = (repo_root / "src/overlay/rules.md").read_text(encoding="utf-8")
    adapter = (repo_root / "src/adapters/CLAUDE.md").read_text(encoding="utf-8")
    assert "One question has one authoritative home" in rules
    assert "`.trazo/project/reports/`" in adapter
    assert "`.trazo/project/workstreams/`" in adapter


def test_every_current_project_doc_has_a_lifecycle_header() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    check_status_headers(repo_root / ".trazo/project")


def test_docs_check_runs_from_wrapup_and_ci() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    wrapup = (repo_root / "src/overlay/skills/wrapup.md").read_text(encoding="utf-8")
    ci = (repo_root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    assert "make docs-check" in wrapup
    assert "run: make docs-check" in ci
    assert "issues: read" in ci
    assert "docs-check:" in makefile


def test_shared_start_skill_skips_superseded_docs() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    start = (repo_root / "src/overlay/skills/start.md").read_text(encoding="utf-8")
    assert "skip any doc marked `**Status:** superseded by" in start
