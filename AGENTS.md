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
# Working in this repository

## Repository

[Brief description of what this repository is and what it does.]

## Development

- Install dependencies: `[command]`
- Build: `[command]`
- Test: `[command]`
- Lint: `[command]`

## Repository structure

- `src/` — application/source code
- `tests/` — tests
- `.trazo/` — Trazo governance and durable agentic project state

## Repository conventions

- [Important coding or architectural convention]
- [Generated files and how they are updated]
- [Important directory-specific conventions]
- [Other repository-specific gotchas]

## Project context

Before making substantial changes, consult the relevant project documentation.

- `.trazo/project/STATUS.md` — current project status
- `.trazo/project/charter/` — project charter
- `.trazo/project/adr/` — architectural decisions
- `.trazo/project/workstreams/` — active workstreams
- `.trazo/plans/` — current or historical plans

Not every project will use all of these paths.

## Agent governance

This repository uses Trazo for agent governance and durable agentic project state.

Before undertaking governed work, read:

`.trazo/rules.md`

Trazo defines roles, skills, plans, workstreams, approvals, evidence requirements, and other constraints on agent activity. Standard roles are defined in `.trazo/roles/`.

Do not infer authority from this file. Repository instructions describe how to work in the repository; Trazo defines the governance of agentic work.

## Important

Do not duplicate Trazo rules, roles, skills, plans, or project state in this file.

Keep repository-specific instructions here and Trazo-specific governance and state under `.trazo/`.
<!-- trazo:end -->
