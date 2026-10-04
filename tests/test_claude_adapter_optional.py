"""The mount instructions must not require `.claude/` (ADR 0007).

ADR 0005 defined the product as "`.trazo/` plus `.claude/`", which contradicts its own
mount-time contract two lines later — *"Do **not** mandate a particular tool for a
mounted repo."* Naming `.claude/` as part of the overlay **is** mandating one.

The error propagated instead of being invented twice: `handbook/index.md` and
`handbook/guide.md` both told people to copy "`.trazo/` and `.claude/`". A Cline or
Cursor user reading that either installs files they do not need, or concludes Trazo
does not support their tool. ADR 0007 supersedes the clause; these tests keep the
corrected instructions from decaying back.

Prose is exactly the kind of thing that drifts, so the claim is pinned mechanically.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

MOUNT_DOCS = ("handbook/index.md", "handbook/guide.md", "README.md")

# A sentence that names `.claude/` as part of what you copy, or alongside `.trazo/` as
# though both were required. The scoping words matter: "copy `.trazo/` and `.claude/`" and
# "a mounted repo takes `.trazo/` and `.claude/`" are the bug, while "copy `.trazo/` in,
# then add the adapter ... `.claude/` if you use Claude Code" is the corrected form and
# must not be flagged. So the pattern looks for `.claude/` sitting next to `.trazo/` with
# no adapter framing between them.
UNIVERSAL_CLAIM = re.compile(
    r"(?:copy|add|install|takes?|bring)[^.\n]{0,60}\.claude/"
    r"|\.trazo/`?\s*(?:and|plus|,)\s*`?\.claude/"
    r"|both\s+`?\.trazo/`?\s+and\s+`?\.claude/",
    re.IGNORECASE,
)

# Words that make a `.claude/` mention explicitly conditional, i.e. the corrected form.
SCOPED = re.compile(
    r"if you use claude code|if that is claude code|which is claude code"
    r"|adapter for (?:your|the) agent|for whichever agent|your own equivalent",
    re.IGNORECASE,
)


def _mount_docs() -> list[tuple[str, str]]:
    return [
        (rel, (REPO_ROOT / rel).read_text(encoding="utf-8"))
        for rel in MOUNT_DOCS
        if (REPO_ROOT / rel).is_file()
    ]


def test_mount_docs_do_not_require_claude():
    """The regression this ADR exists to stop."""
    offenders = [
        f"{rel}: {line.strip()[:90]}"
        for rel, text in _mount_docs()
        for line in text.splitlines()
        if UNIVERSAL_CLAIM.search(line) and not SCOPED.search(line)
    ]
    assert not offenders, (
        "the mount instructions require `.claude/` again. `.claude/` is the Claude Code "
        "adapter, not part of the overlay (ADR 0007). Copy `.trazo/` and add the adapter "
        "for whichever agent you use:\n" + "\n".join(offenders)
    )


def test_mount_instructions_still_offer_the_claude_adapter():
    """Correcting the claim must not delete the adapter people actually need.

    A mount page that only says "add your own adapter" leaves a Claude Code user
    guessing where the commands come from. Both halves have to be present.
    """
    for rel, text in _mount_docs():
        lowered = text.lower()
        if "copy the overlay" in lowered or "repo you already have" in lowered:
            assert ".claude/" in text, (
                f"{rel} tells people how to mount but never mentions the Claude adapter"
            )
            assert re.search(r"if you use claude code|if that is claude code", lowered), (
                f"{rel} must scope `.claude/` to Claude Code, not imply it is the only option"
            )


def test_the_merge_dont_overwrite_rule_is_stated():
    """A host with an existing adapter must be told to merge, not replace.

    Overwriting someone's `.claude/` or `CLAUDE.md` silently deletes their commands and
    permissions. This is the one mount instruction with a way to destroy work.
    """
    found = False
    for _, text in _mount_docs():
        if re.search(r"merge|already has", text, re.IGNORECASE) and re.search(
            r"\.claude/|CLAUDE\.md", text
        ):
            found = True
    assert found, (
        "no mount page says what to do when the host already has an adapter. It must say "
        "to merge rather than overwrite (ADR 0007)."
    )


def test_adr_0007_supersedes_the_wrong_clause():
    """The superseding record exists and names what it replaces.

    ADRs are append-only (#0000), so 0005 keeps its wrong clause forever. The only thing
    that can correct a reader is a later record that says so explicitly.
    """
    adr = REPO_ROOT / ".trazo" / "project" / "adr" / "0007-claude-is-an-adapter.md"
    assert adr.is_file(), "ADR 0007 is missing; nothing supersedes 0005's wrong clause"
    text = adr.read_text(encoding="utf-8")
    assert re.search(r"supersede", text, re.IGNORECASE), (
        "ADR 0007 must state that it supersedes 0005's '.trazo/ plus .claude/' clause"
    )
    assert "0005" in text, "ADR 0007 must reference the record it supersedes"
    assert "AGENTS.md" in text, (
        "ADR 0007 must record that AGENTS.md (codebase context) is a different thing from "
        "Trazo (governance); they are not alternatives"
    )


def test_the_trazo_tree_itself_names_no_tool():
    """The claim rests on this: `.trazo/rules.md` is the tool-neutral half.

    Checked over live files rather than history, and only over `rules.md`, which is the
    one file every mounted repo reads and every tool's adapter loads. ADRs, workstreams
    and the charter are records about *this* repository — the charter's budget line names
    the tool Trazo itself runs on, which is a fact about Trazo's owner, not a rule handed
    to a mounted repo. Asserting those files are tool-free would be asserting a falsehood.
    """
    text = (REPO_ROOT / ".trazo" / "rules.md").read_text(encoding="utf-8")
    offenders = [
        f".trazo/rules.md:{i}: {line.strip()[:70]}"
        for i, line in enumerate(text.splitlines(), 1)
        if re.search(r"Claude Code|\.claude/", line)
    ]
    assert not offenders, (
        "the tool-neutral core names a specific tool, so it is no longer tool-neutral:\n"
        + "\n".join(offenders)
    )
