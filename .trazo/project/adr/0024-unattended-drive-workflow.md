# 0024: Unattended drive workflow with auto-merge on passed gates

**Date:** 2026-10-30  **Status:** accepted

Decided by the owner in session: work should be picked up and shipped without per-issue approval,
and pull requests should merge automatically once their gates pass. The owner's approval of
auto-merge for the routine class is recorded on [#115](https://github.com/manoochehri/trazo/issues/115).

## Context

Work stalled on owner approvals: each `/work` run waited for an OK on its plan, and nothing picked
up the next issue after a session ended. Sessions on the owner's laptop advance only while a turn
is running, so a milestone could not be driven to completion while the owner was away.

## Decision

`.github/workflows/drive.yml` runs on a 30-minute schedule and on manual dispatch. It does nothing
unless the repository variable `DRIVE_ENABLED` is `true`, which is the owner's kill switch. A
concurrency group runs one driver at a time. It has four jobs, split so that the agent that reads
untrusted issue text never holds a token that can write.

- **`work`** picks the highest-priority open issue in the open milestone (P0, P1, P2, then
  unlabeled, oldest first). It skips issues labeled `needs-decision`, `needs-pm` or `epic`, issues
  that already have an open pull request on an `issue-<n>` branch, issues with an open blocker,
  and issues not written by the owner, a member or a collaborator (the repository is public, so
  issue text is data). The agent gets the issue's title and body as a file, runs with a read-only
  token and no `gh` access, has its API key scrubbed from subprocesses, and may not edit `.git`,
  `.github` or the Makefile. It leaves its change in the working tree; the job keeps that as a patch.
  This is the schedule-started case that `work.md` already names as unattended.
- **`publish`** has no LLM. It applies the patch on a fresh branch, commits with `Closes #<n>:` as the
  first line, pushes, appends the closing keyword to the pull request body, opens the pull request and
  posts the plan on the issue.
- **`stuck`** has no LLM. When a run picked an issue but produced no usable change, it labels the
  issue `needs-pm` and comments, so the picker does not choose it again every 30 minutes.
- **`merge`** has no LLM. It squash-merges an `issue-*` pull request only when the exact head has a
  `trazo/verdict` success, every check run passes, the linked issue (from the pull request's closing
  references) and the pull request carry no `needs-decision`, `needs-pm` or `unverified-in-engine`
  label, and `scripts/report_verdict.py --sensitive` reports the change as not sensitive. That script
  is the classifier `review.yml` already uses (ADR 0020, 0023): it reads both sides of a rename and
  fails closed on a short file listing, and it reads `.github/CODEOWNERS` from the default branch.
  Sensitive changes are a decision class and never auto-merge. Fork pull requests are ignored, a
  failure on one pull request is skipped, and the merge uses `--match-head-commit`.

`DRIVE_ENABLED` stays unset until #247 (supervised live run), #252 (agent identity), #249 (spend
cap), #258 (backstops) and #231 (CODEOWNERS gaps) are closed.

## Alternatives considered

- Open pull requests only and leave merging to the owner: rejected by the owner, who wants work
  shipped without waiting on approvals.
- Rely on branch protection and GitHub auto-merge: rejected as the sole gate, because it depends on
  settings a reader cannot see in the repository.
- One job holding both the agent and a write token: rejected after security review (a crafted issue
  could take over an agent holding write access and the API key).
- A second, hand-written list of protected paths in the merge job: rejected, because it drifted from
  `report_verdict.py` within a day of being written. One classifier, one list.

## Consequences

- Changes to `drive.yml` are workflow changes and need owner review under `CODEOWNERS` and a
  security review before they take effect.
- Pull requests opened with the built-in `GITHUB_TOKEN` do not start `pull_request` workflows, so
  until the agent has its own identity (#252) the driver's pull requests get no review and nothing
  merges. A squash merge made with that token also does not start `push` workflows on `main`.
- `UNVERIFIED`: the `claude-code-action` tool allow-list and subprocess scrubbing, and the live
  behavior of the four jobs. The first run must be supervised (#247).
- Merging with no human in the loop means a bad change can reach `main` if the reviewer and the
  verdict gate both miss it. The rollback is a revert commit.
- Residual risk: an agent that runs `make test` after editing a source file that the tests import
  runs that code on the runner. The job token is read-only and the Makefile is not editable, so the
  damage is bounded to the runner, but it is not zero.
