# 0017: Reviews run automatically on PR heads, and the workflow may only tighten the gate

**Date:** 2026-10-13  **Status:** proposed

Raised on [#204](https://github.com/manoochehri/trazo/issues/204). The owner decided that no human
should have to trigger a review. This record supersedes the "no auto-loop" clause of
[ADR 0003](0003-review-security-github-tracked.md), which named this reopening as its revisit trigger.
ADR 0003's other decisions still stand.

## Context

`trazo/verdict` is per head SHA, and only the reviewer subagent sets it. Every push creates a new head
with no verdict. The review was a manual step, so PRs sat red after each push until someone asked for a
review.

## Decision

1. **Automatic trigger.** A workflow (`.github/workflows/review.yml`) runs the reviewer on the head SHA
   when a non-draft PR is opened, marked ready, or pushed to. Every push to a non-draft PR is reviewed,
   because each push is a new head without a verdict. The reviewer stays a fresh-context subagent, not
   the engineer.
2. **Gate.** Draft PRs are skipped. A head SHA that already has a terminal `trazo/verdict` (success or
   failure) is skipped. The gate job reads that status and nothing else.
3. **Base code, PR data.** The review job checks out the base branch, so the PR cannot supply the
   reviewer's settings, hooks or instructions. It loads only user-level settings
   (`--setting-sources user`). The PR title, body, diff and comments are read as data.
4. **No status writes from the agent.** The review job has no commit-status write permission and no
   `gh api` access. Neither the reviewer nor the security subagent sets a status in this run.
5. **Failure, never a silent pending.** A separate report job writes `trazo/verdict` as `failure` when
   the review job did not succeed: it errored, timed out, or was cancelled. The report job runs even
   when the review job is cancelled, because it is a separate job with `if: always()`.
6. **Security on sensitive paths.** A diff touching `.github/workflows`, `CODEOWNERS`, secrets
   handling, dependencies (`pyproject.toml`, `uv.lock`) or permissions also gets the security subagent
   on that head. Its result is posted as a review comment. The security subagent does not set `trazo/security` in this run.
7. **Owner kill switch.** The workflow runs only while the repository variable `AUTO_REVIEW_ENABLED`
   is `true`. The owner can turn it off without a code change.
8. **Same-repo PRs only.** Forked PRs never receive `ANTHROPIC_API_KEY`, because their diff is
   untrusted input.

## What the workflow may write

The workflow writes `trazo/verdict` only as `failure`, and only when the review did not finish. It
never writes `success` or `pending`. The rule that only the reviewer sets `trazo/verdict` success (#115)
therefore still holds, and no LLM output can grant a merge gate.

**Open decision for the owner.** On a clean review the workflow leaves the status unset, so the PR
stays blocked until a status is set. Options: (a) a reviewer run with status access, from `/check-pr`
on the owner's machine, which sets `success` or `failure` as today; (b) a deterministic job that
writes `success` from a trusted, non-LLM check. Option (b) needs its own design review, because an
LLM verdict must not reach the gate. This record does not choose between them.

## Alternatives considered

- **Review only the merge candidate, once.** Deferred: it is cheaper, but it holds the status back
  until merge time. Revisit after the cost is measured.
- **Let the agent set statuses.** Rejected: a prompt-injected diff could grant `success`. The
  security review on #205 found this as a must-fix.
- **Skip trivial deltas (docs-only or formatting-only).** Not in this version. Revisit once the cost is
  measured.

## Consequences

- Cost is per non-draft PR head that has no verdict yet. Every push to a non-draft PR costs one review.
  It is bounded by the monthly spend cap set in the Anthropic console, and by the kill switch.
- `ANTHROPIC_API_KEY` must be stored as a GitHub Actions secret by the owner. It is not stored in
  AWS Secrets Manager, and the engineer does not read it.
- The workflow and CODEOWNERS-protected paths need the owner's review and a separate security review
  before merge, per [the rules](../../rules.md).
- The agent can still post a review with `gh pr review`. It is prompted not to approve or request
  changes, and GitHub refuses a bot approval in this repository, so the residual risk is a comment
  with a wrong verdict word. The security review should weigh this.
- The workflow uses the action pinned to commit `1d6de8c`, not a tag, and the checkout pinned to its
  commit SHA. Whether Actions accepts the action's tag-object SHA was not checked; the pin is a commit.
