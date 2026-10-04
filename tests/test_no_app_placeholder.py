"""Guards for the removal of the application placeholder (issue #51).

#51 removed `src/app/`, `tests/test_smoke.py` and the `run`/`build` Makefile targets.
The risk is not the deletion -- it is the *silent* aftermath. Four things in this repo
pointed at the placeholder, and three of them fail quietly rather than loudly:

- a packaging config that names a package which no longer exists, so `uv sync` fails at
  build time with a hatchling traceback that reads like an environment problem;
- a `CMD` in the Dockerfile invoking a module that is gone, so the image builds and then
  fails at run time, which CI does not catch if it only builds;
- `make run` / `make build` targets that keep working as no-ops, so a derived project
  inherits commands that silently do nothing.

None of these are caught by "the tests pass". The tests are the thing that has to keep
passing, which is why the harness guards (#14) must survive the removal -- they are real
protections, not app boilerplate, and deleting them would reopen a fixed security hole.
"""

import re
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = REPO_ROOT / "Makefile"
PYPROJECT = REPO_ROOT / "pyproject.toml"
DOCKERFILE = REPO_ROOT / "Dockerfile"

GIT = shutil.which("git")


def _tracked_files() -> set[str]:
    """The paths git tracks, which is what "removed" has to mean.

    Asserting on the working tree is wrong here, and it was wrong in a way that only showed
    up on a machine that had run the code before #51. `src/app/__pycache__` is gitignored,
    so it keeps the *directory* alive long after the package was deleted from the repo: the
    test then failed for a reason true on no fresh clone, while CI stayed green because a
    runner never had the stale directory.
    """
    if not GIT:
        return set()
    out = subprocess.run(  # noqa: S603 - our own argv, read-only
        [GIT, "ls-files"], capture_output=True, text=True, cwd=REPO_ROOT, check=True
    )
    return set(out.stdout.split())


# Files that may legitimately name the removed package.
#
# The ADR records a measured snapshot of the repo at commit b42b6d0, when the application
# package did exist. Rewriting an append-only record to match a later change would make it
# false -- the mistake #49 exists for -- so it is whitelisted rather than edited. The
# directory moved to `.trazo/` in #50; only the current location is listed, because the old
# one no longer exists and so cannot be referenced. Note that this comment deliberately
# avoids spelling the pre-#50 path: `test_trazo_layout.py` asserts that no file references
# it, which is the right outcome for a live link and the wrong one for a comment.
ALLOWED_MENTIONS = (".trazo/project/adr/000", "tests/test_no_app_placeholder.py")

# The harness guards that must survive. Named individually because "the test suite still
# passes" is satisfied by an empty suite.
HARNESS_GUARDS = ("tests/test_codeowners.py",)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_the_placeholder_files_are_gone() -> None:
    """Asserted against git rather than the filesystem, and see `_tracked_files` for why.

    A gitignored `__pycache__` from a pre-#51 run keeps the directory present on disk while
    the package has been gone from the repository for days. Asserting on the filesystem makes
    the failure track local state instead of the code -- true on one machine, false on every
    fresh clone, and invisible to CI, which is the opposite of what a guard is for.
    """
    tracked = _tracked_files()
    for rel in ("src/app", "tests/test_smoke.py"):
        assert not any(p == rel or p.startswith(f"{rel}/") for p in tracked), (
            f"{rel} is still tracked; #51 removed it"
        )
    # Bare `src/` is no longer asserted empty, because `src/` is now the product tree
    # (#94): `src/overlay/` and `src/adapters/` are what a host receives. What #51
    # removed was the *application* -- `src/app/`, the smoke test, and the run/build
    # targets -- not the idea of a source directory. The `src/app` assertion above is
    # unchanged and still catches the scaffold coming back.


def test_nothing_references_the_removed_package() -> None:
    """Any surviving reference is a build break or a doc that lies."""
    offenders = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in {".py", ".toml", ".md", ".yml", ".yaml"}:
            continue
        rel = str(path.relative_to(REPO_ROOT))
        if rel.startswith((".git/", ".worktrees/", ".venv/")) or any(
            rel.startswith(a) for a in ALLOWED_MENTIONS
        ):
            continue
        try:
            text = _text(path)
        except (UnicodeDecodeError, ValueError):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if re.search(r"src/app|app\.main|from app\b|import app\b", line):
                offenders.append(f"{rel}:{lineno}: {line.strip()[:70]}")
    assert not offenders, "references to the removed `app` package:\n" + "\n".join(offenders)


def test_the_run_and_build_targets_are_gone() -> None:
    """A target that survives as a no-op is worse than no target: a derived project
    inherits a `make build` that reports success without building anything."""
    makefile = _text(MAKEFILE)
    for target in ("run:", "build:"):
        assert not re.search(rf"^{re.escape(target)}", makefile, re.MULTILINE), (
            f"`make {target[:-1]}` still exists; #51 removed it"
        )
    # .PHONY must not still advertise them.
    phony = re.search(r"^\.PHONY:\s*(.+)$", makefile, re.MULTILINE)
    assert phony, "no .PHONY line in the Makefile"
    for target in ("run", "build"):
        assert target not in phony.group(1).split(), f".PHONY still lists {target}"


def test_the_project_is_not_packaged() -> None:
    """`uv sync` builds the project unless told not to. With no module, hatchling fails
    at build time and the error reads like a broken environment rather than a missing
    package -- the exact trap #51 warned about."""
    pyproject = _text(PYPROJECT)
    assert re.search(r"^\[tool\.uv\]\s*$", pyproject, re.MULTILINE), (
        "no [tool.uv] table, so uv will try to build a wheel for a project with no module"
    )
    assert re.search(r"^package\s*=\s*false", pyproject, re.MULTILINE), (
        "[tool.uv] must set package = false; see the comment in pyproject.toml"
    )
    assert not re.search(r"^\s*packages\s*=", pyproject, re.MULTILINE), (
        "a wheel package path is still configured for a package that no longer exists"
    )


def test_the_dockerfile_still_runs_something() -> None:
    """The image used to `python -m app.main`. With the module gone, a Dockerfile that
    still says so builds cleanly and fails on run -- and CI only builds."""
    dockerfile = _text(DOCKERFILE)
    assert not re.search(r"app\.main", dockerfile), (
        "the Dockerfile still invokes the removed module; it builds and then fails"
    )
    assert re.search(r"^CMD\s+", dockerfile, re.MULTILINE), "the image has no CMD"
    assert not re.search(r"^COPY\s+src\b", dockerfile, re.MULTILINE), (
        "the Dockerfile still copies src/, which no longer exists"
    )


def test_the_harness_guards_survived() -> None:
    """Named individually: "the suite passes" is also true of an empty suite, and these
    two protect CODEOWNERS from the find/replace bug of issue #14."""
    for rel in HARNESS_GUARDS:
        path = REPO_ROOT / rel
        assert path.exists(), f"{rel} was deleted; it is a real guard, not app boilerplate"
        assert re.search(r"^def test_", _text(path), re.MULTILINE), f"{rel} has no tests"
