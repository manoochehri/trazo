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
  token and no `gh` access, and may run no commands at all, only read and edit files inside the
  workspace: an agent that can run `make test`, or even `git log --output`, can write and run its own
  code on a runner that holds the API key, so the pull request's CI runs the tests instead. Its API
  key is scrubbed from subprocess environments, and it may not edit `.git`, `.github`, `.claude`, the
  Makefile or paths outside the workspace. The collect step verifies the `.git` metadata is unchanged
  and runs git with hooks, the file monitor and external diff disabled. It leaves its change in the working tree; the job keeps that as a patch. This is the
  schedule-started case that `work.md` already names as unattended.
- **`publish`** has no LLM. It rejects a patch with binary hunks, symlinks, submodule entries, more
  than 100 files or over 1 MB, and rejects agent text that contains a closing keyword. It applies the
  patch on a branch named `issue-<n>-drive-<run id>` (unique, so a closed pull request's old branch
  cannot block a retry), commits with `Closes #<n>:` as the first line, pushes, opens the pull
  request with the closing keyword written by the workflow, and posts the plan on the issue. Agent
  text is marked as untrusted and its @-mentions are defused.
- **`stuck`** has no LLM. When a run picked an issue but produced no usable change, or publishing
  failed, it labels the issue `needs-pm` and comments, so the picker does not choose it again every
  30 minutes. A cancelled run is not stuck.
- **`merge`** has no LLM. It squash-merges an `issue-*` pull request only when the exact head has a
  `trazo/verdict` success (read from the combined commit status, so a failure cannot fall off a
  page), every check run passes, the pull request closes exactly the issue named in its branch,
  that issue and the pull request carry no `needs-decision`, `needs-pm` or `unverified-in-engine`
  label, and `scripts/report_verdict.py --sensitive` reports the change as not sensitive. That script
  is the classifier `review.yml` already uses (ADR 0020, 0023): it reads both sides of a rename and
  fails closed on a short file listing, and it reads `.github/CODEOWNERS` from the default branch.
  Sensitive changes are a decision class and never auto-merge. Fork pull requests are ignored, a
  failure on one pull request is skipped, and the merge uses `--match-head-commit`.

Every job runs only from the default branch, so a manual run on another branch cannot substitute its
own scripts or CODEOWNERS. The merge job takes every non-fork `issue-*` pull request, including those
opened from interactive sessions, which is the routine class the owner approved on #115.

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
- Residual risk: the agent job holds the API key while it runs. Environment scrubbing does not stop
  code on the same runner from reading the parent process, so the agent is allowed no command that
  runs code it wrote. A spend-capped, dedicated key (#249) bounds the loss if that fails.
- The patch the agent produces is untrusted code that CI then runs on the pull request, so CI and the
  reviewer gate remain the control. The agent cannot capture fail-first output, so its pull requests
  carry a stated `Fail-first exemption`; a follow-up must produce that evidence in a job with no key.
- When #252 gives the driver a stronger token, `publish` needs a fresh security review.
