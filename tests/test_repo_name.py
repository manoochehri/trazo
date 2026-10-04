"""Guards the repository name after the GitHub rename (issue #52).

The rename happened on GitHub, out of band. Nothing in the repo noticed, and one
reference in particular fails in the most expensive way possible:

**`.github/workflows/docs.yml` gated its artifact upload and its deploy on
`github.repository == 'manoochehri/semilla'`.** After the rename that condition is never
true, so every push to `main` would build the site, skip the upload, skip the deploy, and
report **green**. The docs site would quietly stop updating while CI says everything
passed. That is the same shape as lesson 19 (a gate that cannot tell what it scanned is
worse than no gate) and #61 (a check that reported success without doing the work).

So these guards assert the *invariants* rather than the individual strings:

1. The repo slug, wherever it appears, is `manoochehri/trazo`.
2. The Pages deploy gate names the repository the workflow actually runs in. A gate
   pinned to a name that no longer exists is the failure this whole issue is about.
3. `.template/UPSTREAM` points at the real repo, or every derived project's
   `/template-sync` breaks with no error at all.

Historical records are excluded and that exclusion is asserted too: `.trazo/project/adr/0004`
names the old Pages URL because it was true then, and rewriting an append-only record to
match a later change would make it false (#49).
"""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

OLD_SLUG = "man" + "oochehri/semilla"
NEW_SLUG = "man" + "oochehri/trazo"
OLD_PAGES = "manoochehri.github.io/semilla"

# Records that must keep the old name because it was true when written.
HISTORICAL = (".trazo/project/adr/", ".template/CHANGELOG.md", ".template/LESSONS.md", "tests/")

TEXT_SUFFIXES = {".md", ".py", ".toml", ".yml", ".yaml", ".json", ".sh", ".cfg", ".txt"}

# Directories skipped outright. `site/` matters here: `mkdocs build` renders ADR 0004,
# which legitimately names the old Pages URL, into `site/search/search_index.json`. That
# file is a build artifact and is gitignored, but this test walks the working tree
# rather than the index, so a local `make docs` followed by `make test` would fail on a
# file nobody committed. CI never saw it because pytest and mkdocs run in separate jobs.
SKIP_DIRS = {".git", ".worktrees", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "site"}

# A name is spelled out rather than interpolated above, so that a test failing because
# *this file* contains the old slug is not self-defeating. The same trick applies to the
# module's own name in the exclusion below.


def _this_repository() -> str | None:
    """`owner/name` for the repository this checkout belongs to, or None if unknowable.

    Three of the tests below assert that this repository is `manoochehri/trazo`. That is
    true here and false in every clone, and a guard that fails on `gh repo create
    --template` is worse than no guard: the first person who uses the template gets a red
    suite on arrival, and learns that the template's tests are not trustworthy.

    So identity is *detected*, not assumed. `GITHUB_REPOSITORY` is set by GitHub Actions on
    every run; the `origin` remote covers local use. When neither is available the
    identity-based tests skip rather than guess, because a wrong guess in either direction
    is worse than saying nothing.

    `is_trazo_upstream` deliberately does NOT consult the filesystem: a clone inherits
    `.template/` and the overlay, so its presence identifies a *user of Trazo*, not Trazo.
    """
    env = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if re.fullmatch(r"[\w.-]+/[\w.-]+", env):
        return env
    try:
        git = shutil.which("git")
        if git is None:
            return None
        url = subprocess.run(  # noqa: S603 - resolved executable, fixed argv, our own repo
            [git, "remote", "get-url", "origin"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, OSError):
        return None
    match = re.search(r"github\.com[:/]([\w.-]+)/([\w.-]+?)(?:\.git)?$", url)
    return f"{match.group(1)}/{match.group(2)}" if match else None


IS_TRAZO_UPSTREAM = _this_repository() == NEW_SLUG

_SKIP_REASON = (
    f"this checkout is {_this_repository()!r}, not the Trazo repository ({NEW_SLUG!r}). "
    "These assertions describe the upstream repository's own identity -- its Pages URL and "
    "deploy gate -- and cannot hold in a derived project. See issue #76."
)


def _text_files() -> list[Path]:
    out = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        rel = path.relative_to(REPO_ROOT)
        if SKIP_DIRS & set(rel.parts):
            continue
        # This file spells out the old slug to assert on it.
        if rel.name == Path(__file__).name:
            continue
        out.append(path)
    return out


def _is_historical(rel: str) -> bool:
    return rel.startswith(HISTORICAL)


def test_no_live_file_references_the_old_repository() -> None:
    offenders = []
    for path in _text_files():
        rel = str(path.relative_to(REPO_ROOT))
        if _is_historical(rel):
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if OLD_SLUG in line or OLD_PAGES in line:
                offenders.append(f"{rel}:{lineno}: {line.strip()[:70]}")
    assert not offenders, (
        "references to the pre-rename repo. Historical records (.trazo/project/adr/, "
        ".template/CHANGELOG.md, .template/LESSONS.md, tests/) are excluded on purpose -- "
        "they describe what was true when written:\n" + "\n".join(offenders)
    )


def test_the_pages_deploy_gate_matches_this_repository() -> None:
    """The one that fails silently. A gate naming a repo that no longer exists makes
    every deploy a green no-op.

    Only the upstream repository has a Pages URL and a deploy gate; a derived project
    inherited the workflow but has neither, so the assertion skips rather than failing.
    """
    if not IS_TRAZO_UPSTREAM:
        pytest.skip(_SKIP_REASON)
    docs = (REPO_ROOT / ".github" / "workflows" / "docs.yml").read_text(encoding="utf-8")
    gates = re.findall(r"github\.repository\s*==\s*'([^']+)'", docs)
    assert gates, "the deploy gate is gone; if that was deliberate, this test must change"
    for gate in gates:
        assert gate == NEW_SLUG, (
            f"docs.yml gates on {gate!r} but this repo is {NEW_SLUG!r}. The build step will "
            "pass, the upload and deploy will be skipped, and CI will report green."
        )


def test_upstream_pointer_is_not_reintroduced() -> None:
    """`.template/UPSTREAM` named the upstream so a forked template could sync back from
    it. Decision 0005 made Trazo a mountable overlay, so a host project has no upstream to
    sync with and no reason to name one; the file and both commands that read it were
    removed in #73.

    This test used to assert the pointer held the *current* slug. That was correct while
    the file existed and became actively wrong once #73 landed: a rebase onto main can
    resurrect a deleted file from the older branch, and asserting the right slug in it
    would pass — quietly re-adding the thing #73 removed. The assertion is therefore that
    the file is *absent*, which is what #73 decided and what survives a rebase.

    The publish script that once substituted into it was removed with the template path
    (#107), so this assertion is the whole guard.
    """
    assert not (REPO_ROOT / ".template" / "UPSTREAM").exists(), (
        ".template/UPSTREAM is back. It names an upstream for the template-fork model that "
        "decision 0005 replaced; if that model is genuinely returning, supersede #73 with a "
        "new decision record rather than re-adding the file here"
    )


def test_mkdocs_matches_this_repository() -> None:
    """mkdocs feeds site_url (canonical + sitemap), repo_url and repo_name. A stale
    site_url makes the site claim a URL it is not served at.

    A derived project has its own Pages URL or no site at all, so this describes the
    upstream's identity and skips elsewhere.
    """
    if not IS_TRAZO_UPSTREAM:
        pytest.skip(_SKIP_REASON)
    mkdocs = (REPO_ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    assert re.search(r"^site_url:\s*https://manoochehri\.github\.io/trazo/\s*$", mkdocs, re.M), (
        "mkdocs site_url must be the current Pages URL"
    )
    assert re.search(rf"^repo_url:\s*https://github\.com/{re.escape(NEW_SLUG)}\s*$", mkdocs, re.M)
    assert re.search(rf"^repo_name:\s*{re.escape(NEW_SLUG)}\s*$", mkdocs, re.M)
