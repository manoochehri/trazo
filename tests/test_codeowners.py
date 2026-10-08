"""Guards for `.github/CODEOWNERS` (issue #14).

`CODEOWNERS` contains the word `OWNER`, so a template-wide find/replace of `OWNER`
used to rewrite the path `/.github/CODEOWNERS` into `/.github/CODE<user>S`. The file
then matched no rule at all and could be edited without the owner's review.
"""

import fnmatch
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CODEOWNERS = REPO_ROOT / ".github" / "CODEOWNERS"


def _rules() -> list[tuple[str, list[str]]]:
    """Return (pattern, owners) for every non-comment line of CODEOWNERS."""
    rules: list[tuple[str, list[str]]] = []
    for line in CODEOWNERS.read_text(encoding="utf-8").splitlines():
        parts = line.split("#", 1)[0].split()
        if parts:
            rules.append((parts[0], parts[1:]))
    return rules


def _covers(pattern: str, path: str) -> bool:
    """Approximate GitHub's CODEOWNERS matching for one repo-relative path.

    Deliberately simple: it only reports "covered" for patterns that can name this
    exact file, which is all a self-protection check needs. No `**` support.
    """
    pattern = pattern.rstrip("/")
    if pattern.startswith("/"):
        pattern = pattern[1:]
    if "/" in pattern:
        return fnmatch.fnmatch(path, pattern)
    return fnmatch.fnmatch(Path(path).name, pattern)


def _tracked_paths() -> set[str]:
    git = shutil.which("git")
    assert git, "git is required to inspect tracked paths"
    result = subprocess.run(  # noqa: S603 - resolved executable, fixed read-only argv
        [git, "ls-files", "--cached"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return set(result.stdout.splitlines())


def test_codeowners_protects_itself():
    """Without a rule matching the file itself, it can be edited unreviewed."""
    covered_by = [pattern for pattern, _ in _rules() if _covers(pattern, ".github/CODEOWNERS")]
    assert covered_by, "no rule in .github/CODEOWNERS covers .github/CODEOWNERS itself"


def test_codeowners_paths_are_paths_not_usernames():
    """The owner's name inside a path means a find/replace mangled it.

    The handle comes from CODEOWNERS itself rather than from `.template/UPSTREAM`, which
    named the upstream repo for the template-fork model that decision 0005 replaced. It
    was a second copy of the same identity in a different file, so it could drift, and a
    guard that depends on a file nobody edits is a guard one deletion away from breaking
    (issue #73).
    """
    handles = {owner for _, owners in _rules() for owner in owners}
    assert handles, ".github/CODEOWNERS has no owners to compare paths against"
    for pattern, owners in _rules():
        for owner in handles:
            assert owner not in pattern, f"path {pattern!r} contains the owner's name {owner!r}"
        assert owners, f"path {pattern!r} has no owner"


def test_codeowners_owners_are_handles():
    for pattern, owners in _rules():
        for owner in owners:
            assert owner.startswith("@"), f"{owner!r} on {pattern!r} is not an @handle"


def test_every_codeowners_pattern_matches_a_tracked_path():
    tracked = _tracked_paths()
    for pattern, _ in _rules():
        normalized = pattern.lstrip("/")
        matches = [path for path in tracked if fnmatch.fnmatchcase(path, normalized)]
        if normalized.endswith("/"):
            directory = normalized.rstrip("/")
            matches.extend(path for path in tracked if path.startswith(f"{directory}/"))
        assert matches, f"CODEOWNERS pattern {pattern!r} matches no tracked path"
