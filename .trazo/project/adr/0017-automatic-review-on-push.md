# 0017: Reviews run automatically on PR heads, and only when they are needed

**Date:** 2026-10-13  **Status:** proposed

Raised on [#204](https://github.com/manoochehri/trazo/issues/204). The owner decided that no human
should have to trigger a review. This record supersedes the "no auto-loop" clause of
[ADR 0003](0003-review-security-github-tracked.md), which named this reopening as its revisit trigger.
ADR 0003's other decisions still stand.

## Context

`trazo/verdict` is per head SHA, and only the reviewer subagent sets it. Every push resets it. The
review was a manual step, so PRs sat red after each push until someone asked for a review. Reviews
cost subagent budget, so running one on every push is also too expensive.

## Decision

1. **Automatic trigger.** A workflow (`.github/workflows/review.yml`) runs the reviewer for the head
   SHA when a non-draft PR is opened, marked ready, or pushed to. The reviewer stays a fresh-context
   subagent, not the engineer.
2. **Review the merge candidate.** Draft PRs are skipped. A head SHA that already has a terminal
   `trazo/verdict` (success or failure) is skipped.
3. **Review only the delta.** When an earlier head of the PR has a terminal verdict, the reviewer
   reviews only the diff since that head.
4. **Security on sensitive paths.** A diff touching `.github/workflows`, `CODEOWNERS`, secrets
   handling, dependencies (`pyproject.toml`, `uv.lock`) or permissions also gets the security subagent
   on that head. This is required regardless of size.
5. **Never stuck pending.** If the review run errors or times out, the workflow sets
   `trazo/verdict` to `failure` with a reason, so the PR shows red with a cause and not an
   unexplained pending state.
6. **Owner kill switch.** The workflow runs only while the repository variable
   `AUTO_REVIEW_ENABLED` is `true`. The owner can turn it off without a code change.
7. **Same-repo PRs only.** Forked PRs never receive `ANTHROPIC_API_KEY`, because their diff is
   untrusted input.

## Exception to the gate rule

The rule that only the reviewer and security subagents set `trazo/verdict` (#115) still holds for
`success`. The workflow may only tighten the gate: `failure` when the run errors. It never writes
`success`. `pending` comes from the reviewer when it starts, as before.

## Alternatives considered

- **Review every push.** Rejected: costs the most, and mid-fixup pushes don't need a review.
- **Review only on a manual `/check-pr`.** Rejected: the owner does not want a human trigger.
- **Review only at merge (a required check that runs on the final head).** Deferred: it would be
  cheaper still, but it would hold the status back until merge time. Revisit after the cost
  is measured.

## Consequences

- Cost is per non-draft PR head that has no verdict yet. It is bounded by the monthly spend cap set
  in the Anthropic console, and by the kill switch.
- `ANTHROPIC_API_KEY` must be stored as a GitHub Actions secret by the owner. It is not stored in
  AWS Secrets Manager, and the engineer does not read it.
- Workflow and CODEOWNERS-protected paths need the owner's review and a separate security review
  before merge, per [the rules](../../rules.md).
- The reviewer's tool allowlist (`claude_args` in the workflow) limits what the run can do. The
  rule that only the reviewer sets `trazo/verdict` is still enforced by the reviewer role, not by
  the allowlist, since `gh api` is allowed for the reviewer's own status write.
- Trivial-delta skipping (docs-only or formatting-only changes) is not in this version. Revisit once
  the cost is measured.
