Start a work session.
1. Run `git worktree prune` and check `git worktree list` for any orphaned or stale worktrees from crashed or interrupted sessions. Report them if found.
2. Read the repository instruction file, `.trazo/rules.md`, `.trazo/project/charter/charter.md`, `.trazo/project/STATUS.md`, `.trazo/project/PLAN.md`, and the latest `.trazo/project/reports/` entry. When you read `.trazo/project/STATUS.md`, check its `**Updated:**` line: if it is more than a few days old, or names a phase that the work queue in step 3 contradicts, say so in one line rather than treating it as current (#54, #109).
3. Report the work queue as these four groups, in this order. Everything below is a native field, so nothing is inferred from label names or body text — get it all in one call:

   ```
   gh issue list --state open --limit 200 --json number,title,labels,blockedBy,parent,subIssuesSummary
   ```

   `blockedBy` is the CLI field name. The GraphQL name for it is `issueDependenciesSummary`, which `gh --json` rejects outright, so do not substitute it.

   1. **Waiting on you** — issues labeled `needs-decision`. The only group that needs the owner. For each: number, title, and the question awaiting an answer.
   2. **Blocked on the PM** — issues labeled `needs-pm`. If any exist, offer to run the `pm` subagent on them.
   3. **Ready to work** — open, not labeled `needs-decision` or `needs-pm`, not itself an `epic` (epics have their own group below), and with no entry in `blockedBy` whose `state` is `OPEN`. A blocker that has closed no longer blocks. Highest priority first — `P0`, then `P1`, then `P2`, then unlabeled — breaking ties by issue number. Say which epic an issue belongs to when it has a `parent`.
   4. **Epics in flight** — issues labeled `epic`, each as `#<n> <title> — <completed>/<total> sub-issues (<percentCompleted>%)` from `subIssuesSummary`.
4. Reply with: current state in 3 lines; the four groups; what you propose to do this session and why; anything that looks wrong or inconsistent.
5. Wait for my OK before changing anything.
