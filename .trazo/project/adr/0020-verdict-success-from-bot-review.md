# 0020: A bot review can set trazo/verdict to success

**Date:** 2026-10-13  **Status:** accepted

**Supersedes** the "What the workflow may write" section of [0017](0017-automatic-review-on-push.md),
which said the workflow writes `trazo/verdict` only as `failure`. The rest of 0017 stands: the
automatic trigger, the gate, base-branch checkout, the kill switch, and the security review on
sensitive paths.

Owner decision on [#213](https://github.com/manoochehri/trazo/issues/213), given 2026-10-13:
["should a bot's review be enough to turn the merge check green a, make it so"](https://github.com/manoochehri/trazo/issues/213#issuecomment-6150154821).
Decided by the owner. The PM assist on the same issue confirmed that building now needs no further
decision and set the conditions below.

## Context

0017 left a clean automatic review without a verdict. A person then had to run `/check-pr` to turn
the PR green, which is the complaint in [#204](https://github.com/manoochehri/trazo/issues/204). Every
merged head also got two reviews. The owner chose to let the bot's review count toward the merge gate.

## Decision

The report job in `.github/workflows/review.yml` runs `scripts/report_verdict.py` from the base branch
and writes `trazo/verdict`:

1. **`success`** only when a review meets all of these:
   - it is from the login `github-actions[bot]`;
   - its `commit_id` is the pull request head SHA;
   - it was submitted after the review run started;
   - its first line, trimmed, is exactly `merge`.
2. The latest review that meets the first three conditions decides. A later `merge after fixes` or a
   malformed verdict overrides an earlier `merge`.
3. **`failure`** in every other case. That includes no qualifying review, an API error, an unreadable
   response, and a review job that did not finish.
4. Security subagent reviews use `pass` and `fail` as their first line. The script does not count them,
   so they neither set nor override the verdict.
5. Reviews from `/check-pr` are posted from the owner's account. They do not count here, because
   `/check-pr` keeps setting its own status under #115.

The report job reads reviews with `pull-requests: read` and the run start time with `actions: read`. It
has no `contents: write` and no `pull-requests: write`. The review job still has no status token.

## Accepted risks

- **Prompt injection.** A malicious diff could persuade the reviewer to write `merge`, and the gate would
  then turn green. The owner accepted this. The mitigations stay in place: the review runs from a
  base-branch checkout, the PR title, body and diff are treated as data, the review job has no status
  token, and the owner can turn the workflow off with `AUTO_REVIEW_ENABLED`.
- **Forgery that already exists.** This is not new with 0020. The owner's own token can write
  `trazo/verdict` directly ([#44](https://github.com/manoochehri/trazo/issues/44)). A pull request that
  adds a workflow with `statuses: write` can write it too ([#212](https://github.com/manoochehri/trazo/issues/212)).
  The gate is therefore not unforgeable. This record does not claim that it is.

## Unverified until the first live run

- The login that the review action posts under is assumed to be `github-actions[bot]`. The first live run
  must confirm it. The PR records the login observed. If no review is found under that login, the gate
  fails closed.

## Consequences

- A clean automatic review now sets `success`, so a clean PR no longer needs a manual `/check-pr`.
- Owner review through CODEOWNERS is still required before merge, because `.github/workflows/` is
  protected. The bot cannot approve.
- The #115 rule that only the reviewer sets `trazo/verdict` now has one more path: the report job, from a
  bot review that says `merge`. The rule text in the reviewer role and the RUNBOOK says so.
