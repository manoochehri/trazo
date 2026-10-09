"""Guards so a merged pull request actually closes the issue it claims (#61).

Three consecutive PRs (#56, #59, #60) carried `Closes #N` as the first line of the
body, were squash-merged into `main`, and left their issues open. The work queue (#37)
then reported finished work as ready.

The mechanism, verified against this repo's own history rather than assumed:

- All three merge commits are **single-parent** (`16f8a6f0`, `8a29026`, `c054c45`), i.e.
  squash merges, not merge commits.
- Their commit messages contain **no closing keyword** -- the squash kept the PR title,
  which had none.
- PR #60's body *did* parse: `gh pr view 60 --json closingIssuesReferences` returns
  `[#36, #37]`. The link existed and the issue still stayed open.

So the PR body alone is not enough: GitHub resolves the close from the commits that
land on the default branch. The fix therefore puts the keyword in the commit message
(`work.md` step 4) and adds a verification step to `/wrapup`, which is the only place
that observes the post-merge state.

The assertions below guard the *rule*, not the symptom. Asserting "the issue closed"
would be untestable in CI (it needs a merge), and asserting the symptom we saw
(`closingIssuesReferences`) would have stayed green while the bug was live.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORK = REPO_ROOT / "src" / "overlay" / "skills" / "work.md"
WRAPUP = REPO_ROOT / "src" / "overlay" / "skills" / "wrapup.md"
REVIEWER = REPO_ROOT / "src" / "overlay" / "roles" / "reviewer.md"
CLAUDE_MD = REPO_ROOT / "src" / "adapters" / "CLAUDE.md"
PR_TEMPLATE = REPO_ROOT / ".github" / "pull_request_template.md"

CLOSING_KEYWORD = re.compile(
    r"(?i)^(close[sd]?|fix(e[sd])?|resolve[sd]?)\s+#\d+",
    re.MULTILINE,
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _numbered_step(text: str, marker: str) -> str:
    """The full numbered step carrying `marker`, including its indented continuation
    lines. A rule whose evidence or command sits on a wrapped line is still one step,
    and asserting only the first line would test the prose rather than the rule --
    so a rule quoted in an aside still cannot satisfy a test meant for the
    operative step."""
    lines = text.splitlines()
    hits = [i for i, ln in enumerate(lines) if marker in ln and re.match(r"^\d+\.", ln)]
    assert len(hits) == 1, f"expected exactly one numbered step with {marker!r}, got {len(hits)}"
    start = hits[0]
    block = [lines[start]]
    for ln in lines[start + 1 :]:
        # A continuation is indented; the next step or a heading ends the block.
        if re.match(r"^\d+\.\s", ln) or ln.startswith("#"):
            break
        if ln.startswith((" ", "\t")):
            block.append(ln)
            continue
        break
    return "\n".join(block)


def test_wrapup_steps_stay_sequential() -> None:
    """A renumbered step that orphans the following ones silently disables them."""
    numbers = [int(n) for n in re.findall(r"^(\d+)\.", _text(WRAPUP), re.MULTILINE)]
    assert numbers == list(range(1, len(numbers) + 1)), f"steps are not sequential: {numbers}"


def test_work_md_puts_the_keyword_in_the_commit_message() -> None:
    """The fix itself. A PR-body-only keyword is what caused #61."""
    step = _numbered_step(_text(WORK), "closes the issue")
    assert re.search(r"commit message", step, re.IGNORECASE), (
        "step 4 must say the keyword goes in the commit message"
    )
    assert "Closes #" in step, "the literal keyword and its issue reference must be shown"
    assert re.search(r"squash", step, re.IGNORECASE), (
        "the reason must be named, or the next agent reverts it as redundant"
    )
    assert re.search(r"body", step, re.IGNORECASE), (
        "it must say the body is still wanted, or the fix reads as 'drop the body keyword'"
    )


def test_work_md_gives_a_command_to_verify() -> None:
    """A rule with no way to check it is a rule nobody applies."""
    step = _numbered_step(_text(WORK), "closes the issue")
    assert "git log -1 --format=%B" in step, "the check must be runnable, not implied"


def test_wrapup_verifies_closure_after_merging() -> None:
    """Belt and braces: even with the keyword in place, a merged PR that left its
    issue open must be caught before the session ends -- that is what made #61
    invisible for three PRs in a row."""
    text = _text(WRAPUP)
    step = _numbered_step(text, "actually closed their issues")
    assert "CLOSED" in step, "the check must compare against the issue's own state"
    assert re.search(r"gh issue view", step), "the check must be runnable"
    assert re.search(r"does \*\*not\*\* prove closure|does not prove", step, re.IGNORECASE), (
        "closingIssuesReferences is not proof of closure -- the trap this bug hides in"
    )


def test_wrapup_still_asks_for_the_keyword_when_it_commits() -> None:
    text = _text(WRAPUP)
    assert re.search(r"Closes #<n>|Closes #<issue", text), (
        "the step that opens the PR must repeat the keyword requirement, since that is "
        "often the first commit on a fresh branch"
    )
    # Renumbering must not orphan a step: every step stays sequential.
    numbers = [int(n) for n in re.findall(r"^(\d+)\.", text, re.MULTILINE)]
    assert numbers == list(range(1, len(numbers) + 1)), f"steps are not sequential: {numbers}"


def test_reviewer_checks_the_closing_keyword() -> None:
    """The reviewer is what stands between a bad commit message and a merge, so the
    check belongs in its numbered list, not in a note."""
    reviewer = _text(REVIEWER)
    assert re.search(r"^8\.\s+\*\*Closing keyword", reviewer, re.MULTILINE), (
        "the reviewer's checks must include the closing keyword as its own item"
    )
    assert re.search(r"does not prove", reviewer, re.IGNORECASE), (
        "the reviewer must not treat a parsed reference as proof of closure"
    )


def test_claude_md_routes_work_with_the_keyword() -> None:
    """The plain-English route is what a session reads first; a route that omits this
    sends the agent straight to the body-only habit."""
    rule = _text(CLAUDE_MD)
    assert "/work` routine" in rule
    line = [ln for ln in rule.splitlines() if "/work` routine" in ln and "Closes" in ln]
    assert line, "the /work route must mention the commit-message keyword (#61)"


def test_pr_template_asks_for_it_in_both_places() -> None:
    template = _text(PR_TEMPLATE)
    assert "Closes #<issue-number>" in template, "the placeholder must name the issue"
    assert re.search(r"commit message", template, re.IGNORECASE), (
        "the template must ask for the commit message, not just display a keyword"
    )
    assert "#61" in template, "the template should say why, or it looks like boilerplate"


def test_work_md_rule_is_a_standalone_line_not_prose() -> None:
    """#65 obeyed the letter of the old rule and missed its point: its commit
    message *mentioned* `Closes #N` inside a sentence about the bug and closed
    nothing. The rule must therefore require a standalone line, and this test
    must read that requirement out of the operative step -- prose that merely
    discusses the keyword anywhere in the step no longer counts (#68)."""
    step = _numbered_step(_text(WORK), "closes the issue")
    assert re.search(r"standalone line", step, re.IGNORECASE), (
        "the rule must say the keyword is a standalone line; 'put the keyword in the "
        "commit message' is the wording #65 satisfied without obeying"
    )
    assert re.search(r"(never|not)[^.;]*inside a sentence", step, re.IGNORECASE), (
        "the rule must exclude the in-sentence mention that #65 shipped"
    )


def test_work_md_check_is_an_anchored_grep_of_the_first_lines() -> None:
    """#68's second defect: the old verification was a presence test over the
    whole message, which any later prose mention satisfies. The check must be a
    real grep, anchored to line starts and limited to the head of the message,
    so it fails on the exact commit #65 produced."""
    step = _numbered_step(_text(WORK), "closes the issue")
    assert re.search(r"grep\s+-i?E\s+\S*\^", step), (
        "the verification must be an anchored grep (`grep -iE '^...'`), not a presence test"
    )
    assert re.search(r"head\s+-?\s*\d*", step), (
        "the grep must be applied to the first lines of the message; a keyword "
        "buried deeper is discussion of the directive, not the directive"
    )


def test_work_md_puts_the_keyword_in_the_first_line() -> None:
    """The landing commit's subject is the first commit's subject on this repo
    (`squash_merge_commit_title=COMMIT_OR_PR_TITLE`, measured on #68), so the
    directive has to survive as the message's first line -- anywhere else can be
    reordered, truncated, or edited away at merge time."""
    step = _numbered_step(_text(WORK), "closes the issue")
    assert re.search(r"first line", step, re.IGNORECASE), (
        "the rule must put `Closes #<n>` on the first line of the first commit"
    )
    assert re.search(r"PR title", step), (
        "the squash subject is editable at merge time; the PR title must mirror "
        "the keyword or a hand-edited subject drops it (#68, five issues in)"
    )
