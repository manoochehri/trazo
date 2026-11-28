# Use it

**What do I type once Trazo is installed, and what happens?** This page follows one working session from your side. It lists the commands that exist, what each one does, and the few things that stay with you. The commands are Claude Code slash commands. In Codex the same routines are skills, and the plain-English requests below work the same way.

The main chat is the session you type into. It starts the other agents, sends pull requests to review and starts the merge, and it never edits repository files itself. A hook blocks that ([`front_door_guard.py`](https://github.com/manoochehri/trazo/blob/main/src/overlay/hooks/front_door_guard.py)). Trazo calls this session the Coordinator ([`rules.md`](https://github.com/manoochehri/trazo/blob/main/src/overlay/rules.md)).

## One session, step by step

Start Claude Code from the root of your repository. A session started in a subdirectory does not load the rules ([the adapter](https://github.com/manoochehri/trazo/blob/main/src/adapters/CLAUDE.md)).

| You type | What you see | What needs your decision |
|---|---|---|
| `/kickoff` (first time only) | An interview about the goal, success criteria, budget, deadline, constraints and stop rule. It then drafts the charter and plan. | Approve the charter and plan before anything is built. Labels, milestones and first issues follow only after you agree. |
| `/start` | The docs read, then your open issues in four groups: waiting on you, blocked on the project manager agent, ready to work, and epics in flight. | Say OK to the proposed work. Nothing changes before that. |
| "work on issue 12", or `/work 12` | An engineer agent builds issue 12 on its own branch in a separate copy of the repository. It opens a draft pull request, waits for CI, and reports the link and the review result. | Nothing, unless it stops with a question on the issue. |
| "is #15 ok", or `/check-pr 15` | A pass, or a list of must-fix items. A reviewer agent reads risky changes in its own session, and a security agent reads them too. A documentation-only change is checked against the diff and CI. | Nothing. The agents post their own verdicts. |
| "merge it" | The Coordinator starts the merge workflow once the checks pass, or tells you in one line which check is missing. | Nothing for ordinary changes. A change to the rules, workflows or `CODEOWNERS` paths needs your review. |
| `/wrapup` | `.trazo/project/STATUS.md` rewritten in its own pull request, decision records drafted, issues updated. | Confirm the wording of any decision record. |

Start a fresh session for the next task. Status travels through issues, pull requests and files, so nothing is lost ([`rules.md`](https://github.com/manoochehri/trazo/blob/main/src/overlay/rules.md), "Session budget").

## Other things you can ask for

| You say | What happens |
|---|---|
| "catch me up", "where are we", "what's next" | The project manager agent summarizes state from the repository, or `/start` does. |
| "what can I do", "help" | `/trazo` lists what you can do right now. |
| "should we...", "plan the next milestone" | `/pm` |
| "does this fit the design?" | `/architect` |
| "is this secure?" | The security agent checks it. |
| "is this number real?" | The skeptic agent checks it against the bar your project wrote down. |
| "we decided..." | `/decide` drafts a numbered decision record for you to approve. |
| "back to building", or an issue labeled `tier:senior` | `/eng`, or `/senior-eng` for the stronger engineer. |
| "quick status" | `/brief` prints under 15 lines and changes nothing. |

The reviewer, security and skeptic agents are subagent-only: you ask for them, and you do not switch into them with a command. A review that grades the conversation that produced the work is not a review ([the adapter table](https://github.com/manoochehri/trazo/blob/main/src/adapters/CLAUDE.md)).

## What stays with you

- **Answers to `needs-decision` issues.** Only you remove that label, after you answer.
- **Secrets.** You enter them yourself with `scripts/put_secret.sh`. Never paste one into a chat.
- **Money, production, repository settings, release tags, and changes to the rules, roles, hooks, workflows and charter.** An agent stops and asks instead of deciding ([`rules.md`](https://github.com/manoochehri/trazo/blob/main/src/overlay/rules.md), "Ask before guessing").

Everything else, such as building, tests, fixes inside an issue's scope, and verdicts, the agents handle. An implementation choice an agent can undo is recorded on the issue as a comment that starts `Decided:`.

## When something goes wrong

### A check stays pending

**You see** a pull request with a pending check, or the merge workflow saying the checks are not all green. The report job writes success or failure and never `pending`, so a pending status is a run that is still going or a status another writer set ([`report.yml`](https://github.com/manoochehri/trazo/blob/main/.github/workflows/report.yml), [`report_verdict.py`](https://github.com/manoochehri/trazo/blob/main/scripts/report_verdict.py)). **Fix:** open the run in the Actions tab and wait if it is still going. If it finished and the status is still pending, ask for a new commit, because a new latest commit gets its own review. UNVERIFIED: that re-running the review clears a pending status that another writer set.

### The merge is refused as risky

**You see** `trazo/verdict` or `trazo/security` named as failure, missing or pending. The change touches a risky path, and the merge workflow needs a reviewer pass and a security pass on the latest commit ([`owner-merge.yml`](https://github.com/manoochehri/trazo/blob/main/.github/workflows/owner-merge.yml)). **Fix:** ask "is #N ok". If the agents list must-fix items, have the engineer fix them, then ask again and start the merge once both show success. A known gap: the two statuses come from the same GitHub account, so the workflow cannot tell them apart ([#366](https://github.com/manoochehri/trazo/issues/366)).

### The drive is halted

The drive is the optional unattended workflow that builds ready issues ([owner setup](install.md#owner-setup)). **You see** `Drive is halted (drive-halt)` in a run and an open issue labeled `drive-halt`. Two failures in a row open it, and the drive stops working and merging until it is closed ([`drive.yml`](https://github.com/manoochehri/trazo/blob/main/.github/workflows/drive.yml)). **Fix:** read the two failed runs, fix the cause or ask the project manager agent to rescope the issue, then close the halt issue yourself. Setting the repository variable `DRIVE_ENABLED` to anything but `true` stops the drive entirely.

### A review failed

**You see** `trazo/verdict` as failure or a list of must-fix items. A review that errors, times out or is cancelled also sets failure, never a silent pending. **Fix:** ask for the must-fix items to be fixed, which pushes a new commit and starts a fresh review, then ask "is #N ok" again. After two failed review rounds the issue is labeled `tier:senior`, and the next attempt runs on the senior engineer ([`senior-engineer.md`](https://github.com/manoochehri/trazo/blob/main/src/overlay/roles/senior-engineer.md)). If the review job itself errored, read its log in the Actions tab and re-run it only for a transient error.

### New hooks do not apply

**You see** a blocked action that still runs after an upgrade, or a new block that does not apply. **Fix:** quit Claude Code and start a new session from the repository root. Claude Code reads hooks and settings when a session starts. UNVERIFIED: that a running session cannot pick up new hooks without a restart; the new session is the safe step either way.

## A note on this repository

This repository manages itself with an installed copy of Trazo, and that copy can be a release behind the newest one. Read `.trazo/VERSION` in any repository to see which copy it runs, and see [how to upgrade](install.md#upgrade).

Next: [how it works](how-it-works.md) explains the loop behind these steps, and [guardrails and limits](guardrails.md) lists what agents may and may not do.
