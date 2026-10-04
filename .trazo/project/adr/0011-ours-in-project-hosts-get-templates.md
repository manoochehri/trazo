# 0011: Ours lives in `.trazo/project/`; the host's is a template under `src/`

**Date:** 2026-10-03  **Status:** accepted

## Context

[0010](0010-src-canonical-trazo-pinned.md) says `.trazo/project/` is "this repository's own
state" and lists charter and decision records. It left `STATUS.md`, `PLAN.md`, `RUNBOOK.md`,
`SKEPTIC_BAR.md` and `reports/` in `docs/`, on the strength of a test comment
(`KEPT_IN_DOCS`: "operational and session state, not design records"), a distinction made by
[0005](0005-pivot-to-trazo.md). That left a clone inheriting a `STATUS.md` about Trazo's own
session, the failure [#77](https://github.com/manoochehri/trazo/issues/77) exists to remove,
one directory over.

0005's question was "design record or operational state". 0010's is "ours or the host's".
The second wins, because `docs/` no longer ships to anyone: hosts install from `src/`.

## Decision

**Ours lives in `.trazo/project/`; the host's is a template under `src/overlay/templates/`.**

- `.trazo/project/` holds this repository's `charter/charter.md`, `adr/`, `workstreams/`,
  `STATUS.md`, `PLAN.md`, `RUNBOOK.md`, `SKEPTIC_BAR.md` and `reports/`. It is never
  overwritten on upgrade and never shipped.
- `src/overlay/templates/` ships blank `charter.md`, `adr.md`, `workstream.md` and
  `docs/` (STATUS, PLAN, RUNBOOK, SKEPTIC_BAR, `reports/`). `/kickoff` copies them into the
  host's own `.trazo/project/`.
- `docs/` is empty in this repository and is the host's to use.
- Because the commands and rules are one file shared byte for byte between `src/` and the
  installed copy, they name one location for project state, `.trazo/project/`, for Trazo and
  for hosts alike. A host's STATUS is therefore at `.trazo/project/STATUS.md`, not `docs/`.
  The template directory is named `docs/` because it holds the former `docs/` scaffold, not
  because hosts install it there.

`KEPT_IN_DOCS` in `tests/test_trazo_layout.py` is replaced by tests asserting this split. The
charter keeps its filename (`charter/charter.md`), not the `CHARTER.md` sketched in 0010, so
the CODEOWNERS rule is a directory, `/.trazo/project/charter/`.

## Alternatives considered

- **Leave them in `docs/`.** Rejected: contradicts 0010 and keeps #77's failure.
- **Hosts keep state in `docs/`, ours in `.trazo/project/`.** Rejected: the shared commands
  and rules cannot name two paths, and the installed copy must equal `src/` byte for byte
  ([#96](https://github.com/manoochehri/trazo/issues/96)).

## Consequences

Easier: one path for state everywhere; upgrades cannot touch it. Harder: the owner must add
`/.trazo/project/charter/` to CODEOWNERS (owner-only file) and update the `docs-updated` gate
in `ci.yml`, which still greps for `docs/RUNBOOK.md`. Until then the charter is unprotected
and that gate watches a path that no longer exists.

0001, 0005 and 0009 describe the old paths and are history, not edited.
