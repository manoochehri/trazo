# 0023: Bind an automatic verdict to the exact head reviewed

**Date:** 2026-10-13  **Status:** accepted

Decided by the owner on [#224](https://github.com/manoochehri/trazo/issues/224). This supersedes
ADR 0020's use of the workflow run start time and `commit_id` alone to qualify a successful review.

## Context

GitHub records a pull request review against the head that exists when the review is submitted. A
reviewer can start on H1, then post `merge` after H2 is pushed; the review's `commit_id` can then be
H2 even though the reviewer read H1. Checking only `commit_id` and the workflow run start could
credit that stale review to H2.

## Decision

- The report job reads `started_at` from the `review` job in the current workflow run attempt, using
  GitHub's [list jobs for a workflow run attempt API](https://docs.github.com/en/rest/actions/workflow-jobs).
  Missing job data or a missing start time fails closed.
- A reviewer verdict must contain exactly one standalone `Reviewed-Head: <full SHA>` line. The
  marker must equal the event's head SHA, and the review's `commit_id` must also equal that SHA.
- The verdict is eligible only when `submitted_at` is strictly after that review job's `started_at`.
  The current head must still match the event SHA before the report job writes its status.
- The reviewer checks the requested SHA before reading the diff and again before posting. If the PR
  moved, it does not post a verdict.
- Missing, malformed, duplicate, stale-head, pre-review, or unreadable data results in `failure`.
  Existing sensitive-path exclusions and the security `FAIL` veto remain unchanged.

## Consequences

An old review cannot make a newer head green just because GitHub records its submission on that
newer head. Manual reviewer verdicts also identify the exact commit they cover. This is fail-closed:
a missing marker or job timestamp can leave a PR blocked until a fresh review runs.
