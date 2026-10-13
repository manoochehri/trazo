End a work session.
1. After this session's feature PRs merge, start a separate branch and worktree from the fresh default branch for project-state updates. Rewrite .trazo/project/STATUS.md (replace, don't append; keep under one screen): date, milestone, running now, recently done, blocked/needs-decision, next. This is its only writer. Keep the refresh in its own PR, or one containing only `.trazo/project/` changes; never add it to a feature PR. If feature PRs are still open, record their state in their issues and defer the status refresh until after merges.
2. For each decision made this session, add a numbered file in .trazo/project/adr/ (use the template). Ask me to confirm the wording first.
3. Update any .trazo/project/workstreams/ file whose status or evidence changed, and ARCHITECTURE/RUNBOOK if the system changed.
4. Close finished issues with a one-line comment; open issues for new work; label needs-decision where I must choose.
   Commit the updated project docs, then run `make docs-check-wrapup` if the host declares that target in its Makefile; it checks issue references and freshness after merges. Hosts without that target run their own documented docs check (`make docs-check` if declared). Do not assume hosts receive Trazo's repository-local checker. Amend the commit to fix any drift; per-PR CI runs the host's static checks.
5. **Check that this session's merges actually closed their issues.** For each PR merged into `main` this session, read the issue it says it closes and confirm it is CLOSED. A squash merge drops the PR body's `Closes #N`, so the issue can stay open after a successful merge and the work queue will then report finished work as ready (#61). If one is still open, close it with a one-line comment naming the PR that did it. The check:
   `gh pr list --state merged --search "merged:>=<date>" --json number,title` then for each, `gh pr view <n> --json closingIssuesReferences` and `gh issue view <m> --json state`. A `closingIssuesReferences` entry does **not** prove closure — check the issue's own `state`.
6. Commit on the separate project-state branch, push, and open or update its project-only PR. Report the PR link and anything I need to do. The commit message carries `Closes #<n>` — see `work.md` step 4 for why the PR body alone is not enough.
7. Teardown / cleanup: for any merged feature branch that used an isolated worktree, remove the worktree and clean up the local branch:
   `git worktree remove .worktrees/<name> && git branch -d <name>`
   Run `git worktree prune` to keep worktree tracking clean.
8. Keep the owner-facing wrap-up short and decision-first. Lead with the PR link and
  verdict, then give a concise test result, review-round count, and defects fixed. Include
  at most one command; do not ask the owner to check something or give multi-step instructions.
  Put supporting evidence in the linked PR. Start a fresh session for the
  next task to stay within the token budget instead of extending this one.
