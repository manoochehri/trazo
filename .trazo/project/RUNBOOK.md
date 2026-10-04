# Runbook

## Local
```
make setup     # deps + git hooks (gitleaks, ruff)
make test
make run
make build     # docker image
make scan      # scan git history for secrets
```

`make scan` scans the full git history in a container. It works from inside a
`.worktrees/*` worktree (it mounts the shared git dir), and it refuses to report
success when it cannot verify the history: it exits non-zero with the reason instead
of printing "no leaks found" after scanning 0 commits.

## Parallel work (git worktrees)
To run multiple engineer sessions concurrently without branch or directory collision:
```bash
# 1. Create a dedicated worktree off fresh origin/main
git fetch origin
git worktree add .worktrees/issue-<N>-<name> -b issue-<N>-<name> origin/main

# 2. Work inside the worktree
cd .worktrees/issue-<N>-<name>
make setup     # fast due to uv's shared cache

# 3. List active worktrees
git worktree list

# 4. Remove after PR merge and clean up local branch
cd ../..
git worktree remove .worktrees/issue-<N>-<name>
git branch -d issue-<N>-<name>

# 5. Prune stale worktree references
git worktree prune
```
Note: Claude Code can also be launched directly inside an isolated worktree via `claude --worktree <name>` (which creates `.claude/worktrees/<name>`). Both `.worktrees/` and `.claude/worktrees/` are ignored in `.gitignore`, and secret protections in `.claude/settings.json` cover both recursively.

## Merge gate: verdict status (owner step, #115)
The reviewer subagent sets commit status `trazo/verdict` on the PR head SHA (`pending` at start, `success` for merge, `failure` for merge after fixes or worse); the security subagent sets `trazo/security` the same way. A new push resets both, so a fix needs a fresh review.

Owner step, once: GitHub repo Settings -> Rules -> Rulesets -> the `protect main` ruleset -> Require status checks to pass -> Add checks -> add `trazo/verdict` (optionally `trazo/security` too). Until the check has reported once it may not appear in the picker; type the name in.

Caveat (#44): agents post as the owner's account, so an agent could set `success` itself. The rule says only the reviewer or security subagent sets it, and the audit trail is the PR review comment that accompanies each status. This is not enforced until #44 gives agent work its own identity.

## Secrets
- Local: copy `.env.example` to `.env` and fill in. `.env` is git-ignored and blocked from Claude Code.
- AWS: `scripts/put_secret.sh <secret-name>` (you run it; it prompts without echoing).

## Deploy
TODO once infra exists: branch → PR → CI → merge to main → merge main into `deploy` → approve in GitHub → deploy workflow.

## Roll back
TODO

## Recurring
- Daily advisor review: TODO (scheduled task / GitHub Action)
- Weekly: dependency PRs from Dependabot

## Teardown
TODO
