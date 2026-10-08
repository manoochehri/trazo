"""Guards for the `src/` + `.trazo/` layout (issues #50, #92, #96; ADR 0010).

`src/` is the canonical product and `.trazo/` is the installed copy that governs this
repository. The tests below assert that split, and fail if the old single-directory
layout (rules edited in place under `.trazo/`, product state mixed into the install) comes
back.

The move in #50 is the kind of change that looks finished the moment the files are in
place, and is actually finished weeks later when some doc still points at a path that no
longer exists. `docs/CHARTER.md` was referenced from 29 tracked files; the failure mode is
not a broken build, it is a doc that quietly tells a future session to read a file that is
not there.

Two properties are asserted:

1. **No tracked file points at a path that does not exist.** The issue's own done-when.
   The exceptions are deliberate and listed, so a new exception has to be argued for.
2. **The moved trees are where the rules say they are, and the old paths are gone.**
   Otherwise a half-finished move leaves both copies, and the next agent reads whichever
   it finds first.
"""

import re
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

TEMPLATE_TOKENS = ("NNNN", "TODO", "YYYY")

TEXT_SUFFIXES = {".md", ".py", ".toml", ".yml", ".yaml", ".json", ".sh", ".cfg", ".txt"}

# The paths that moved in #50, and where they went.
MOVED = (
    "docs/CHARTER.md",
    "docs/ARCHITECTURE.md",
    "docs/ADVISOR.md",
    "docs/decisions/",
    "docs/workstreams/",
)

# ADR 0010: `src/` is the canonical source and holds everything a host receives. `.trazo/`
# is the installed copy that governs this repository, and is never hand-edited. The
# product is edited in `src/` and the installed copy is refreshed from it.
PRODUCT = "src"
OVERLAY = "src/overlay"
ADAPTERS = "src/adapters"

# Installed copy -> canonical source. Every row is a file a host receives; none of them
# is edited in place on the left-hand side.
INSTALLED_FROM_SRC = {
    ".trazo/rules.md": "src/overlay/rules.md",
    ".trazo/ADVISOR.md": "src/overlay/ADVISOR.md",
    ".trazo/ARCHITECTURE.md": "src/overlay/ARCHITECTURE.md",
    "CLAUDE.md": "src/adapters/CLAUDE.md",
    "AGENTS.md": "src/adapters/AGENTS.md",
    ".claude/settings.json": "src/adapters/claude/settings.json",
}

# ADR 0011: ours lives in `.trazo/project/`; the host's is a template under `src/`.
PROJECT = ".trazo/project"
OURS = (
    "charter/charter.md",
    "STATUS.md",
    "PLAN.md",
    "RUNBOOK.md",
    "SKEPTIC_BAR.md",
    "reports",
    "adr",
    "workstreams",
)
HOST_TEMPLATES = (
    "charter.md",
    "adr.md",
    "workstream.md",
    "docs/STATUS.md",
    "docs/PLAN.md",
    "docs/RUNBOOK.md",
    "docs/SKEPTIC_BAR.md",
    "docs/reports",
)
# The decision records are append-only history and name the layouts they were written under.
HISTORY = (".trazo/project/adr/", ".template/CHANGELOG.md")


# The two adapters are installed as a marked block inside the host's own file (#133), so the
# repo's root copy holds this repository's notes outside the markers. What the installer
# writes, and so what must equal `src/`, is the lines between the markers.
MARKED = {"CLAUDE.md", "AGENTS.md"}
BEGIN = b"<!-- trazo:begin -->\n"
END = b"<!-- trazo:end -->\n"
GIT = shutil.which("git")


def _installed_bytes(rel: str) -> bytes:
    """The bytes the installer would have written for `rel`: the marked block for the
    adapters, the whole file for everything else (still byte-exact)."""
    data = (REPO_ROOT / rel).read_bytes()
    if rel not in MARKED:
        return data
    assert data.count(BEGIN) == 1 and data.count(END) == 1, (
        f"{rel} must carry exactly one trazo:begin and one trazo:end marker line"
    )
    head, _, rest = data.partition(BEGIN)
    block, _, _tail = rest.partition(END)
    return block


def _pinned_tag() -> str | None:
    """Return the installed release tag once it exists in this checkout.

    Before the first release there is no `.trazo/VERSION`, so the source tree is the
    only available baseline. After installation, VERSION records the tag that owns the
    files in `.trazo/`; that immutable tag must remain the comparison baseline while
    `src/` moves ahead.
    """
    version_file = REPO_ROOT / ".trazo/VERSION"
    if not version_file.is_file():
        return None
    assert GIT, ".trazo/VERSION exists, but git is required to verify its pinned tag"

    version_lines = version_file.read_text(encoding="utf-8").splitlines()
    assert version_lines, ".trazo/VERSION is empty"
    tag = version_lines[0].strip()
    assert re.fullmatch(r"v\d+\.\d+\.\d+", tag), (
        f".trazo/VERSION must start with a release tag, got {tag!r}"
    )
    result = subprocess.run(  # noqa: S603 - fixed git argv; tag is constrained to semver
        [GIT, "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )
    return tag if result.returncode == 0 else None


def _source_bytes(rel: str, tag: str | None) -> bytes:
    """Read the canonical file from the pinned tag, or from the worktree pre-release."""
    if tag is None:
        return (REPO_ROOT / rel).read_bytes()
    assert GIT is not None
    result = subprocess.run(  # noqa: S603 - fixed git argv and repository-relative path
        [GIT, "show", "--no-ext-diff", "--no-textconv", f"{tag}:{rel}"],
        capture_output=True,
        cwd=REPO_ROOT,
        check=False,
    )
    assert result.returncode == 0, (
        f"could not read {rel} from pinned release {tag}: " + result.stderr.decode(errors="replace")
    )
    return result.stdout


def _tracked() -> list[Path]:
    """Every tracked path, without a subprocess.

    Walking the tree and filtering out `.git` and `.worktrees` is deliberate: shelling
    out to `git ls-files` is a subprocess (S603, a rule worth keeping) and this repo
    already carries a guard that every path reference resolves to a real file, so the
    test does not need an authoritative index -- it needs the set of files a reader could
    follow. That set *is* the working tree, minus the two directories that are not part
    of the project.
    """
    skip = {".git", ".worktrees", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache"}
    found = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if skip & set(path.relative_to(REPO_ROOT).parts):
            continue
        found.append(path)
    return found


def _text_files() -> list[Path]:
    return [p for p in _tracked() if p.suffix in TEXT_SUFFIXES and p.is_file()]


def test_the_overlay_layout_exists() -> None:
    """The layout from ADR 0010, asserted rather than assumed.

    `src/` is the canonical product. `.trazo/` is the installed copy that governs this
    repository, plus this repository's own state under `.trazo/project/` (ADR 0011).
    """
    for rel in (
        # The canonical product a host receives.
        "src/overlay/rules.md",
        "src/overlay/ADVISOR.md",
        "src/overlay/ARCHITECTURE.md",
        "src/overlay/templates/adr.md",
        "src/overlay/templates/workstream.md",
        "src/adapters/AGENTS.md",
        "src/adapters/CLAUDE.md",
        "src/adapters/claude/settings.json",
        # The installed copy that governs this repository.
        ".trazo/rules.md",
        ".trazo/ADVISOR.md",
        ".trazo/ARCHITECTURE.md",
        # This repository's own state.
        ".trazo/project/charter/charter.md",
    ):
        assert (REPO_ROOT / rel).exists(), f"{rel} is missing; the layout is incomplete"


def test_the_installed_copy_is_the_product_not_a_fork_of_it() -> None:
    """ADR 0010's reason for existing: one editable copy, never two that drift.

    The old layout let `.trazo/rules.md` be edited in place, so the rules an agent was
    given and the rules it was held to were the same mutable file. Under the new one an
    edit goes to `src/`, and the installed file is refreshed from it. A hand-edit of the
    installed copy (or an edit to `src/` that nobody installed) makes the two disagree,
    and this names which file.

    Before the first install, compare the working trees. Once `.trazo/VERSION` names an
    available release tag, compare the installed files with that tag's `src/` so that
    the product can move ahead while this repository remains pinned (ADR 0010).
    """
    tag = _pinned_tag()
    drifted = [
        f"{installed} != {source}"
        for installed, source in INSTALLED_FROM_SRC.items()
        if _installed_bytes(installed) != _source_bytes(source, tag)
    ]
    assert not drifted, (
        "the installed copy differs from its canonical source. Edit `src/`, then "
        "reinstall from the intended release; never edit `.trazo/` directly:\n" + "\n".join(drifted)
    )


def test_the_installed_overlay_is_pinned_to_an_available_release_tag() -> None:
    """After the first release, the self-installed overlay must keep its tag baseline."""
    assert _pinned_tag() is not None, (
        ".trazo/VERSION must name a release tag available in this checkout; "
        "falling back to the working tree would let src/ and the pinned install drift together"
    )


def test_claude_product_adapters_point_to_shared_trazo_content() -> None:
    """Tool-specific Claude files are discovery wrappers; shared role and workflow
    instructions live in the installable overlay and are also used by Codex."""
    for name in ("pm", "reviewer", "security", "skeptic"):
        text = (REPO_ROOT / ADAPTERS / "claude/agents" / f"{name}.md").read_text()
        target = ".trazo/ADVISOR.md" if name == "pm" else f".trazo/roles/{name}.md"
        assert target in text, name
    for name in ("start", "work", "check-pr", "brief", "decide", "kickoff", "trazo", "wrapup"):
        text = (REPO_ROOT / ADAPTERS / "claude/commands" / f"{name}.md").read_text()
        assert f".trazo/skills/{name}.md" in text, name
    for name in ("engineer", "pm", "reviewer", "security", "skeptic"):
        assert (REPO_ROOT / "src/overlay/roles" / f"{name}.md").is_file(), name
    for name in ("start", "work", "check-pr", "brief", "decide", "kickoff", "trazo", "wrapup"):
        assert (REPO_ROOT / "src/overlay/skills" / f"{name}.md").is_file(), name
    kickoff = (REPO_ROOT / "src/overlay/skills/kickoff.md").read_text().lower()
    assert "semilla" not in kickoff
    assert "templates/docs/" not in kickoff


def test_the_product_tree_holds_no_trazo_project_state() -> None:
    """`src/` is what ships. This repository's own charter, decision records and
    workstreams must never move into it.

    That is the whole point of the split (#77, #94): `handbook/guide.md` tells a host to
    copy the overlay, so anything of ours sitting in the product tree is inherited by
    every host. A host running `/kickoff` should not be handed our charter and stop rule.
    """
    forbidden = ("charter", "adr", "workstreams", "project", "STATUS", "PLAN")
    for path in (REPO_ROOT / PRODUCT).rglob("*"):
        if not path.is_file():
            continue
        parts = set(path.relative_to(REPO_ROOT).parts)
        assert not (parts & set(forbidden)), (
            f"{path.relative_to(REPO_ROOT)} is Trazo's own state, not product; "
            "a host would inherit it"
        )


def test_no_file_points_at_a_path_that_does_not_exist() -> None:
    """The issue's done-when. A dangling path is a doc that lies to the next session."""
    dangling: list[str] = []
    pattern = re.compile(r"\.trazo/[A-Za-z0-9_./-]+")
    for path in _text_files():
        if path.relative_to(REPO_ROOT).as_posix().startswith(HISTORY):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, ValueError):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for raw in pattern.findall(line):
                ref = raw.rstrip(".,;:)`\"'")
                if not ref or any(t in ref for t in TEMPLATE_TOKENS):
                    continue
                # A bare directory or a shorthand like `.trazo/adr/0003` is prose.
                if not (REPO_ROOT / ref).exists() and "." not in Path(ref).name:
                    continue
                product_ref = REPO_ROOT / "src/overlay" / ref.removeprefix(".trazo/")
                if not (REPO_ROOT / ref).exists() and not product_ref.exists():
                    dangling.append(f"{path.relative_to(REPO_ROOT)}:{lineno}: {ref}")

    assert not dangling, "paths that do not exist (issue #50 done-when):\n" + "\n".join(dangling)


def test_the_old_paths_are_gone() -> None:
    """A half-finished move leaves two copies and the next agent reads whichever it finds.

    Asserted as "no *files* remain" rather than "the directory does not exist": git does
    not track empty directories, so `git mv` leaves them behind in the working tree
    uncommitted and invisible to a fresh clone. A clone would never see the stale
    directory, but a session working in this tree would, and `ls docs/` showing
    `decisions/` that is not there is exactly the kind of thing that sends an agent
    looking for a file that moved.
    """
    for old in MOVED:
        root = REPO_ROOT / old
        stale = (
            [str(p.relative_to(REPO_ROOT)) for p in root.rglob("*") if p.is_file()]
            if (root.exists())
            else []
        )
        assert not stale, f"{old} still has files: {stale}"
        refs = [
            str(p.relative_to(REPO_ROOT))
            for p in _text_files()
            # This file names the old paths on purpose -- they are the assertion.
            if p.name != Path(__file__).name
            and old in p.read_text(encoding="utf-8", errors="ignore")
        ]
        assert not refs, f"{old} is still referenced by: {refs}"


def test_ours_is_in_project_and_the_hosts_is_a_template() -> None:
    """ADR 0011: the question is "ours or the host's", not "design or operational".

    Everything Trazo-authored about Trazo's own work lives in `.trazo/project/`, which is
    never shipped. What a host receives is a blank template under `src/overlay/templates/`.
    `docs/` holds nothing of ours, so a clone does not inherit a STATUS about our session.
    """
    for rel in OURS:
        assert (REPO_ROOT / PROJECT / rel).exists(), f"{PROJECT}/{rel} is missing"
    for rel in HOST_TEMPLATES:
        assert (REPO_ROOT / OVERLAY / "templates" / rel).exists(), f"template {rel} is missing"
    for old in (".trazo/charter", ".trazo/adr", ".trazo/workstreams"):
        stale = [p for p in (REPO_ROOT / old).rglob("*") if p.is_file()]
        assert not stale, f"{old} still has files; they moved to {PROJECT}/ (#97)"
    docs = REPO_ROOT / "docs"
    leftover = [str(p.relative_to(REPO_ROOT)) for p in docs.rglob("*") if p.is_file()]
    assert not leftover, f"docs/ holds Trazo-authored state: {leftover}"


def test_host_templates_are_blank() -> None:
    """A template that carries our own content is the #77 failure again, one level down."""
    for rel in ("charter.md", "docs/STATUS.md", "docs/PLAN.md", "docs/RUNBOOK.md"):
        text = (REPO_ROOT / OVERLAY / "templates" / rel).read_text(encoding="utf-8")
        assert "TODO" in text, f"{rel} should be a blank template"
        assert "semilla" not in text.lower(), f"{rel} carries this repository's own state"


def test_the_rules_file_is_the_tool_neutral_core() -> None:
    """The issue requires `.trazo/rules.md` to carry the mount-time contract, and
    requires that it does not mandate a tool for mounted repos."""
    rules = (REPO_ROOT / ".trazo" / "rules.md").read_text(encoding="utf-8")
    assert "one-command" in rules, "the mount-time environment contract is missing"
    assert re.search(r"hermetic", rules, re.IGNORECASE), "the contract must say hermetic"
    for tool in ("Docker", "nix", "devcontainer", "Makefile"):
        assert tool.lower() in rules.lower(), f"{tool} must be named as a valid option"
    assert re.search(r"do \*\*not\*\* mandate", rules, re.IGNORECASE), (
        "the contract must explicitly refuse to mandate a tool -- that is the mistake "
        "this pivot exists to fix"
    )


def test_claude_md_is_the_adapter_not_the_rules() -> None:
    """CLAUDE.md is a thin adapter; the rules live once, tool-neutral.

    The mechanical form of that -- the `@.trazo/rules.md` import, and the guards that keep
    it from silently failing open -- live in `test_adapter_import.py`.
    """
    claude = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    assert ".trazo/rules.md" in claude, "the adapter must point at the rules"
    assert "adapter" in claude.lower(), "CLAUDE.md must say what it now is"
    # The judgment layer must not be reduced to specs + ADRs (#0005).
    assert ".trazo/project/charter/" in claude, "the charter must stay visible from the adapter"
    assert ".trazo/project/adr/" in claude and ".trazo/project/workstreams/" in claude


def test_codeowners_still_protects_the_charter() -> None:
    """The charter is a judgment-layer path and was owner-protected under its old name.
    Moving the path without moving the rule would silently drop that protection -- the
    exact 'a path that matches no rule protects nothing' failure of issue #14."""
    codeowners = (REPO_ROOT / ".github" / "CODEOWNERS").read_text(encoding="utf-8")
    assert "docs/CHARTER.md" not in codeowners, "the old protected path is still listed"
    assert re.search(r"/\.trazo/project/charter/\s+@\S+", codeowners), (
        "the charter's new path is unprotected -- a moved path that matches no rule "
        "protects nothing (issue #14)"
    )


def test_the_docs_updated_ci_gate_followed_the_move() -> None:
    """ci.yml greps changed files for the architecture doc. ARCHITECTURE moved, so a
    stale pattern turns the gate into a no-op that still reports success."""
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert ".trazo/ARCHITECTURE.md" in ci, "the docs-updated gate does not watch the new path"
    assert ".trazo/project/RUNBOOK.md" in ci, "the docs-updated gate does not watch the runbook"
    assert "docs/RUNBOOK.md" not in ci, "the stale runbook path is still in ci.yml"
    assert not re.search(r"\^docs/\(ARCHITECTURE", ci), "the stale pattern is still there"
