# 0028: A workflow_run report job sets trazo/verdict as the reviewer App

**Date:** 2026-11-22  **Status:** accepted

Implements option 1 of [#291](https://github.com/manoochehri/trazo/issues/291), decided by the owner in
session on 2026-11-22 ("lock it first", recorded on the issue). Amends where the report of
[0020](0020-verdict-success-from-bot-review.md) runs and who writes the status; the decision rules of
0017, 0020 and 0023 (gate, base-branch review, exact-head binding, sensitive paths, kill switch) stand.

## Decision

- `review.yml` stays on `pull_request` with no App key and keeps only the `gate` and `review` jobs. It
  sets no status.
- `.github/workflows/report.yml` runs on `workflow_run` of `review` (completed). A `workflow_run` workflow
  runs the file on the default branch and `GITHUB_REF` is the default branch
  ([events docs](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_run)),
  and an environment's deployment rule is matched against `GITHUB_REF`
  ([environments docs](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)),
  so the job declares `environment: trazo-apps` (main only) and mints a reviewer App token with
  `actions/create-github-app-token` (same pinned commit as `drive.yml`), `statuses: write` only.
- It sets `trazo/verdict` and nothing else. It does not set `trazo/security`: the review job never did
  (its prompt forbids statuses) and the security subagent sets that context itself.
- The report never checks out or runs pull request code. The head SHA, run id and attempt come from the
  event payload; the pull request is found from the head SHA through the API; titles, branch names and
  artifacts are never read. Changed paths come from the compare endpoint between two fixed SHAs.
- **Only pull requests into the default branch are reported** (`.base.ref` equals the repository's default
  branch, from the API and the event, never PR text; else no verdict). A commit status is shared by every PR
  with that head, so a verdict earned against another base (a sensitive branch plus one benign commit) would
  otherwise show green on a PR of the same head into the default branch. The review must also have
  seen that base: a re-run keeps its original event, so a review of `x...H` re-run after a retarget to the
  default branch would otherwise yield a verdict for a diff the reviewer never saw. The `gate` in `review.yml`
  therefore requires the event's base branch to be the default branch, and the `edited` trigger counts only
  when the base changed (`changes.base`), so a retarget starts a fresh review of `main...H`. A title or body
  edit starts nothing (the gate skips it before the review job's cancel group), and a head that already has a
  terminal verdict is still skipped, so the trigger cannot loop. `UNVERIFIED` live (#247): that
  `changes.base` is present on a base change.
- Same decision rules as before: success only for a `github-actions[bot]` review that is on this head,
  names it in one `Reviewed-Head` line, says exactly `merge`, and was submitted after the `review` job
  started; sensitive paths never get success from the bot; a head that moved since the review gets no
  verdict (its own review run reports it); a terminal verdict already on the head is never overwritten.
- **Fork pull requests:** `review.yml` never reviews them (no API key), so the report does nothing for them
  (`head_repository` must be this repository). No status is set; a person sets it through `/check-pr`.
- **No verdict is set** when the gate was skipped, or the review was skipped because the head already had a
  terminal verdict. A gate that failed, or a review that failed, was cancelled or timed out, is `failure`.
- Cost: one run of delay after the review, and a host that enables review must also create the reviewer App
  and the `trazo-apps` environment (installer prints this).

## Residual risk

A pull request that edits `review.yml` runs its own copy with `GITHUB_TOKEN` and can post a forged `merge`
review as `github-actions[bot]`, which the report trusts. Mitigations: the `Reviewed-Head` and
after-job-start checks (a forged review must still name this head and post after the real job started),
`.github/workflows/` is in CODEOWNERS (owner review) and every workflow change needs a separate security
review. The App key itself is never reachable by a pull request. This does not close #212: closing it needs both the `integration_id` pin on `trazo/verdict` (owner) and
reviews posted by the reviewer App with `BOT_LOGIN` set to it, because the report trusts any
`github-actions[bot]` review, which any workflow in the repo can post. Until then `report.yml` is not the only
writer of `trazo/verdict`.

## Owner steps (owner-only, tracked in #212)

Pin `integration_id` on `trazo/verdict` in the `protect main` ruleset to the reviewer App, and require
`trazo/security`. Until then the status is set by the App but a person's account could still satisfy it. The
pin alone does not close #212 (see Residual risk).

## Consequences

- `UNVERIFIED` until a live run (#247): that `workflow_run` fires for a `review` run triggered by an
  App-authored PR; that the environment accepts the run; that the compare endpoint's file listing matches
  `changed_files` (a mismatch, or over 300 files, fails closed as sensitive); that the event's
  `pull_requests` is empty for forks (the job does not rely on it).
