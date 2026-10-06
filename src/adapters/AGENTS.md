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
