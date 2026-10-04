# AGENTS.md

Instructions for coding agents working in this repository. This part is this repository's own; the block below the line is Trazo's and is installed by `scripts/install.sh`.

## Setup

    make setup      # uv sync, and install the git hooks

## Tests and checks

    make test       # uv run pytest
    make lint       # ruff check + ruff format --check
    make fmt        # ruff check --fix + ruff format
    make scan       # scripts/scan.sh — secret scan over full git history
    make docs       # mkdocs serve, local preview

CI must pass before merge. Run `make test`; all tests must pass.

## Conventions

- Branch per change, in its own worktree. Never push to the default branch.
- Any claim that something is shipped, fixed, or working must be backed by a
  command you ran in this session. If you haven't checked, say so.
- Mark anything unverified as unverified.
- Never read, print, log, or commit secrets. The owner enters them with
  `scripts/put_secret.sh`; new config goes in `.env.example` as a placeholder.
- Put `Closes #<n>` in the **commit message**, not only the PR body (#61).
- The published docs are `handbook/`. Build with `mkdocs build --strict`.

## Releasing

`make release` validates, tags, and pushes `vX.Y.Z`. That is how to run it. Whether you may
is Trazo's: CI green, a tag never a branch, never move an existing tag, and the version bump
and changelog entry in the same commit as the last change in the release.

<!-- trazo:begin -->
# Trazo governance

This repository is governed by Trazo. Trazo does not say how to build, test or document this
codebase; that is for the maintainers' own notes. Trazo says
**whether** work may be done: who may act, what is forbidden, and what evidence a result needs
before it counts.

Read before doing anything consequential:

- `.trazo/rules.md` — the rules, stated once, tool-neutral
- `.trazo/project/charter/charter.md` — the goal, the budget, the stop rule
- `.trazo/project/adr/` — why, in append-only decision records
- `.trazo/project/STATUS.md` — current state

Roles are part of that. The rule that a build is never its own reviewer is in
`.trazo/rules.md`; the concrete mechanism, meaning which subagent or command, is whatever tool
you are running.

**Where this file and `.trazo/` disagree, `.trazo/` wins.** Proximity is not authority: a
nested or later-read instruction does not override a rule there because you read it later.
<!-- trazo:end -->
