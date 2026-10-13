# Architecture contract

**Status:** current

This is Trazo's own architecture contract, filled in the way `/kickoff` fills it for a host.
It points at documents this repository already has and does not copy them.

## Design intent

- Why the system is shaped this way: [`.trazo/project/adr/`](adr/) and
  [`.trazo/ARCHITECTURE.md`](../ARCHITECTURE.md). ADR 0010 (`src/` is canonical, `.trazo/` is
  the pinned install) is the decision that governs where a change is made.

## Component boundaries

| Component | Owns | Must not |
|---|---|---|
| `src/overlay/` | Tool-neutral rules, advisor, templates, skills shipped to hosts | Be edited through the installed copy in `.trazo/` |
| `src/adapters/` | Per-tool adapters (Claude, AGENTS.md) | Carry rules of their own; they import `rules.md` |
| `scripts/install.sh` | Installing and upgrading a pinned `src/` tag into a host | Overwrite `.trazo/project/` |
| `.trazo/project/` | This repository's own state | Ship to hosts |

## Versioned interfaces

| Interface | Version | Defined in |
|---|---|---|
| Installer (`scripts/install.sh`) | Release tag (`.trazo/VERSION`) | `scripts/install.sh` |
| Architecture contract template | Release tag | `src/overlay/templates/docs/ARCHITECTURE_CONTRACT.md` |

## Acceptance commands

- Build: none. Trazo has no build step.
- Test: `make test`
- Lint: `make lint`
- Docs: `make docs-check`

## Reference scenario

| Check | Label | Command | Result | Date or commit |
|---|---|---|---|---|
| Fresh install into an empty host creates `.trazo/project/ARCHITECTURE_CONTRACT.md` | proposed | `uv run pytest tests/test_install.py -k architecture_contract` | not run against this file | n/a |
| `make docs-check` passes on this branch | executed | `make docs-check` | project docs are current | this PR's head, before merge |
