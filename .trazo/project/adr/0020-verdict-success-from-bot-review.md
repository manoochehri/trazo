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
4. Security subagent reviews start with `PASS (...)` or `FAIL (...)`. A `FAIL` on the head fails the gate
   whatever the order of reviews. A `PASS` never sets or overrides the verdict; the script skips it.
5. **A pull request that changes a sensitive path never gets `success` from the bot.** Sensitive paths are
   every path in the base branch's `.github/CODEOWNERS`, plus `scripts/`, `.claude/`, `Makefile`,
   `Dockerfile`, `.pre-commit-config.yaml`, `pyproject.toml`, `uv.lock`, `.env.example`, and any path
   containing `secret`. Both names of a renamed file count. A listing that does not match the PR's
   file count counts as sensitive. For these PRs the report job writes `failure`, and a person sets the
   status through `/check-pr`, which routes a separate security review. A security `PASS` from the bot
   does not change this, because it comes from the same run as the `merge` and cannot be a check on it.
6. Reviews from `/check-pr` are posted from the owner's account. They do not count here, because
   `/check-pr` keeps setting its own status under #115.

The report job reads reviews with `pull-requests: read` and the run start time with `actions: read`. It
has no `contents: write` and no `pull-requests: write`. The review job still has no status token.

## Accepted risks

- **Prompt injection.** A malicious diff could persuade the reviewer to write `merge` on a non-sensitive PR,
  and the gate would then turn green. The owner accepted this. Sensitive PRs are excluded (item 5). The
  bot's security review is not an independent check for this risk: it runs in the same job, under the same
  bot account, reading the same diff, so one injected run can produce both results. The mitigations that
  stay in place: the review runs from a base-branch checkout, the PR title, body and diff are treated as
  data, the review job has no status token, and the owner can turn the workflow off with `AUTO_REVIEW_ENABLED`.
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
- **Not enforced today:** `.github/CODEOWNERS` names the owner for `.github/workflows/` and the other
  sensitive paths, but the live `protect main` ruleset does not enforce it. It has
  `require_code_owner_review: false` and `required_approving_review_count: 0`, and it requires
  `trazo/verdict` but not `trazo/security`. This record does not assume that owner review is in place.
- For a sensitive PR the bot cannot set `success`, so the gate stays red until a person sets it through
  `/check-pr`. That person is the owner's account, which the ruleset does not distinguish from any other
  merge. Nothing else on the gate separates a reviewed sensitive change from an unreviewed one.
- The #115 rule that only the reviewer sets `trazo/verdict` now has one more path: the report job, from a
  bot review that says `merge` on a non-sensitive PR. The rule text in the reviewer role and the RUNBOOK
  says so.
- Owner decision needed on #213: make `trazo/security` a required check, or turn on code-owner review with
  a bypass for the owner. Only the owner can change the ruleset.
