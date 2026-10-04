"""Guards for how subagent review verdicts reach a pull request (issue #47).

Six files told subagents to post verdicts with `gh pr review --approve` or
`--request-changes`. GitHub refuses both when the reviewer and the PR author are the
same account, and every PR in this repository is self-authored (#44), so the
instruction could not be run. The failed command is not the damage; the recovery is:
an agent that cannot follow the instruction improvises, and the verdict ends up in
chat only -- the exact outcome `.trazo/project/adr/0003` exists to prevent. So the fix
prescribes `gh pr review --comment` *and* names the reason, and these tests hold both
halves in place.

Cross-file on purpose: the #36 review established that a test guarding one file
passes happily while another contradicts it.

Scope is the *operative* files -- the ones an agent executes: `.claude/agents/*.md`,
`.claude/commands/*.md`, and `CLAUDE.md`. Descriptive prose is deliberately out:
`handbook/playbook.md` (rewritten by #33/#40) and `.trazo/project/STATUS.md` (session status,
replaced by `/wrapup`) may describe the old mechanism, but they instruct nothing.
"""

import hashlib
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
CLAUDE_DIR = REPO_ROOT / ".claude"

# The five files issue #47 names, each of which prescribes the mechanism.
PRESCRIBING_FILES = (
    CLAUDE_DIR / "agents" / "reviewer.md",
    CLAUDE_DIR / "agents" / "security.md",
    CLAUDE_DIR / "commands" / "check-pr.md",
    CLAUDE_DIR / "commands" / "work.md",
    CLAUDE_MD,
)

# `.trazo/project/adr/0003` is append-only: the record #44 produces supersedes it by name,
# it is never edited. Pinning the digest is the only thing that stops a well-meaning
# "update the bullet" edit -- the risk #47 calls out by name.
DECISION_0003 = REPO_ROOT / ".trazo" / "project" / "adr" / "0003-review-security-github-tracked.md"
DECISION_0003_SHA256 = "5377a667839937ae1346c4ff873d13b9008e8844a6af39f30d4731f95dae2524"

# The prescribing forms, however they are spelled: the flag attached to the command
# (`gh pr review --approve`) or the bare parenthetical two of the files used instead
# of flags (`(approve / request-changes)`). A grep for `--approve` alone misses the
# second, which is how a flag-only search under-counts the files that need fixing.
PRESCRIBED_APPROVAL = re.compile(
    r"gh pr review\s+--(?:approve|request-changes)|\(\s*approve\s*/\s*request-changes\s*\)"
)


def _operative_files() -> list[Path]:
    """Agent definitions, role commands, and the root rules -- what an agent executes."""
    return (
        sorted(CLAUDE_DIR.glob("agents/*.md"))
        + sorted(CLAUDE_DIR.glob("commands/*.md"))
        + [CLAUDE_MD]
    )


def test_no_operative_file_prescribes_approving_or_requesting_changes() -> None:
    offenders = []
    for path in _operative_files():
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            match = PRESCRIBED_APPROVAL.search(line)
            if match:
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{lineno}: {match.group(0)!r}")
    assert not offenders, (
        "GitHub refuses --approve/--request-changes while the agent and the PR author "
        "share one account, i.e. every PR here (#44). Prescribe `gh pr review --comment` "
        "with the verdict word on the first line instead:\n" + "\n".join(offenders)
    )


def test_each_prescribing_file_uses_comment_and_names_the_reason() -> None:
    """`--comment` alone is not enough: without the reason, the next agent reverts it."""
    for path in PRESCRIBING_FILES:
        text = path.read_text(encoding="utf-8")
        where = path.relative_to(REPO_ROOT)
        assert "gh pr review --comment" in text, f"{where}: not prescribed via --comment"
        assert any(
            "gh pr review --comment" in line
            and "--approve" in line
            and ("#44" in line or "refused" in line)
            for line in text.splitlines()
        ), f"{where}: the mechanism line must also say why (#44: GitHub refuses it)"


def test_decision_0003_is_byte_identical() -> None:
    """Append-only (#47): supersede with a new record, never edit this file."""
    digest = hashlib.sha256(DECISION_0003.read_bytes()).hexdigest()
    assert digest == DECISION_0003_SHA256, (
        ".trazo/project/adr/0003-*.md changed -- it is append-only. Supersede it with a new "
        "record (see #44) and update this pin only if the owner decides otherwise."
    )
