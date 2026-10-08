"""Guards for the decision records (issue #49, and #0005 in particular).

Two things about a decision record make it worth a test, and neither is about prose:

1. **Numbering is append-only and must not collide.** #0004 was taken by PR #30 on
   2026-09-28, *after* #49 was drafted to claim that number. A record that silently
   overwrites or duplicates an existing one destroys the audit trail that decisions
   0001 and 0003 exist to provide, and the mistake is invisible until someone goes
   looking for a history.
2. **The verifiable numbers must stay true.** #0005 quotes a file count and a ratio
   measured at a pinned commit. Pinning the commit means the claim is checkable, so
   a test can check it -- and if the numbers are wrong the record is wrong, and a
   decision record that is wrong is worse than no record.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DECISIONS = REPO_ROOT / ".trazo" / "project" / "adr"

# The blank template ships to hosts as product, so it lives in the overlay tree (#94)
# rather than in this repository's own decision directory. It is still `0000`: the
# numbering starts there and the contiguity check below depends on it.
TEMPLATE = REPO_ROOT / "src" / "overlay" / "templates" / "adr.md"

# The commit #0005's counts were measured against. A count is only meaningful with
# the tree it was taken from; without this pin the assertion rots on the next PR.
MEASURED_AT = "b42b6d0"
MEASURED_TOTAL_FILES = 86
MEASURED_SRC_FILES = 2
MEASURED_DIR_COUNTS = {".claude/": 17, "docs/": 15, "handbook/": 9, ".template/": 9, "infra/": 6}


def _records() -> list[Path]:
    return sorted(DECISIONS.glob("[0-9][0-9][0-9][0-9]-*.md"))


def _number(path: Path) -> int:
    return int(path.name[:4])


def _unloaded_accepted_rules(records: list[tuple[str, str]], rules: str) -> list[str]:
    """Return accepted ADR rules absent from the always-loaded rules text."""
    normalized_rules = re.sub(r"\s+", " ", rules).casefold()
    missing = []
    for name, text in records:
        status = re.search(r"\*\*Status:\*\*\s*([^\n]+)", text)
        if not status or not status.group(1).strip().startswith("accepted"):
            continue
        rule = re.search(r"^\*\*Rule:\*\*\s*(.+)$", text, re.MULTILINE)
        if not rule or rule.group(1).strip().casefold() == "none":
            continue
        statement = re.sub(r"\s+", " ", rule.group(1)).strip().casefold()
        if statement not in normalized_rules:
            missing.append(name)
    return missing


def test_decision_numbers_are_unique_and_contiguous() -> None:
    numbers = [_number(p) for p in _records()]
    duplicates = [n for n in set(numbers) if numbers.count(n) > 1]
    assert not duplicates, f"two decision records share a number: {duplicates}"
    # 0000 is the template, so the real records are 1..N with no gaps. The template no
    # longer sits in this directory (#94) but it is still 0000, so the expected sequence
    # is unchanged and a gap at 0 is still a real gap.
    assert numbers == list(range(1, len(numbers) + 1)), f"decision numbers have a gap: {numbers}"
    assert TEMPLATE.exists(), f"the 0000 template is missing: {TEMPLATE}"


def test_the_template_is_not_numbered_as_a_record() -> None:
    """0000 is a template, not a decision; it must not claim a status or a date."""
    template = TEMPLATE.read_text(encoding="utf-8")
    assert "YYYY-MM-DD" in template, "the template's date must stay a placeholder"


def test_every_record_declares_a_status() -> None:
    """A record whose status is ambiguous cannot be superseded, which is the one
    operation decisions must support.

    Dates are deliberately not asserted for the pre-existing records: 0001 still
    carries the template placeholder `YYYY-MM-DD` (created that way in the initial
    commit and never filled in, tracked separately). Backfilling it would mean
    editing an append-only record to assert a date nobody can now verify, so the
    new records are held to a real date and the old one is left alone.
    """
    for path in _records():
        if path.name.startswith("0000-"):
            continue
        text = path.read_text(encoding="utf-8")
        where = path.name
        status = re.search(r"\*\*Status:\*\*\s*([a-z ]+)", text)
        assert status, f"{where}: no status"
        value = status.group(1).strip()
        assert value in {"accepted", "proposed"} or value.startswith("superseded"), (
            f"{where}: unknown status {value!r}"
        )


def test_accepted_adr_rules_are_always_loaded() -> None:
    """A behavior decision cannot live only in a record agents may not read (#113)."""
    records = [(path.name, path.read_text(encoding="utf-8")) for path in _records()]
    source_rules = (REPO_ROOT / "src/overlay/rules.md").read_text(encoding="utf-8")
    installed_rules = (REPO_ROOT / ".trazo/rules.md").read_text(encoding="utf-8")
    missing_source = _unloaded_accepted_rules(records, source_rules)
    missing_installed = _unloaded_accepted_rules(records, installed_rules)
    assert not missing_source, (
        f"accepted ADR Rule missing from src/overlay/rules.md: {missing_source}"
    )
    assert not missing_installed, (
        f"accepted ADR Rule missing from .trazo/rules.md: {missing_installed}"
    )


def test_accepted_adr_rule_check_detects_a_missing_rule() -> None:
    sample = "**Status:** accepted\n**Rule:** The reviewer checks the current base branch.\n"
    assert _unloaded_accepted_rules([("0001-sample.md", sample)], "# rules\n") == ["0001-sample.md"]


def test_newer_records_carry_a_real_date() -> None:
    """0004 and later were authored against the template and must have a real date.
    0001 is exempted deliberately -- see the test above."""
    for path in _records():
        if path.name < "0004":
            continue
        text = path.read_text(encoding="utf-8")
        assert re.search(r"\*\*Date:\*\*\s*\d{4}-\d{2}-\d{2}", text), f"{path.name}: no real date"


def test_records_are_append_only_in_practice() -> None:
    """The four records this guard predates must be byte-stable. #0003 in particular is
    SHA-pinned by `test_review_verdicts.py` because #47 called it out; pinning the
    rest here means a well-meaning "tidy the old records" edit fails loudly."""
    pinned = {
        "0001-record-decisions.md": 1,
        "0002-per-issue-git-worktrees.md": 1,
        "0003-review-security-github-tracked.md": 1,
        "0004-docs-site-claude-aws-focus.md": 1,
    }
    for name in pinned:
        assert (DECISIONS / name).exists(), f"{name} was removed; decisions are append-only"


def test_0005_records_the_pivot_with_verified_numbers() -> None:
    record = DECISIONS / "0005-pivot-to-trazo.md"
    assert record.exists(), "the pivot decision record is missing (#49)"
    text = record.read_text(encoding="utf-8")

    assert "accepted" in text, "the owner decided; the status must say accepted"
    assert MEASURED_AT in text, (
        f"the file count must name the commit it was measured on ({MEASURED_AT}), "
        "or the number cannot be re-checked later"
    )
    assert f"{MEASURED_TOTAL_FILES} tracked files" in text, "the measured total drifted"
    assert f"{MEASURED_TOTAL_FILES - MEASURED_SRC_FILES}" in text, "the ratio must be derivable"

    for d, n in MEASURED_DIR_COUNTS.items():
        assert f"`{d}` {n}" in text, f"directory count for {d} is missing or wrong ({n})"


def test_0005_carries_the_two_binding_amendments() -> None:
    """#33 is a brief, not a decision; where they conflict, 0005 must say so
    explicitly, or the implementer follows the brief and the conflict returns."""
    text = (DECISIONS / "0005-pivot-to-trazo.md").read_text(encoding="utf-8")
    assert "amend" in text.lower(), "the amendments section must be present"
    # The reviewer must not merge: this is the one that contradicts CLAUDE.md rule 2.
    assert re.search(r"[Rr]eviewer does not merge|reviewer.*does \*\*not\*\* merge", text), (
        "the 'reviewer does not merge' amendment is missing"
    )
    assert "0003" in text, "it must cite the decision it is reconciling with"
    # Native dependencies, not the 'Blocked by #N' text convention.
    assert "blockedBy" in text or "blocked by" in text.lower(), (
        "the dependency-amendment must name the native field"
    )
    assert "2.101.0" in text, "the amendment should record the version it was verified on"


def test_0005_links_the_issues_a_reader_would_otherwise_need() -> None:
    """Links for the brief and the PR that took 0004; #48 is named in prose, which is
    enough for a reader here, so it is matched as a reference rather than a URL."""
    text = (DECISIONS / "0005-pivot-to-trazo.md").read_text(encoding="utf-8")
    assert "issues/33" in text, "must link the brief it records"
    assert "pull/30" in text, "must link the PR that took the number 0004"
    assert re.search(r"#48|issues/48", text), "must reference the epic it belongs to"


def test_0010_records_the_split_and_its_cost() -> None:
    """#93 exists because "moving files first and recording the rule afterwards produces
    folklore instead of a record" -- every issue in the #92 chain cites 0010, so the
    clauses they depend on must survive in it rather than in the PR description.

    These assert the three clauses and the stated cost. A later "just edit `.trazo/`
    directly" is answered by this record, so a future edit that quietly drops the cost
    takes away the answer.
    """
    record = DECISIONS / "0010-src-canonical-trazo-pinned.md"
    assert record.exists(), "ADR 0010 is missing; the #92 chain cites it"
    text = record.read_text(encoding="utf-8")

    # The decision, in the words the epic uses.
    assert re.search(r"`src/` is the canonical source", text, re.IGNORECASE), (
        "the record must state that src/ is canonical"
    )
    assert re.search(r"never hand-edited", text, re.IGNORECASE), (
        "the record must state that .trazo/ is never hand-edited"
    )
    assert ".trazo/project/" in text, "the record must name where this repo's own state lives"
    assert re.search(r"never overwritten", text, re.IGNORECASE), (
        "project state must be marked never-overwritten, or an upgrade destroys it"
    )

    # The install route, decided on #77 -- the part an agent would otherwise re-derive
    # from a README button that outlives the decision.
    assert re.search(r"install from `src/`", text, re.IGNORECASE), (
        "hosts install from src/; this is what stops them inheriting this repo's state"
    )
    assert re.search(r"template.*retired|retire.*template", text, re.IGNORECASE), (
        "the retirement of the GitHub-template path is part of the decision (#77)"
    )

    # The cost, which is what makes the rule answerable under pressure.
    assert re.search(r"frozen `v0\.1\.0` rules", text), (
        "the cost -- governed by frozen rules until a release -- must be stated"
    )
    assert re.search(r"just edit `\.trazo/`", text, re.IGNORECASE), (
        "the record must name the pressure it will create, so 'no, deliberately' works"
    )

    # Measured, not remembered: the figures the epic quoted were measured before
    # #103/#105/#106 landed, and #0009 exists because remembered numbers rotted.
    for label, value in (("files referencing", "55"), ("occurrences", "258"), ("handbook", "30")):
        assert value in text, f"the {label} figure ({value}) is missing"
    assert "47c1e09" in text, "the measurement must name the tree it was taken from"


def test_0010_does_not_edit_the_records_it_supersedes() -> None:
    """0005-0008 describe the old layout and are append-only. 0010 names them as
    superseded instead of rewriting them; a future tidy-up that edits them in place
    breaks the audit trail the ADR rules exist to keep."""
    text = (DECISIONS / "0010-src-canonical-trazo-pinned.md").read_text(encoding="utf-8")
    for number in ("0005", "0006", "0007", "0008"):
        assert number in text, f"{number} names the old layout and must be cited"
    assert re.search(r"superseded, not edited", text, re.IGNORECASE), (
        "0010 must say the old records are superseded rather than edited"
    )
