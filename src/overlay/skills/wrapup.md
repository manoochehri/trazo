End a work session.
1. Rewrite .trazo/project/STATUS.md (replace, don't append; keep under one screen): date, milestone, running now, recently done, blocked/needs-decision, next.
2. For each decision made this session, add a numbered file in .trazo/project/adr/ (use the template). Ask me to confirm the wording first.
3. Update any .trazo/project/workstreams/ file whose status or evidence changed, and ARCHITECTURE/RUNBOOK if the system changed.
4. Close finished issues with a one-line comment; open issues for new work; label needs-decision where I must choose.
   Commit the updated project docs, then run `make docs-check` before pushing/opening the PR; amend the commit to fix any drift. CI runs the same check.
5. **Check that this session's merges actually closed their issues.** For each PR merged into `main` this session, read the issue it says it closes and confirm it is CLOSED. A squash merge drops the PR body's `Closes #N`, so the issue can stay open after a successful merge and the work queue will then report finished work as ready (#61). If one is still open, close it with a one-line comment naming the PR that did it. The check:
   `gh pr list --state merged --search "merged:>=<date>" --json number,title` then for each, `gh pr view <n> --json closingIssuesReferences` and `gh issue view <m> --json state`. A `closingIssuesReferences` entry does **not** prove closure — check the issue's own `state`.
6. Commit on the current branch, push, and open or update the PR. Report the PR link and anything I need to do. The commit message carries `Closes #<n>` — see `work.md` step 4 for why the PR body alone is not enough.
7. Teardown / cleanup: for any merged feature branch that used an isolated worktree, remove the worktree and clean up the local branch:
   `git worktree remove .worktrees/<name> && git branch -d <name>`
   Run `git worktree prune` to keep worktree tracking clean.
8. Keep the owner-facing wrap-up short and decision-first. Lead with the PR link and
  verdict, then give a concise test result, review-round count, and defects fixed. Include
  at most one command; do not ask the owner to check something or give multi-step instructions.
  Put supporting evidence in the linked PR. Start a fresh session for the
  next task instead of extending this one.
