"""Changelog drafts are generated from closed issues in the named milestone (#130)."""

import os
import re
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts/changelog.sh"
BASH = shutil.which("bash")


def _run(tmp_path: Path, *, output: str, fail: bool = False) -> subprocess.CompletedProcess[str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    gh = bin_dir / "gh"
    gh.write_text(
        '#!/bin/sh\nprintf \'%s\\n\' "$@" > "$GH_ARGS"\n'
        '[ "$GH_FAIL" = 0 ] || exit 1\n'
        "printf '%s' \"$GH_OUTPUT\"\n"
    )
    gh.chmod(0o755)
    env = {
        **os.environ,
        "GH_ARGS": str(tmp_path / "gh-args"),
        "GH_FAIL": "1" if fail else "0",
        "GH_OUTPUT": output,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
    }
    return subprocess.run(  # noqa: S603, S607 - run our fixed local script with a stubbed gh
        [BASH or "bash", str(SCRIPT), "--version", "1.2.3"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_changelog_prints_closed_milestone_issues_without_editing_file(tmp_path: Path):
    changelog = REPO_ROOT / ".template/CHANGELOG.md"
    before = changelog.read_bytes()
    result = _run(tmp_path, output="- #12 Fix stale paths\n- #18 Add adapter\n")

    assert result.returncode == 0, result.stderr
    assert re.search(r"^## 1\.2\.3 \(\d{4}-\d{2}-\d{2}\)$", result.stdout, re.MULTILINE)
    assert "- #12 Fix stale paths\n- #18 Add adapter" in result.stdout
    args = (tmp_path / "gh-args").read_text().splitlines()
    assert args[:6] == ["issue", "list", "--state", "closed", "--milestone", "v1.2.3"]
    assert "sort_by(.number)" in args[-1]
    assert changelog.read_bytes() == before


def test_changelog_refuses_empty_milestone(tmp_path: Path):
    result = _run(tmp_path, output="")
    assert result.returncode != 0
    assert "no closed issues" in result.stderr


def test_changelog_fails_closed_when_github_query_fails(tmp_path: Path):
    result = _run(tmp_path, output="", fail=True)
    assert result.returncode != 0
    assert "could not query" in result.stderr
