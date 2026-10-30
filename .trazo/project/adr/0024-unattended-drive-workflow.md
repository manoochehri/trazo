# 0024: Unattended drive workflow with auto-merge on passed gates

**Date:** 2026-10-30  **Status:** accepted

Decided by the owner in session: work should be picked up and shipped without per-issue approval,
and pull requests should merge automatically once their gates pass.

## Context

Work stalled on owner approvals: each `/work` run waited for an OK on its plan, and nothing picked
up the next issue after a session ended. Owner-invoked sessions cannot drive a milestone to
completion on their own.

## Decision

- `.github/workflows/drive.yml` runs on a 30-minute schedule and on manual dispatch. Its `work` job
  takes the highest-priority open issue in the open milestone (P0, P1, P2, then unlabeled, oldest
  first), skipping issues labeled `needs-decision` or `needs-pm`, and runs the work routine
  unattended. This is the schedule-started case that `work.md` already names as unattended.
- Its `merge` job squash-merges an open pull request from an `issue-*` branch only when the exact
  head has a `trazo/verdict` success, passing check runs, and `trazo/security` success or absent
  (absent means the change touched no security-sensitive path). The job checks these itself rather
  than relying on branch protection, and it refuses when the linked issue carries `needs-decision`
  or `needs-pm`.
- The run uses `--match-head-commit`, so a push that lands after the check does not merge.
- Concurrency group `drive` runs one driver at a time.

## Alternatives considered

- Open pull requests only and leave merging to the owner: rejected by the owner, who wants work
  shipped without waiting on approvals.
- Rely on branch protection and GitHub auto-merge: rejected as the sole gate, because it depends on
  settings a reader cannot see in the repository.

## Consequences

- Changes to `drive.yml` are workflow changes and need owner review under `CODEOWNERS` before
  they take effect.
- `UNVERIFIED`: the `claude-code-action` tool allow-list in `drive.yml` and the behavior of
  `gh pr merge --match-head-commit` have not been exercised on a live run. The first run must be
  watched.
- Merging with no human in the loop means a bad change can reach `main` if the reviewer and the
  verdict gate both miss it. The rollback is a revert commit.
