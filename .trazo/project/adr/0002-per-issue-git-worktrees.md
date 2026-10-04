# 0002: Per-issue git worktrees for isolated parallel sessions

**Date:** 2026-09-28  **Status:** accepted

## Context
When running multiple agent sessions simultaneously, working on branches in the same working directory causes working tree collisions and branch confusion. Additionally, when independent feature branches modify `.template/VERSION` and `CHANGELOG.md`, merge collisions occur upon integration.

## Decision
1. **In-repo worktree isolation:** Each `/work` session creates an isolated git worktree under `.worktrees/issue-<N>-<slug>` branching from fresh `origin/main`.
2. **Path protection:** `.worktrees/` and `.claude/worktrees/` are added to `.gitignore`. Secret read deny rules in `.claude/settings.json` are changed from `./.env` / `./.env.*` to recursive globs (`./**/.env` and `./**/.env.*`) so that `.env` files in worktrees are blocked.
3. **Lifecycle management:** `/start` performs `git worktree prune` and lists stale worktrees; `/wrapup` removes worktrees and local branches post-merge.
4. **Reviewer target check:** Reviewer checks enforce that PRs target base `main`.
5. **Release decoupling:** Version bumps and changelog updates are decoupled from feature PRs and handled on dedicated release workflows to prevent semantic collisions.

## Alternatives considered
- *Sibling directory worktrees:* Rejected because `.claude/settings.json` paths resolve relative to repo root, leaving sibling directories unprotected.
- *Single-directory switching:* Collides when multiple sessions run concurrently.

## Consequences
Parallel engineer sessions can run without contaminating the root working copy. Secret protection applies recursively to all nested worktrees.
