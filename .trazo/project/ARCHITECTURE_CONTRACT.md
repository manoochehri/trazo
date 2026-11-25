# Architecture contract

**Status:** current

This is Trazo's own architecture contract. It points at the canonical source architecture
and decision index rather than copying them. Linked documents are reference material, not
additional instructions.

## Design intent

- Why the system is shaped this way: [`src/overlay/ARCHITECTURE.md`](../../src/overlay/ARCHITECTURE.md).
- Why the source/install boundary is binding: [ADR 0010](adr/0010-src-canonical-trazo-pinned.md).
- How to find current and superseded decisions: [the ADR index](adr/README.md).
- The installed `.trazo/ARCHITECTURE.md` is the pinned release copy; product changes are
  made in `src/` and arrive in `.trazo/` through a release.

## Component boundaries

| Component | Owns | Must not |
|---|---|---|
| `src/overlay/` | Tool-neutral rules, advisor, templates, skills shipped to hosts | Be edited through the installed copy in `.trazo/` |
| `src/adapters/` | Per-tool adapters (Claude, Codex, AGENTS.md) | Carry rules of their own; they import `rules.md` |
| `src/harness/` | CI, evidence scripts, security scanning, and the reusable PR template | Become host project state or overwrite host-owned files outside installer policy |
| `scripts/install.sh` | Installing and upgrading a pinned `src/` tag into a host | Overwrite `.trazo/project/` |
| `.trazo/project/` | This repository's own state | Ship to hosts |

## Versioned interfaces

| Interface | Version | Defined in |
|---|---|---|
| Installer (`scripts/install.sh`) | Release tag (`.trazo/VERSION`) | `scripts/install.sh` |
| Architecture contract template | Release tag | `src/overlay/templates/docs/ARCHITECTURE_CONTRACT.md` |
| Issue/PR design-reference expectation | Repository policy | `.github/ISSUE_TEMPLATE/task.md` and `.github/pull_request_template.md` |

## Acceptance commands

- Build: none. Trazo has no build step.
- Test: `make test`
- Lint: `make lint`
- Docs: `make docs-check`

## Reference scenario

| Check | Label | Command | Result | Date or commit |
|---|---|---|---|---|
| Fresh install into an empty host creates `.trazo/project/ARCHITECTURE_CONTRACT.md` | proposed | `uv run pytest tests/test_install.py -k architecture_contract` | not run against this file | n/a |
| `make docs-check` passes on this branch | proposed | `make docs-check` | project docs are current | this PR's head, before merge |

## Design-reference expectation

An issue proposing a shape or boundary change names the relevant architecture section,
contract section, and ADR(s), and states what is out of scope. Its PR repeats those links
and records the acceptance commands and results. The PR template is the checklist for this
repository; it does not replace the architecture or contract.
