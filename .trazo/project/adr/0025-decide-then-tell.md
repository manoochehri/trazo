# 0025: Decide, then tell

**Date:** 2026-10-30  **Status:** proposed (needs the owner's review: it loosens a gate in `rules.md`)

Raised by the owner on 2026-10-30 and tracked in [#266](https://github.com/manoochehri/trazo/issues/266).
Reviewed by the architect role, whose changes are included.

## Context

The owner reports that agents do not ship or make decisions, that they must babysit, and that
agents ask too many questions. Calenda's issue comments show the pattern: a PM comment that says
"Next I'll send #216 to the reviewer" and then asks whether to carry on; an agent that merges a
PR and then asks "say the word" before running a mandatory skeptic check.

The rules produce this. `rules.md` "Ask before guessing" said to stop and ask for anything
"expensive, irreversible, or ambiguous", and nearly every real task is ambiguous somewhere.
`work.md` step 2 said to wait for the owner's OK on the plan unless the run was unattended.

## Decision

- A reversible choice belongs to the agent: pick the recommended option, record it on the issue
  in a comment that starts `Decided:` with the reason, and keep going. Reversible means that
  reverting a pull request undoes it and it touches no safety limit, no money, no data and no
  external system. The `Decided:` prefix makes decisions countable.
- Stop and ask only when a choice is expensive, hard to reverse, or inside a human-only limit
  (`CODEOWNERS` paths, the charter, secrets, spend, production). Keep working on anything that
  does not depend on the answer.
- "Safety limits are human-only" is unchanged and wins over this section. The reviewer, security
  and skeptic gates still run. The engineer still never sets a commit status.
- `work.md` step 2: post the plan to the issue and carry on in every mode. Stop at the plan only
  for a choice that meets the stop conditions above.
- Done means the pull request is ready with its checks and review verdicts on the current head
  and merged by whoever the repository's merge policy names, or the issue names the blocker.

This is consistent with ADR 0024 (schedule-started runs already post the plan and proceed); it
extends that behavior to attended sessions.

## Alternatives considered

- Keep "ambiguous" and add examples: rejected, because the word itself is what makes every task
  a stop.
- Remove the stop rule entirely: rejected; it is the only rule that sends expensive or
  irreversible choices to the owner.

## Consequences

- This loosens a rule that was a gate. The guardrails are the definition of reversible, the
  carve-out for human-only limits, the unchanged review and security gates, and the `Decided:`
  record, which lets the owner audit decisions.
- Measure over two weeks, stating sample sizes: `needs-decision` and `needs-pm` issues opened,
  `Decided:` comments per issue, time from issue open to merged PR, issues that stall without a
  named blocker, and `Decided:` choices later reverted or reopened. Any PR touching `CODEOWNERS` or
  the charter without owner review, or merged without a verdict on its head, is a failure (target 0).
- It does not give any role ownership of a multi-piece goal; that is a separate proposal.
- Review: governance in `src/`, so `tier:senior` and a security review apply (ADR 0018).
