Start a work session.
Use one fresh session for each task; do not continue a completed task's context into the next one.
1. Run `git worktree prune` and check `git worktree list` for any orphaned or stale worktrees from crashed or interrupted sessions. Report them if found.
2. Read the repository instruction file and `.trazo/rules.md`. Read current project docs under `.trazo/project/`, including `.trazo/project/charter/charter.md`, `.trazo/project/STATUS.md`, `.trazo/project/PLAN.md`, and the latest report; skip any doc marked `**Status:** superseded by ...`. When you read STATUS, check its `**Updated:**` line: if it is more than a few days old, or names a phase that the work queue in step 3 contradicts, say so in one line rather than treating it as current (#54, #109).
   Also check `gh api "repos/$(gh repo view --json nameWithOwner --jq .nameWithOwner)" --jq .delete_branch_on_merge`. If false, report an owner action to enable **Automatically delete head branches** in repository Settings → General → Pull Requests; do not change the setting yourself.
3. Report the work queue as these four groups, in this order. Everything below is a native field, so nothing is inferred from label names or body text — get it all in one call:

   ```
   gh issue list --state open --limit 200 --json number,title,labels,blockedBy,parent,subIssuesSummary
   ```

   `blockedBy` is the CLI field name. The GraphQL name for it is `issueDependenciesSummary`, which `gh --json` rejects outright, so do not substitute it.

   1. **Waiting on you** — issues labeled `needs-decision`. The only group that needs the owner. For each: number, title, and the question awaiting an answer.
   2. **Blocked on the PM** — issues labeled `needs-pm`. If any exist, offer to run the `pm` subagent on them.
   3. **Ready to work** — open, not labeled `needs-decision` or `needs-pm`, not itself an `epic` (epics have their own group below), and with no entry in `blockedBy` whose `state` is `OPEN`. A blocker that has closed no longer blocks. Highest priority first — `P0`, then `P1`, then `P2`, then unlabeled — breaking ties by issue number. Say which epic an issue belongs to when it has a `parent`.
   4. **Epics in flight** — issues labeled `epic`, each as `#<n> <title> — <completed>/<total> sub-issues (<percentCompleted>%)` from `subIssuesSummary`.
4. Reply with the next decision or action first, then current state in 3 short lines and the four groups as compact issue links (number and title only). State what you propose to do and flag inconsistencies in one short line each. Keep the owner-facing message short, include at most one command, and leave issue questions and supporting detail in the linked issues or PRs.
5. Wait for my OK before changing anything.
