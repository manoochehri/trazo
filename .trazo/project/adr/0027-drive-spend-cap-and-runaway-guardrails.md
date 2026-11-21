# 0027: Drive spend cap and runaway guardrails

**Date:** 2026-11-19  **Status:** accepted

Implements [#249](https://github.com/manoochehri/trazo/issues/249) and [#258](https://github.com/manoochehri/trazo/issues/258)
on top of [ADR 0024](0024-unattended-drive-workflow.md). Every change tightens a limit; none loosens one.

## Decision

- **Spend per run.** The agent runs with `--max-turns 60` (already there), `--max-budget-usd` (default 2,
  repo variable `DRIVE_MAX_USD_PER_RUN`) and a 30-minute job timeout (was 45). The dollar flag is checked
  against Claude Code's client-side cost estimate, not the bill, and works in print mode only
  ([CLI reference](https://code.claude.com/docs/en/cli-reference)). `UNVERIFIED`: that `claude-code-action`
  runs the CLI in print mode and passes the flag through. The strongest limit that does not depend on this is
  the turn bound plus the timeout plus the daily run cap; the real ceiling is a spend limit on a dedicated
  API key, which only the owner can set in the Anthropic console.
- **Runs per day.** `DRIVE_MAX_RUNS_PER_DAY` (default 4) agent runs per UTC day, counted from the earlier
  runs' `work the issue` step.
- **Merges per day.** `DRIVE_MAX_MERGES_PER_DAY` (default 5), enforced by the work guard and by the merge job.
- **One drive PR in flight.** No agent run while an open pull request has a branch `issue-<n>-drive-<run>`.
- **`drive-halt`.** While any open issue carries the label, `work` and `merge` do nothing.
- **Circuit breaker.** After two failures in a row (a failed run, a drive pull request whose `trazo/verdict`
  failed, a revert of a drive merge; idle runs are not events and a merged drive PR resets the count) the
  `breaker` job opens an issue labeled `drive-halt`. Only a person closes it.
- **Digest.** A daily run comments the last 24 hours of merges on the open `drive-digest` issue.
- A bad or missing variable falls back to the default, and every guard fails closed.

## Consequences

- `UNVERIFIED`: live behavior of all of the above, including the Actions API calls used to count runs;
  #247 checks it.
- The digest and breaker add a second cron (13:05 UTC), which also starts the other jobs once; the caps bound it.
- Changes to `drive.yml` need owner review (CODEOWNERS) and a security review.
