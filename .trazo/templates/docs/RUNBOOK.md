# Runbook

**Status:** current

## Local
TODO: the one command that builds and tests hermetically from a fresh worktree.

## Parallel work (git worktrees)
```bash
git fetch origin && git worktree add .worktrees/<name> -b <name> origin/main
git worktree list
git worktree remove .worktrees/<name> && git branch -D <name>
git worktree prune
```

## Secrets
TODO: where they live and how the owner enters them. Never in git.

## Deploy
TODO

## Roll back
TODO

## Recurring
TODO

## Teardown
TODO
