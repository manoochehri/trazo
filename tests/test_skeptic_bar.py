"""Guards for the skeptic role and its standing gate (issue #58).

The issue asks for more than an agent file. Its real requirement is that
"skeptic review before it counts" be a *standing rule rather than a one-off*, and
that the skeptic run "read-only and separately from the building agent's own
session". Both of those are prose, so nothing but a test stops them being edited
into a suggestion -- the same shape as #36 and #47.

Two failure modes these guard against, both real in this repo's history:

1. **The gate degrades to optional.** An agent file that exists but is never invoked
   is a role nobody calls, and the workflow rule the issue insists on ("not an
   optional step invoked only on request") silently evaporates. So the tests assert
   the *invocation* in each surface that would trigger one, not merely the agent's
   existence.
2. **The separation is lost.** A skeptic invoked in the building conversation
   inherits its blind spots, which is the entire reason the role exists (#0003's
   reasoning applied to results). Asserted as read-only tools plus subagent-only
   framing, matching the reviewer and security agents.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKEPTIC = REPO_ROOT / ".claude" / "agents" / "skeptic.md"
BAR = REPO_ROOT / ".trazo" / "project" / "SKEPTIC_BAR.md"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
RULES = REPO_ROOT / ".trazo" / "rules.md"
WORK = REPO_ROOT / ".claude" / "commands" / "work.md"
ADVISOR = REPO_ROOT / ".trazo" / "ADVISOR.md"
KICKOFF = REPO_ROOT / ".claude" / "commands" / "kickoff.md"

# The issue's own requirements, as assertions.
VERDICTS = ("holds", "holds with caveats", "does not hold")


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _frontmatter(path: Path) -> str:
    text = _text(path)
    assert text.startswith("---\n"), f"{path.name} has no frontmatter"
    end = text.index("\n---\n", 3)
    return text[4:end]


def test_skeptic_exists_with_the_role_the_issue_specifies() -> None:
    """Read-only, Opus, and named so the subagent can be invoked at all."""
    fm = _frontmatter(SKEPTIC)
    assert re.search(r"^name: skeptic$", fm, re.MULTILINE)
    assert re.search(r"^model: opus$", fm, re.MULTILINE)
    tools = re.search(r"^tools: (.+)$", fm, re.MULTILINE)
    assert tools, "no tools: line, so the subagent cannot be invoked"
    assert tools.group(1) == "Read, Grep, Glob, Bash", (
        f"tools are {tools.group(1)!r}; the issue specifies read-only, and Edit/Write "
        "here would let the skeptic edit the very result it is reviewing"
    )


def test_skeptic_never_edits_or_builds() -> None:
    """The issue: "never edits files and never builds the thing it's reviewing"."""
    body = _text(SKEPTIC)
    assert "never edit" in body.lower()
    assert "never build" in body.lower()
    assert re.search(r"read-only commands", body), "Bash must be scoped, not just present"


def test_verdict_is_one_of_exactly_three_and_is_mandatory() -> None:
    """A free-text verdict is not a gate: nothing downstream can key off it."""
    body = _text(SKEPTIC)
    assert "one of exactly" in body, "the three verdicts must be presented as exhaustive"
    for verdict in VERDICTS:
        assert verdict in body, f"missing verdict {verdict!r}"
    assert re.search(r"\bVerdict\b", body), "the verdict must be a labelled field"


def test_verdict_carries_evidence_and_a_settling_check() -> None:
    """The issue asks for the three most serious problems "with evidence", and what
    check would settle each. A problem list without either is a vibe."""
    body = _text(SKEPTIC)
    assert re.search(r"three most serious problems", body, re.IGNORECASE)
    assert re.search(r"evidence", body, re.IGNORECASE)
    assert re.search(r"would settle it", body, re.IGNORECASE)
    assert re.search(r"could not check", body, re.IGNORECASE), (
        "an unchecked item must be reported, or silence reads as a pass"
    )


def test_every_named_failure_mode_is_hunted() -> None:
    """The issue names these explicitly; each is a distinct bug, so each is asserted."""
    body = _text(SKEPTIC).lower()
    for mode in (
        "look-ahead",
        "overlapping samples",
        "tuned after seeing the result",
        "multiple-comparisons",
        "outlier",
        "rounding",
        "impossible result",
    ):
        assert mode in body, f"failure mode {mode!r} from the issue is missing"


def test_the_bar_exists_and_is_what_the_skeptic_checks() -> None:
    """The issue is explicit that the bar is the per-project part, so the agent must
    actually read it rather than carrying a generic list inline."""
    agent = _text(SKEPTIC)
    assert ".trazo/project/SKEPTIC_BAR.md" in agent, "the skeptic must check the project's bar"
    assert re.search(r"`.trazo/project/SKEPTIC_BAR\.md`", agent), "cite it as a path"
    assert BAR.exists(), "the bar doc is missing"

    bar = _text(BAR)
    for heading in ("A.", "B.", "C.", "D.", "E."):
        assert heading in bar, f"bar section {heading} missing"
    # Item numbers, so a verdict can cite a line rather than a general impression.
    for item in ("A1", "A2", "A3", "B1", "B2", "B3", "C1", "C2", "C3", "D1", "D2", "D3"):
        assert re.search(rf"\*\*{item}\b", bar), f"bar item {item} is missing"
    assert "specialise" in bar, "the per-project items must be marked as such"


def test_the_gate_is_a_standing_rule_not_a_suggestion() -> None:
    """The issue's own test: "not an optional step invoked only on request".

    The rule itself moved to the tool-neutral core in #53: `.trazo/rules.md` is the single
    statement of the rules, and `CLAUDE.md` imports it. Pointing this at `CLAUDE.md` would
    have re-introduced the copy this framework exists to avoid. What still has to hold is
    that the rule reads as mandatory, and that the adapter says which subagent satisfies it.
    """
    rule = _text(RULES)
    assert re.search(r"A result is not a result until it has been checked", rule), (
        "the gate must be a named rule in the tool-neutral core"
    )
    for verdict in VERDICTS:
        assert verdict in _text(CLAUDE_MD), (
            f"the adapter must name the verdict {verdict!r} so the tool knows what it returns"
        )
    assert re.search(r"permanent record", rule), "the rule must say where the claim is held"
    assert re.search(r"every time", rule, re.IGNORECASE), (
        "invoked only when something looks suspicious is the failure the issue names"
    )


def test_work_invents_the_skeptic_on_a_quantitative_claim() -> None:
    """The invocation that makes rule 8 fire. Without it in /work the gate has no
    trigger, and an agent file nobody calls is a role that does not exist."""
    work = _text(WORK)
    # Match either `skeptic` or **skeptic**: the file uses bold, and a test that
    # demands backticks would only force a pointless edit to the rule it guards.
    assert re.search(r"skeptic\*{0,2}`?\s*subagent|\*\*skeptic\*\*\s*subagent", work), (
        "/work must invoke the skeptic subagent"
    )
    assert re.search(r"quantitative|empirical", work, re.IGNORECASE), (
        "the trigger must name the kind of claim that requires it"
    )
    assert re.search(r"does not hold.{0,80}must-fix|must-fix.{0,80}does not hold", work, re.I), (
        "a failing verdict must be a must-fix item, or it does not block the merge"
    )


def test_advisor_and_kickoff_carry_the_rule() -> None:
    """The PM is the one who acts on a result, and kickoff is where the bar is
    filled in. A gate with no entry point in either is decoration."""
    advisor = _text(ADVISOR)
    assert "`skeptic`" in advisor, "ADVISOR.md must route numbers to the skeptic"
    assert "Act on a quantitative" in advisor, (
        "ADVISOR.md must forbid acting on an un-cleared result"
    )

    kickoff = _text(KICKOFF)
    assert ".trazo/project/SKEPTIC_BAR.md" in kickoff, (
        "the bar is per-project, so kickoff is the only place it can be filled in"
    )
    assert re.search(r"specialise", kickoff), "kickoff must say which lines to replace"


def test_separation_from_the_building_session_is_stated() -> None:
    """The issue flags this as what makes the role work: the value comes from not
    sharing the builder's blind spots."""
    agent = _text(SKEPTIC).lower()
    # "shar", not "share": the file says "sharing", and testing the exact inflection
    # would break the moment the sentence is reworded.
    assert "shar" in agent, "the separation must be explained"
    assert "blind spot" in agent, "must name the blind spots the separation avoids"
    assert "same conversation" in agent, "must say why a second question in-session is not enough"

    rule = _text(CLAUDE_MD)
    assert re.search(r"subagent-only", rule), "skeptic must be subagent-only, never a role switch"
    assert re.search(r"`reviewer`, `security`, and `skeptic`", rule), (
        "the subagent-only sentence must name the skeptic alongside the others"
    )
