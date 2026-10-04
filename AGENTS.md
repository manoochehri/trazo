# AGENTS.md

Instructions for coding agents working in this repository.

## Setup

    make setup      # uv sync, and install the git hooks

## Tests and checks

    make test       # uv run pytest
    make lint       # ruff check + ruff format --check
    make fmt        # ruff check --fix + ruff format
    make scan       # scripts/scan.sh — secret scan over full git history
    make docs       # mkdocs serve, local preview

CI must pass before merge. Baseline: 132 passed, 2 skipped.

## Conventions

- Branch per change, in its own worktree. Never push to the default branch.
- Any claim that something is shipped, fixed, or working must be backed by a
  command you ran in this session. If you haven't checked, say so.
- Mark anything unverified as unverified.
- Never read, print, log, or commit secrets. The owner enters them with
  `scripts/put_secret.sh`; new config goes in `.env.example` as a placeholder.
- Put `Closes #<n>` in the **commit message**, not only the PR body (#61).
- The published docs are `handbook/`. Build with `mkdocs build --strict`.

## Governance

This repository is governed by Trazo, and Trazo governs itself.

**An agent wants to cut a release.** `make release` validates, tags, and pushes
`vX.Y.Z` — that command is above, and it is everything you need to *run* it.
Trazo is what decides whether you *may*:

- CI must be green. A command existing is not permission to run it.
- A release is a tag, never a branch.
- Never move a tag that already exists — someone may hold it.
- The version bump and the changelog entry go in the same commit as the last
  change in that release.

So: this file tells you **how**. `.trazo/` tells you **whether** — who may
act, what is forbidden, and what evidence is required before a result counts.

Read before doing anything consequential:

- `.trazo/rules.md` — the rules, stated once, tool-neutral
- `.trazo/project/charter/charter.md` — the goal, the budget, the stop rule
- `.trazo/project/adr/` — why, in append-only records
- `.trazo/project/STATUS.md` — current state

Roles are part of that, not part of this file: the rule that a build should
never be its own reviewer is in `.trazo/rules.md`. The concrete mechanism —
which subagent, which command — is whatever tool you are running.

**Where this file and `.trazo/` disagree, `.trazo/` wins.** Proximity is not
authority: a nested instruction does not override a project-level safety rule
because you read it later.

`CLAUDE.md` carries the same rules for a different tool. Both point at
`.trazo/rules.md`; neither is a copy of it.
