"""Guards for the work-queue report in `.claude/commands/start.md` (issue #37).

`/start` used to summarize state and leave the queue implicit, so the owner still had
to read the issue list and work out who was waiting on whom -- the relay problem #35
exists to remove. The report now has four groups in a fixed order.

The file is prose an agent follows, so nothing but a test stops it drifting back to a
vague summary, or to a `--json` field list that `gh` refuses. These checks assert the
load-bearing structure, not the wording.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
START = REPO_ROOT / ".claude" / "commands" / "start.md"

# The four groups, in the order the report must present them.
GROUPS = ("Waiting on you", "Blocked on the PM", "Ready to work", "Epics in flight")

# Every field `gh issue list --json` accepts, from the CLI's own "Available fields"
# output (gh 2.101.0). A snapshot on purpose: its job is to reject a field the CLI
# does not know -- notably `issueDependenciesSummary`, the GraphQL name from #37's
# text, which makes the whole command fail rather than degrade.
GH_ISSUE_FIELDS = frozenset(
    """
    assignees author blockedBy blocking body closed closedAt
    closedByPullRequestsReferences comments createdAt id isPinned issueType labels
    milestone number parent projectCards projectItems reactionGroups state stateReason
    subIssues subIssuesSummary title updatedAt url
    """.split()
)

# What the four groups need in order to be computable without parsing body text.
REQUIRED_FIELDS = ("number", "title", "labels", "blockedBy", "parent", "subIssuesSummary")


def _text() -> str:
    return START.read_text(encoding="utf-8")


def _line_with(marker: str) -> str:
    """The one line carrying `marker`, so a clause cannot satisfy a test from the wrong
    group -- `P0` appearing somewhere in the file says nothing about the ready group."""
    lines = [line for line in _text().splitlines() if marker in line]
    assert len(lines) == 1, f"expected exactly one {marker!r} line, found {len(lines)}"
    return lines[0]


def _requested_fields() -> list[str]:
    match = re.search(r"gh issue list[^\n]*?--json\s+([A-Za-z0-9,]+)", _text())
    assert match, "start.md has no `gh issue list ... --json <fields>` command"
    return match.group(1).split(",")


def test_the_four_groups_are_reported_in_order() -> None:
    positions = [_text().find(group) for group in GROUPS]
    missing = [group for group, at in zip(GROUPS, positions, strict=True) if at == -1]
    assert not missing, f"groups missing from start.md: {missing}"
    assert positions == sorted(positions), f"groups are out of order: {positions}"


def test_ready_to_work_excludes_open_blockers() -> None:
    ready = _line_with("Ready to work")
    assert "blockedBy" in ready, "the ready group must key off blockedBy"
    assert "OPEN" in ready, "only *open* blockers exclude; a closed blocker must not"


def test_ready_to_work_is_ordered_by_priority() -> None:
    ready = _line_with("Ready to work")
    order = [ready.find(label) for label in ("P0", "P1", "P2")]
    assert all(at != -1 for at in order), f"missing a priority label in: {ready}"
    assert order == sorted(order), "priority labels are not in P0 -> P1 -> P2 order"


def test_epics_report_sub_issue_progress() -> None:
    epics = _line_with("Epics in flight")
    assert "epic" in epics
    assert "subIssuesSummary" in epics and "completed" in epics and "total" in epics


def test_the_queue_command_uses_json_fields_gh_accepts() -> None:
    fields = _requested_fields()
    missing = [field for field in REQUIRED_FIELDS if field not in fields]
    assert not missing, f"the queue command does not request {missing}"
    unknown = [field for field in fields if field not in GH_ISSUE_FIELDS]
    assert not unknown, (
        f"{unknown} is not a `gh issue list --json` field (gh 2.101.0). "
        "`issueDependenciesSummary` is the GraphQL name; the CLI field is `blockedBy`."
    )


def test_start_still_waits_for_the_owners_ok() -> None:
    assert re.search(r"[Ww]ait for my OK", _text()), "the human gate was dropped"


def test_start_flags_a_stale_status_instead_of_reading_it_as_current() -> None:
    """#109, from the #54 root cause: `/wrapup` has told every session to rewrite
    `.trazo/project/STATUS.md` since this repository's first commit (`git log -S 'Rewrite
    .trazo/project/STATUS.md'` -> `7eaf827`), yet STATUS went stale. That was cause (b) --
    sessions end at merge without running `/wrapup`, and nothing made the omission
    visible.

    `/start` already *reads* STATUS in step 2, so this is not about making a session
    look at a file it skips. A stale file reads exactly like a fresh one, so the
    session has to be told to check the date and say so when it is old. Pinned here
    because `start.md` is prose an agent follows -- only a test keeps prose honest,
    and a tidy rewrite of `/start` would otherwise drop the clause as redundant.
    """
    step = re.search(r"^2\..*?(?=\n3\.)", _text(), re.S | re.MULTILINE)
    assert step, "start.md no longer has the step that reads .trazo/project/STATUS.md"
    body = step.group(0)

    assert ".trazo/project/STATUS.md" in body, "step 2 must still read STATUS"
    assert "**Updated:**" in body, (
        "step 2 must tell the session to check STATUS's `**Updated:**` date; without "
        "it a stale STATUS reads exactly like a current one (#54 cause (b))"
    )
    assert re.search(r"old|stale|outdated|contradicts|does not match", body, re.IGNORECASE), (
        "step 2 must say what to do when STATUS is stale -- flag it in one line rather "
        "than reporting it as current"
    )
    assert re.search(r"#54|#109", body), (
        "cite the issue, or the clause reads as filler and the next rewrite drops it"
    )
