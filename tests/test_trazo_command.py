"""Guards the /trazo menu command (issue #72).

The command was renamed from /semilla when the repo became Trazo. Unlike the repo slug --
which is a URL and can be updated everywhere at once -- a slash command is a user-facing
API. Someone who typed `/semilla` yesterday gets command-not-found today, and nothing in
the build says so: the command simply stops existing, and the docs that mention it go on
describing it.

Two things are asserted:

1. **The command file exists under the new name and no longer under the old one.** A
   half-finished rename leaves both, and two commands with different content is worse than
   either.
2. **No live file advertises the old command name.** Every surface that taught a user to
   type `/semilla` has to change in the same change, or the docs teach a command that does
   not exist.

`<owner>/semilla` in `gh repo create --template ...` lines is deliberately exempt: that is
a *derived project's* suggested name and a placeholder in the docs, not the menu command.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
COMMANDS = REPO_ROOT / ".claude" / "commands"

# Records that must keep the old name because it was true when written.
HISTORICAL = (".template/CHANGELOG.md", ".template/LESSONS.md", ".trazo/project/adr/", "tests/")

TEXT_SUFFIXES = {".md", ".py", ".toml", ".yml", ".yaml", ".json", ".sh", ".cfg", ".txt"}

# The old command form, spelled out rather than interpolated so this file can assert on
# it without tripping its own scan.
OLD_COMMAND = "/" + "semilla"
NEW_COMMAND = "/" + "trazo"


def _text_files() -> list[Path]:
    skip = {".git", ".worktrees", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache"}
    out = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        rel = path.relative_to(REPO_ROOT)
        if skip & set(rel.parts):
            continue
        if rel.name == Path(__file__).name:  # this file names the old command to assert on it
            continue
        out.append(path)
    return out


def test_the_menu_command_is_named_after_the_project() -> None:
    assert (COMMANDS / "trazo.md").exists(), ".claude/commands/trazo.md is missing"
    assert not (COMMANDS / "semilla.md").exists(), (
        "both command files exist; the rename was only half done and two commands with "
        "different content is worse than either"
    )


def test_the_command_has_a_frontmatter_description() -> None:
    """Without a description it will not appear in the slash-command menu, which is the
    only way anyone discovers it -- so the rename would leave the command unreachable."""
    text = (COMMANDS / "trazo.md").read_text(encoding="utf-8")
    assert text.startswith("---\n"), "no frontmatter, so the command is not discoverable"
    front = text[4 : text.index("\n---\n", 3)]
    assert re.search(r"^description:\s*\S", front, re.MULTILINE), "no description"


def test_no_live_file_advertises_the_old_command() -> None:
    offenders = []
    for path in _text_files():
        rel = str(path.relative_to(REPO_ROOT))
        if rel.startswith(HISTORICAL):
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            # Anchored on a backtick or quote so `owner/semilla` is not matched: that is a
            # derived project's suggested name, not this command.
            if re.search(rf"[`\"']{re.escape(OLD_COMMAND)}[`\"']", line):
                offenders.append(f"{rel}:{lineno}: {line.strip()[:70]}")
    assert not offenders, (
        f"these still teach `{OLD_COMMAND}`, which no longer exists. Every surface that "
        "taught the old command has to change in the same change:\n" + "\n".join(offenders)
    )


def test_the_plain_english_route_points_at_the_new_command() -> None:
    """`CLAUDE.md`'s route table is what a session reads first, so it is the single
    highest-value reference to update."""
    claude = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    route = [ln for ln in claude.splitlines() if NEW_COMMAND in ln and "menu" in ln]
    assert route, f"CLAUDE.md does not route 'menu' requests to `{NEW_COMMAND}`"


def test_the_handbook_documents_the_new_command() -> None:
    """The handbook is the published docs; a command that exists but is undocumented is
    effectively private."""
    for rel in ("handbook/guide.md", "handbook/team.md"):
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        assert NEW_COMMAND in text, f"{rel} does not mention {NEW_COMMAND}"
