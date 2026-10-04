"""The release process must stay mechanical, not advisory (issue #81).

Trazo is installed into a host repo from `src/`, so a consumer resolves
"latest" by reading a git tag. That only works if the tag, `.template/VERSION` and
`.template/CHANGELOG.md` keep agreeing. All three were hand-maintained and all three
had drifted: the repository carried a changelog claiming seven released versions and
**zero tags**, so a consumer had nothing resolvable to pin to.

The rule this pins is the one from `.trazo/project/adr/0006-release-process.md`: a release is an
immutable tag, `latest` is the highest tag, and `scripts/release.sh` is the only way to
cut one. An invariant enforced only in prose is advisory, so it is enforced here too.

Pinned mechanically, without running a real release:

  - `make release` exists, is phony, and delegates to the script;
  - `.template/VERSION` is `MAJOR.MINOR.PATCH`;
  - the changelog has an entry for the current version;
  - every released version in the changelog has a tag (`vX.Y.Z`) — the check that
    would have caught the zero-tag state;
  - `--dry-run` creates no tag.

`git` is real so tags are read for real; the script is only ever executed in
`--dry-run` mode against a throwaway repo, which is required never to write a tag.
"""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = REPO_ROOT / ".template" / "VERSION"
CHANGELOG = REPO_ROOT / ".template" / "CHANGELOG.md"
MAKEFILE = REPO_ROOT / "Makefile"
RELEASE = REPO_ROOT / "scripts" / "release.sh"
RULES = REPO_ROOT / ".trazo" / "rules.md"

GIT = shutil.which("git")
SH = shutil.which("bash")

# The first version released under the tag process defined by ADR 0006. Earlier
# versions were released without tags and are deliberately not backfilled.
PROCESS_VERSION = "0.6.0"

pytestmark = pytest.mark.skipif(
    not (GIT and SH), reason="git and bash are needed to read release tags"
)


def _version() -> str:
    return VERSION_FILE.read_text().strip()


def _changelog_versions() -> list[str]:
    """Versions with a dated changelog entry, oldest-last as written."""
    return re.findall(
        r"^## (\d+\.\d+\.\d+) \(\d{4}-\d{2}-\d{2}\)", CHANGELOG.read_text(), re.MULTILINE
    )


def _tags() -> set[str]:
    out = subprocess.run(  # noqa: S603 - our own argv, read-only `git tag -l`
        [GIT, "tag", "-l"], capture_output=True, text=True, cwd=REPO_ROOT, check=True
    )
    return set(out.stdout.split())


def test_version_is_semver():
    assert re.fullmatch(r"\d+\.\d+\.\d+", _version()), (
        f".template/VERSION is {_version()!r}; the release script requires "
        "MAJOR.MINOR.PATCH and no prereleases (ADR 0006 leaves that undecided)"
    )


def test_changelog_has_entry_for_current_version():
    assert _version() in _changelog_versions(), (
        f"version {_version()} has no '## {_version()} (YYYY-MM-DD)' entry in "
        ".template/CHANGELOG.md; make release refuses to cut an undescribed version"
    )


def test_every_merged_changelog_version_has_a_tag():
    """The check that would have caught zero tags.

    Each version claimed in the changelog must exist as an immutable `vX.Y.Z` tag,
    because that tag is what a consumer resolves.

    Two deliberate limits, both about not inventing history:

    - **Versions before 0.6.0 are exempt.** They were released before this process
      existed (ADR 0006) and were never tagged. Backfilling tags onto commits nobody
      tagged would fabricate a release record; `.template/CHANGELOG.md` says so
      explicitly instead.
    - **Unmerged work is exempt.** The check applies once the release commit is
      reachable from the default branch, because that is when the version becomes real.
      On the PR that introduces the changelog entry the tag cannot exist yet, and
      failing there would block the very merge the process depends on.
    """
    unreleased = set(_changelog_versions()) - set(_tagged_versions())
    assert PROCESS_VERSION in _changelog_versions(), (
        f"{PROCESS_VERSION}, the version this process starts at, has no changelog entry"
    )
    # Versions before the process began are exempt: they predate tagging entirely.
    pre_process = {
        v for v in _changelog_versions() if _semver_key(v) < _semver_key(PROCESS_VERSION)
    }
    pending = unreleased - pre_process - {PROCESS_VERSION}
    merged = sorted(pending & _versions_on_origin_main())
    assert not merged, (
        f"version(s) {merged} are merged to the default branch and claimed released in "
        ".template/CHANGELOG.md, but have no `vX.Y.Z` tag; cut them with "
        "`make release`, or drop the entry if they were never released"
    )


def _semver_key(version: str) -> tuple[int, int, int]:
    major, minor, patch = version.split(".")
    return (int(major), int(minor), int(patch))


def _tagged_versions() -> set[str]:
    """Versions with a real `vX.Y.Z` tag."""
    return {m.group(1) for tag in _tags() if (m := re.fullmatch(r"v(\d+\.\d+\.\d+)", tag))}


def _versions_on_origin_main() -> set[str]:
    """Changelog versions whose release commit is already on the default branch."""
    main_branch = subprocess.run(  # noqa: S603 - our own argv, read-only
        [GIT, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    ).stdout.strip()
    main_branch = main_branch or "origin/main"
    merged = subprocess.run(  # noqa: S603 - our own argv, read-only
        [GIT, "log", "--format=%H", main_branch],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    ).stdout.split()

    released_on_main: set[str] = set()
    for commit in merged:
        show = subprocess.run(  # noqa: S603 - our own argv, read-only
            [GIT, "show", f"{commit}:.template/VERSION"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        if show.returncode == 0 and show.stdout.strip():
            released_on_main.add(show.stdout.strip())
    return released_on_main


def test_makefile_exposes_release_target():
    makefile = MAKEFILE.read_text()
    assert re.search(r"^release:", makefile, re.MULTILINE), (
        "Makefile has no `release` target; ADR 0006 makes `make release` the only "
        "supported way to cut a release"
    )
    phony = re.search(r"^\.PHONY:.*$", makefile, re.MULTILINE)
    assert phony and "release" in phony.group(0), (
        "`release` is missing from .PHONY, so make may skip it if a file of that name ever exists"
    )
    target = re.search(r"^release:.*(?:\n\t.*)+", makefile, re.MULTILINE)
    assert target and "scripts/release.sh" in target.group(0), (
        "the `release` target must delegate to scripts/release.sh so its validation "
        "cannot be bypassed"
    )


def test_release_script_exists_and_is_executable():
    assert RELEASE.exists(), "scripts/release.sh is missing"
    assert RELEASE.stat().st_mode & 0o111, (
        "scripts/release.sh is not executable; `make release` invokes it directly"
    )


def test_release_script_rejects_unknown_arguments():
    """Typos must fail, not fall through to a release."""
    result = subprocess.run(  # noqa: S603 - our own argv, release.sh in this repo
        [SH, str(RELEASE), "--definitely-not-a-flag"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode != 0, "an unknown argument was accepted by release.sh"


def test_rules_state_the_release_invariant():
    """The rule exists in prose too, so a reader of rules.md sees it.

    This is the one place a duplicate is the point: the test proves the script enforces
    the invariant, and the rule tells a reader what it is.
    """
    assert "releases are immutable tags" in RULES.read_text().lower(), (
        ".trazo/rules.md has no 'Releases are immutable tags' rule (ADR 0006)"
    )


def test_rules_state_the_release_cadence():
    """A release is a body of work, not a pull request.

    This repository shipped four minor versions in one afternoon (0.6.0, 0.7.0, 0.8.0,
    0.9.0), so `0.9.0` read as "nearly stable" on a three-day-old repo. The cause was that
    `CONTRIBUTING.md` told you to bump the version on every change and said nothing about
    *when* a release happens, so every merged PR became one.

    Cadence is a judgement call and no test can enforce it directly — a check like "reject
    two versions on one date" would fail legitimate same-day patch releases. What can be
    enforced is that the decision is written down where the next contributor meets it, which
    is the same argument as the rules above.
    """
    rules = " ".join(RULES.read_text().lower().split())
    assert "release when there is something to release" in rules, (
        ".trazo/rules.md has no release-cadence rule; without it the version history drifts "
        "toward one release per pull request"
    )
    assert "not once per merged pull request" in rules, (
        "the cadence rule must say what it rules out, not only what it prefers"
    )
    contributing = " ".join((REPO_ROOT / "CONTRIBUTING.md").read_text().lower().split())
    assert "not once per merged pr" in contributing, (
        "CONTRIBUTING.md must carry the cadence rule too — that is where the version bump "
        "is described, and where this rule was originally misread"
    )


def _throwaway_repo(tmp: str, *, version: str = "9.9.9") -> Path:
    """A throwaway repo with a real origin, so release.sh runs its full path.

    The remote matters: release.sh refuses to tag a commit that is not already pushed
    (ADR 0006), so a repo without one can only ever exercise the refusal, not the tag.

    The branch is forced to `main` explicitly rather than inherited. Cloning an empty
    repository leaves HEAD on whatever `init.defaultBranch` says, which is `master` on
    the CI runner's git, and the first version of this test pushed a `main` that did not
    exist. Everything here pushes `HEAD` rather than naming a branch.
    """
    root = Path(tmp)
    remote = Path(f"{tmp}-remote.git")
    subprocess.run(  # noqa: S603 - our own argv, throwaway paths under tmp
        [GIT, "init", "-q", "--bare", "-b", "main", str(remote)], check=True
    )
    subprocess.run(  # noqa: S603 - our own argv, throwaway path
        [GIT, "clone", "-q", str(remote), str(root)], check=True
    )
    for cmd in (
        ["config", "user.email", "test@example.com"],
        ["config", "user.name", "Test"],
        ["config", "commit.gpgsign", "false"],
        # Force the branch name; do not trust init.defaultBranch.
        ["symbolic-ref", "HEAD", "refs/heads/main"],
    ):
        subprocess.run([GIT, *cmd], cwd=root, check=True)  # noqa: S603 - our argv

    (root / ".template").mkdir()
    (root / "scripts").mkdir()
    (root / ".template" / "VERSION").write_text(f"{version}\n")
    (root / ".template" / "CHANGELOG.md").write_text(
        f"# changelog\n\n## {version} (2026-09-30)\n- test release\n"
    )
    shutil.copy(RELEASE, root / "scripts" / "release.sh")
    (root / "scripts" / "release.sh").chmod(0o755)

    _commit_and_push(root, "init")
    return root


def _commit_and_push(root: Path, message: str) -> None:
    subprocess.run([GIT, "add", "-A"], cwd=root, check=True)  # noqa: S603 - our argv
    subprocess.run(  # noqa: S603 - our argv
        [GIT, "commit", "-q", "-m", message], cwd=root, check=True
    )
    # Push HEAD, not a branch name, so this works whatever HEAD is called.
    subprocess.run(  # noqa: S603 - our own argv, throwaway remote
        [GIT, "push", "-q", "-u", "origin", "HEAD:refs/heads/main"], cwd=root, check=True
    )


def _git(root: Path, *args: str) -> str:
    return subprocess.run(  # noqa: S603 - our own argv, read-only queries
        [GIT, *args], capture_output=True, text=True, cwd=root, check=True
    ).stdout


def _stub_gh(tmp_bin: Path, *, out: str = "0", rc: int = 0) -> None:
    """A fake `gh` that prints what the milestone jq filter would, so no network is used."""
    tmp_bin.mkdir(parents=True, exist_ok=True)
    gh = tmp_bin / "gh"
    gh.write_text(f"#!/bin/sh\nprintf '%s' '{out}'\n[ -z '{out}' ] || echo\nexit {rc}\n")
    gh.chmod(0o755)


def _release(
    root: Path, *args: str, gh_out: str | None = "0", gh_rc: int = 0
) -> subprocess.CompletedProcess:
    """Run release.sh with a stubbed gh first on PATH; gh_out=None means no gh at all."""
    import os

    bin_dir = Path(f"{root}-bin")
    env = dict(os.environ)
    if gh_out is None:
        bin_dir.mkdir(parents=True, exist_ok=True)
        # Only the tools release.sh needs, no gh.
        for tool in ("git", "sed", "grep", "tr", "wc", "dirname", "cat", "printf"):
            found = shutil.which(tool)
            if found and not (bin_dir / tool).exists():
                (bin_dir / tool).symlink_to(found)
        env["PATH"] = str(bin_dir)
    else:
        _stub_gh(bin_dir, out=gh_out, rc=gh_rc)
        env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    return subprocess.run(  # noqa: S603 - release.sh copy in a throwaway repo
        [SH, "scripts/release.sh", *args],
        capture_output=True,
        text=True,
        cwd=root,
        env=env,
    )


def test_dry_run_creates_no_tag():
    """`--dry-run` is the safe preview; it must not write a tag.

    Exercises the happy path (a valid, pushed release) so the assertion is meaningful:
    an earlier version of this test used a repo with no remote, so release.sh refused
    before it ever reached the tag step and the test passed for the wrong reason.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = _throwaway_repo(tmp)
        result = _release(root, "--dry-run")

        assert result.returncode == 0, (
            f"--dry-run failed on a valid repo: {result.stdout}{result.stderr}"
        )
        assert "9.9.9" in result.stdout, (
            f"--dry-run did not report the version it would cut: {result.stdout}"
        )
        assert "v9.9.9" not in _git(root, "tag", "-l").split(), (
            f"--dry-run created a tag: {result.stdout}{result.stderr}"
        )


def test_release_creates_an_annotated_tag():
    """The happy path: a valid, pushed repo gets an annotated `vX.Y.Z` tag.

    `git push` reaches a throwaway bare repo, so this runs the real tagging and pushing
    code without touching the network or the real repository.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = _throwaway_repo(tmp)
        result = _release(root)

        assert result.returncode == 0, (
            f"release failed on a valid repo: {result.stdout}{result.stderr}"
        )
        tags = _git(root, "tag", "-l").split()
        assert "v9.9.9" in tags, f"release did not create v9.9.9 (tags: {tags})"
        # Annotated, not lightweight: `git tag -l` alone cannot tell them apart.
        kind = _git(root, "cat-file", "-t", "v9.9.9").strip()
        assert kind == "tag", f"v9.9.9 is a {kind}, expected an annotated tag"
        # And it must reach origin, or a consumer cannot resolve it.
        remote = _git(root, "ls-remote", "--tags", "origin")
        assert "v9.9.9" in remote, "the tag was not pushed to origin"


def test_release_refuses_an_already_tagged_version():
    """Tags are never moved. Re-releasing the same version must fail."""
    with tempfile.TemporaryDirectory() as tmp:
        root = _throwaway_repo(tmp)
        assert _release(root).returncode == 0, "setup release failed"
        result = _release(root)

        assert result.returncode != 0, "re-releasing an existing version succeeded"
        assert "already exists" in result.stderr, f"unexpected message: {result.stderr}"


def test_release_refuses_a_version_with_no_changelog_entry():
    """An undescribed version is not shipped."""
    with tempfile.TemporaryDirectory() as tmp:
        root = _throwaway_repo(tmp)
        (root / ".template" / "CHANGELOG.md").write_text("# changelog\n\n## 0.0.1 (x)\n")
        _commit_and_push(root, "strip the entry")
        result = _release(root)

        assert result.returncode != 0, "released a version with no changelog entry"
        assert "CHANGELOG" in result.stderr, f"unexpected message: {result.stderr}"


def test_release_refuses_a_non_semver_version():
    with tempfile.TemporaryDirectory() as tmp:
        root = _throwaway_repo(tmp, version="1.2")
        result = _release(root)

        assert result.returncode != 0, "accepted version '1.2'"
        assert "MAJOR.MINOR.PATCH" in result.stderr, f"unexpected message: {result.stderr}"


def test_release_refuses_an_unpushed_commit():
    """The tagged commit must already be on the default branch."""
    with tempfile.TemporaryDirectory() as tmp:
        root = _throwaway_repo(tmp)
        (root / "extra.txt").write_text("local only\n")
        subprocess.run([GIT, "add", "-A"], cwd=root, check=True)  # noqa: S603 - our argv
        subprocess.run(  # noqa: S603 - our argv
            [GIT, "commit", "-q", "-m", "local"], cwd=root, check=True
        )
        result = _release(root)

        assert result.returncode != 0, "tagged a commit that was never pushed"
        assert "push or rebase" in result.stderr, f"unexpected message: {result.stderr}"
        assert "v9.9.9" not in _git(root, "tag", "-l").split(), "a tag was created anyway"


def test_release_refuses_a_dirty_tree():
    with tempfile.TemporaryDirectory() as tmp:
        root = _throwaway_repo(tmp)
        (root / "scratch.txt").write_text("uncommitted\n")
        result = _release(root)

        assert result.returncode != 0, "released from a dirty tree"
        assert "not clean" in result.stderr, f"unexpected message: {result.stderr}"


def test_release_refuses_a_non_default_branch():
    """Releases are cut from the default branch, not from a feature branch."""
    with tempfile.TemporaryDirectory() as tmp:
        root = _throwaway_repo(tmp)
        subprocess.run(  # noqa: S603 - our own argv, throwaway branch name
            [GIT, "checkout", "-q", "-b", "feature"], cwd=root, check=True
        )
        result = _release(root)

        assert result.returncode != 0, "released from a feature branch"
        assert "cut from" in result.stderr, f"unexpected message: {result.stderr}"


def test_release_refuses_while_the_milestone_has_open_issues():
    """A release is a milestone (ADR 0012): open issues mean the scope is not done."""
    with tempfile.TemporaryDirectory() as tmp:
        root = _throwaway_repo(tmp)
        result = _release(root, gh_out="3")

        assert result.returncode != 0, "released with 3 open issues in the milestone"
        assert "open issue" in result.stderr, f"unexpected message: {result.stderr}"
        assert "v9.9.9" not in _git(root, "tag", "-l").split(), "a tag was created anyway"


def test_release_refuses_when_there_is_no_milestone():
    with tempfile.TemporaryDirectory() as tmp:
        root = _throwaway_repo(tmp)
        result = _release(root, gh_out="")

        assert result.returncode != 0, "released with no milestone for the version"
        assert "no GitHub milestone" in result.stderr, f"unexpected message: {result.stderr}"


def test_release_fails_closed_when_gh_errors():
    with tempfile.TemporaryDirectory() as tmp:
        root = _throwaway_repo(tmp)
        result = _release(root, gh_out="0", gh_rc=1)

        assert result.returncode != 0, "released although the milestone lookup failed"
        assert "refusing" in result.stderr, f"unexpected message: {result.stderr}"
        assert "v9.9.9" not in _git(root, "tag", "-l").split(), "a tag was created anyway"


def test_release_fails_closed_when_gh_is_missing():
    with tempfile.TemporaryDirectory() as tmp:
        root = _throwaway_repo(tmp)
        result = _release(root, gh_out=None)

        assert result.returncode != 0, "released without gh available"
        assert "gh not found" in result.stderr, f"unexpected message: {result.stderr}"
        assert "v9.9.9" not in _git(root, "tag", "-l").split(), "a tag was created anyway"


def test_rules_state_a_release_is_a_milestone():
    rules = " ".join(RULES.read_text().lower().split())
    assert "a release is a milestone" in rules, "rules.md does not say a release is a milestone"
    assert "immutable tags" in rules, "the immutable-tags rule must remain"
