# AGENTS.md

Instructions for coding agents working in this repository. This part is this repository's own; the block below the line is Trazo's and is installed by `scripts/install.sh`.

## Setup

    make setup      # uv sync, and install the git hooks

## Tests and checks

    make test       # uv run pytest
    make lint       # ruff check + ruff format --check
    make docs-check # validate project-doc status, links, issues and freshness
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
# Trazo adapter for Codex and AGENTS.md readers

This file connects the host's operating instructions to Trazo. Read
`.trazo/rules.md` before governed work. The host's own instructions say how to build and
test its code; Trazo says which roles, approvals, and acceptance gates apply.

Before the first file write, follow the repository instruction file's document map into
referenced rule and decision directories. Skim their indexes or contents and read applicable
current records; a pointer is not a read. If the map does not name them, check project-local
`decisions/`, `rules/`, `adr/`, or equivalent paths. Project layouts vary.

## Route plain-English requests

Use the matching Trazo skill for a request even when the owner does not name a command:

| Request | Skill or role |
|---|---|
| “Work on issue 12”, “fix this”, or another implementation request | `trazo-work` |
| “What is next?”, “catch me up”, or a status request | `trazo-start` |
| “Is PR 15 ready?”, “review this PR”, or “can I merge?” | `trazo-check-pr` |
| “Should we do this?” or a prioritization question | `trazo-pm` |
| “Help” or “what can I do?” | `trazo-menu` |

Codex skills are installed under `.agents/skills/`; role agents are under
`.codex/agents/`. If the matching skill is not available to invoke, read its installed
`SKILL.md` and follow it. Do not answer with a command for the owner to run when the
plain-English request already asks you to do the work.

The skills contain the workflows; this adapter only routes requests to them. Their
instructions and `.trazo/rules.md` remain canonical.
<!-- trazo:end -->
