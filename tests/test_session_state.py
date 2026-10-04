"""Guards the session STATUS and PLAN files against the stub they shipped as (#54).

The claim this repository makes is "the repo is the memory." `STATUS.md` is the file a
fresh session reads to learn where things stand, and `PLAN.md` is where the charter's
stop rule gets a date it can be checked against. Both shipped as stubs -- `YYYY-MM-DD`
and `TODO` -- through six merged PRs, and nothing failed: `mkdocs build`, `make test` and
`make lint` were all green the whole time, because a placeholder is not an error.

The counterargument on #54 is right -- a *stale* file is worse than a visibly unfilled
one -- and that is the argument for a guard rather than a one-off fill. These tests
cannot tell whether STATUS is accurate, only that it is not a stub any more: the date is
real, the author is named, and no `YYYY-MM-DD` placeholder can creep back into either
file. Accuracy is `/wrapup`'s job; this is the floor under it.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
STATUS = REPO_ROOT / ".trazo" / "project" / "STATUS.md"
PLAN = REPO_ROOT / ".trazo" / "project" / "PLAN.md"

PLACEHOLDER = re.compile(r"YYYY-MM-DD|\bTODO\b")
ISO_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_status_carries_a_real_date_and_author() -> None:
    """`/wrapup` step 1 replaces this file every session; the header is how a reader
    tells whether it was, and `YYYY-MM-DD by TODO` is the shipped stub."""
    line = next(
        (ln for ln in _text(STATUS).splitlines() if ln.startswith("**Updated:**")),
        "",
    )
    assert line, "STATUS.md has no `**Updated:**` header line"
    assert ISO_DATE.search(line), f"the Updated line has no real date: {line!r}"
    assert "TODO" not in line, f"the Updated line still names a placeholder author: {line!r}"
    assert line.split(" by ", 1)[-1].strip(), "the Updated line names no author"


def test_neither_file_carries_a_placeholder() -> None:
    """The stub both files shipped with. A placeholder reads as 'not yet decided',
    which is a decision nobody made."""
    for path in (STATUS, PLAN):
        hit = PLACEHOLDER.search(_text(path))
        assert hit is None, f"{path.name} carries the placeholder {hit.group(0)!r} (#54)"


def test_every_milestone_has_a_target_date() -> None:
    """`M1 | | |` is a row that cannot be planned against, and M2 is the row the
    charter's stop rule fires on -- #27 has nothing to watch without it."""
    rows = [
        ln
        for ln in _text(PLAN).splitlines()
        if re.match(r"^\|\s*M\d", ln) and not ln.startswith("|---")
    ]
    assert len(rows) >= 2, f"expected the milestone rows in PLAN.md, found {len(rows)}"
    for row in rows:
        cells = [c.strip() for c in row.strip("|").split("|")]
        assert len(cells) == 4, f"milestone row is not name/date/exit/status: {row!r}"
        assert ISO_DATE.search(cells[1]), f"milestone {cells[0]!r} has no real target date: {row!r}"
        assert cells[3], f"milestone {cells[0]!r} has no status: {row!r}"
