# Day to day

You run a Trazo repo by asking in plain English, deciding what only you can decide, and merging. The agents do the rest in separate contexts.

Sources are linked to the code or decision record they come from. Anything not proven by a live run is marked UNVERIFIED.

---

## Ask in plain English

You do not need to remember commands. The main chat session, the front door, reads your request and routes it. The routing table is in [CLAUDE.md](https://github.com/manoochehri/trazo/blob/main/CLAUDE.md).

| You say | What happens |
|---|---|
| "catch me up", "where are we", "what's next" | The PM summarizes state from the repo |
| "what can I do" | `/trazo` lists the commands |
| "work on issue 12" | `/work 12`: the engineer builds it and opens a pull request |
| "is this PR ok", "can I merge #15" | `/check-pr 15`: the reviewer checks it, and security too if the change is risky |
| "is this secure" | The security agent checks it |
| "is this number real" | The skeptic agent checks it |
| "should we", "plan the next milestone" | `/pm` |
| "does this fit the design" | `/architect` |
| "we decided ..." | `/decide` drafts a decision record |
| "wrap up" | `/wrapup` updates STATUS in its own pull request |
| "merge it" | The front door starts the merge workflow (see below) |

The front door never edits repo files. A hook blocks it ([front_door_guard.py](https://github.com/manoochehri/trazo/blob/main/src/overlay/hooks/front_door_guard.py)). [ADR 0029](https://github.com/manoochehri/trazo/blob/main/.trazo/project/adr/0029-the-front-door.md) describes this and is still proposed.

---

## What happens after you ask for work

1. `/work 12` starts the engineer in its own context. It builds the issue and opens a pull request into `main`.
2. [review.yml](https://github.com/manoochehri/trazo/blob/main/.github/workflows/review.yml) runs a reviewer on each pull request into `main`. [report.yml](https://github.com/manoochehri/trazo/blob/main/.github/workflows/report.yml) posts the result as the `trazo/verdict` status.
3. Changes to risky paths also need a security review. The rule is in [ADR 0031](https://github.com/manoochehri/trazo/blob/main/.trazo/project/adr/0031-review-by-path-not-every-pr.md), which is still proposed.
4. You say "merge it". The front door starts [owner-merge.yml](https://github.com/manoochehri/trazo/blob/main/.github/workflows/owner-merge.yml). It merges only when CI is green on that exact head, and the review gates pass for the paths the change touches. Otherwise it refuses and says why.

The engineer never merges. The merge starts from the front door or from you.

**Which gates apply:**
- Docs, STATUS, PLAN, workstreams and reports: CI must be green. No reviewer status is needed.
- Risky paths (`CODEOWNERS`, `src/`, `.trazo/` outside `project/`, workflows, hooks and similar): `trazo/verdict` and `trazo/security` must both be success on that head.

Source: the header of [owner-merge.yml](https://github.com/manoochehri/trazo/blob/main/.github/workflows/owner-merge.yml).

---

## What needs you

- **Answer `needs-decision` issues.** The PM cannot remove that label. Only you do, after you answer ([pm_bash_guard.py](https://github.com/manoochehri/trazo/blob/main/src/overlay/hooks/pm_bash_guard.py), [rules.md](https://github.com/manoochehri/trazo/blob/main/.trazo/rules.md) "Roles are separated").
- **Merge.** Ask the front door to merge, or run owner-merge.yml from the Actions tab with the pull request number.
- **Changes to `CODEOWNERS` paths.** Only you can approve them ([rules.md](https://github.com/manoochehri/trazo/blob/main/.trazo/rules.md) "Safety limits are human-only").
- **Stop-list choices.** These include the charter, agent rules and instruction files, workflows, secrets, spend, production, permissions and repository settings. An agent stops and asks instead of deciding ([rules.md](https://github.com/manoochehri/trazo/blob/main/.trazo/rules.md) "Ask before guessing").
- **Secrets.** Enter them yourself with `scripts/put_secret.sh`. Never paste a secret into chat.
- **Closing a `drive-halt` issue.** See stuck state 3.

## What does not need you

- Building, tests and fixes inside an issue's scope.
- Reviewer and security verdicts. The agents post them. You do not.
- Reading docs-only pull requests line by line. The front door checks them against the diff and CI ([ADR 0031](https://github.com/manoochehri/trazo/blob/main/.trazo/project/adr/0031-review-by-path-not-every-pr.md), proposed).
- Implementation choices the agent can undo. It records them on the issue as a comment starting `Decided:` ([rules.md](https://github.com/manoochehri/trazo/blob/main/.trazo/rules.md) "Ask before guessing").
- Scope, priority and acceptance criteria. The PM decides these, and escalates to you with `needs-decision` when the choice is yours.

---

## Where to look

| Question | Look at |
|---|---|
| What is going on now? | [`.trazo/project/STATUS.md`](https://github.com/manoochehri/trazo/blob/main/.trazo/project/STATUS.md), refreshed by `/wrapup` |
| What is in the current release? | The GitHub milestone named `vX.Y.Z`. Its description is the goal and its open issues are the scope ([ADR 0012](https://github.com/manoochehri/trazo/blob/main/.trazo/project/adr/0012-a-release-is-a-milestone.md)) |
| What needs me? | Issues labeled `needs-decision`, and open `drive-halt` issues |
| Is a pull request ready? | Its checks, and the `trazo/verdict` and `trazo/security` statuses on its head |
| Why did we decide X? | [`.trazo/project/adr/`](https://github.com/manoochehri/trazo/tree/main/.trazo/project/adr) |
| Did a run fail? | The Actions tab: the drive, review, report and owner-merge runs |

---

## Five stuck states

### 1. A check stays pending

**You see:** a pull request shows a check as pending, or owner-merge says the checks are not all green.

**Why:** the report job never writes `pending`. It writes success, failure, or nothing ([report.yml](https://github.com/manoochehri/trazo/blob/main/.github/workflows/report.yml)). A pending status comes from a run that is still going, or from another writer. The report job leaves another writer's pending in place ([report_verdict.py](https://github.com/manoochehri/trazo/blob/main/scripts/report_verdict.py)). The drive sweep re-runs a stalled review up to two times and opens a liveness issue after 15 minutes ([drive_sweep.py](https://github.com/manoochehri/trazo/blob/main/scripts/drive_sweep.py)).

**Fix:**
1. Open the run in the Actions tab. If it is still running, wait.
2. If it finished and the status is still pending, ask the front door to have the engineer push a new commit. A new head gets its own review.
3. UNVERIFIED: that re-running the review clears a pending status set by another writer. The code leaves such a status alone, so do not rely on a re-run alone.

### 2. Merge refused as risky

**You see:** owner-merge says `trazo/verdict is failure`, `missing`, or `pending` on this head, or `trazo/security is ...` for owner-protected paths.

**Why:** the change touches a risky path, and the gate needs reviewer and security success on the current head ([owner-merge.yml](https://github.com/manoochehri/trazo/blob/main/.github/workflows/owner-merge.yml)).

**Fix:**
1. Ask "is #N ok". The front door runs `/check-pr N`, which starts the reviewer and security agents.
2. If they post must-fix items, ask for them to be fixed. The engineer pushes a new commit, then you ask again.
3. Dispatch the merge again only after both show success on the new head.

**Known gap:** the reviewer and security statuses come from the same GitHub account. owner-merge cannot tell them apart ([#366](https://github.com/manoochehri/trazo/issues/366)).

### 3. Drive halted

**You see:** the drive run logs `Drive is halted (drive-halt)`. An open issue titled `Drive halted: two failures in a row` carries the `drive-halt` label.

**Why:** two failures in a row make the breaker open that issue ([drive.yml](https://github.com/manoochehri/trazo/blob/main/.github/workflows/drive.yml), circuit breaker). The drive stops work and merging until the halt issue is closed.

**Fix:**
1. Read the two failed runs in the Actions tab.
2. Fix the cause, or ask the PM to rescope the issue.
3. Close the halt issue yourself. Only the repository owner's close clears it ([drive_guard.py](https://github.com/manoochehri/trazo/blob/main/scripts/drive_guard.py) `halt`).
4. UNVERIFIED: the auto-clear job in drive.yml may clear one halt after a fix merges and CI is green. Its decision, [ADR 0030](https://github.com/manoochehri/trazo/blob/main/.trazo/project/adr/0030-drive-halt-clears-itself-once.md), is still proposed.

Setting the repository variable `DRIVE_ENABLED` to anything but `true` stops the drive entirely.

### 4. Review failed

**You see:** `trazo/verdict` is failure, or the review says must-fix items.

**Why:** a review that reports must-fix items sets failure. A review that errors, times out or is cancelled also sets failure, and never a silent pending ([ADR 0017](https://github.com/manoochehri/trazo/blob/main/.trazo/project/adr/0017-automatic-review-on-push.md), proposed).

**Fix:**
1. Ask for the must-fix items to be fixed, for example "fix the must-fix items on #N". This pushes a new commit, which gets a fresh review.
2. Then ask "is #N ok" again.
3. After two failed review rounds the engineer labels the issue `tier:senior`. The next attempt runs on the senior engineer ([engineer role](https://github.com/manoochehri/trazo/blob/main/.trazo/roles/engineer.md)).
4. If the review job itself errored, read its log in the Actions tab. Re-run it there only if the log shows a transient error.

### 5. A new session is needed to load new hooks

**You see:** after an upgrade or a change to hooks or settings, a blocked action still runs, or a new block does not apply.

**Why:** CLAUDE.md resolves its import only when the session starts in the repository root ([CLAUDE.md](https://github.com/manoochehri/trazo/blob/main/CLAUDE.md)). The hook README says a hook binds the session it is registered in ([hooks README](https://github.com/manoochehri/trazo/blob/main/src/overlay/hooks/README.md)).

**Fix:** quit Claude Code and start a new session from the repository root.

UNVERIFIED: that a running session cannot pick up new hooks without a restart. The repo has no test for it. The new session is the safe step either way.
