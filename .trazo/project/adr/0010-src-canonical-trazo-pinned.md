# 0010: `src/` is canonical, `.trazo/` is the pinned install

**Date:** 2026-10-02  **Status:** accepted

## Context

Trazo is two things that want to live apart: a **framework product** that hosts receive,
and a **harness** that governs its own repository. Today they share one directory, which
produces a specific failure: **editing a rule silently changes the rules governing the
edit.** An agent working under `.trazo/rules.md` rewrites that same file mid-session, so
the constraints it was given and the constraints it is held to are the same mutable object.

The second failure is what hosts experience. Measured on `origin/main` at `47c1e09`
(2026-10-02), re-measured for this record rather than carried forward from the #92 brief,
which predates #103, #105 and #106:

```
files referencing .trazo/          ->  55
total occurrences of .trazo/       ->  258
test files with references         ->  11   (61 occurrences)
  tests/test_trazo_layout.py      ->  17 occurrences on its own
handbook pages with references     ->   6   (30 occurrences)
decision records naming the old
  layout (0005, 0006, 0007, 0008)  ->   4
```

`handbook/guide.md` step 2 tells hosts to "**copy the overlay in**: `.trazo/` from this
repository. It is the whole of it." That instruction is why every host inherits this
repository's own charter, nine decision records about Trazo's internal tooling, and a
`docs/STATUS.md` describing a session that has since ended. It was measured on
[#77](https://github.com/manoochehri/trazo/issues/77) as: 29 files of overlay that a host
came for, and roughly half a repository's worth of Trazo's own diary that they did not.

The `src/` tree already exists (`src/overlay/`, `src/adapters/`,
`src/overlay/templates/`) from [#94](https://github.com/manoochehri/trazo/issues/94), so
the question is not whether to split but which direction the split runs and what the
boundary means.

This record is written **before** the files move. Moving first and recording afterwards
produces folklore: the next agent reads a directory tree and infers intent from it.

## Decision

**`src/` is the canonical source. Everything a host receives lives there and is edited
there.** `.trazo/` is the installed, pinned version that governs work in this repository
and **is never hand-edited**. `.trazo/project/` is this repository's own state — charter
and decision records — and is never overwritten on an upgrade.

```
src/                      canonical source (the product)
  overlay/                governance core, tool-neutral
    rules.md
    ADVISOR.md
    ARCHITECTURE.md
    templates/            blank charter / adr / workstream for hosts
  adapters/
    AGENTS.md             the AGENTS.md adapter
    CLAUDE.md             the CLAUDE.md adapter
    claude/               agents, commands, settings.json

.trazo/                   installed + pinned
  VERSION                 the tag this copy came from
  rules.md, ADVISOR.md, templates/     overwritten on upgrade
  project/                NEVER overwritten
    CHARTER.md
    adr/                   real decision history
```

Three clauses follow, and each of them is the point:
### The cost, stated up front

**After this lands, this repository is governed by frozen `v0.1.0` rules while `src/`
builds the next version.** A rule that fixes a problem cannot be used here until a
version is cut. That is deliberate, and it is the decision's main source of pressure: the
correct response to "just edit `.trazo/` directly" is **no, deliberately**, and that answer
only works if it is written down here. The CI guard that enforces the byte-for-byte
equality is [#96](https://github.com/manoochehri/trazo/issues/96); `fetch-depth: 0` is
already set in `.github/workflows/ci.yml`, so tags are available to it.

## Alternatives considered

- **One folder, no split** — rejected: editing a rule changes the rules governing the edit.
  This is the status quo, and the reason 55 files now reference a path whose meaning is
  contested.
- **Two copies with a sync step** — rejected: a duplicate `rules.md` drifts, reintroducing
  the exact defect [#39](https://github.com/manoochehri/trazo/issues/39) and
  [#53](https://github.com/manoochehri/trazo/issues/53) exist to prevent. The version
  boundary works because there is exactly one editable copy.
- **Move dev state out, keep everything else in place** — rejected: leaves the version
  boundary unstated, so the next agent cannot tell which `.trazo/rules.md` is authoritative.
  `.trazo/project/` exists to state it.
- **Keep the GitHub template, mark or strip what a host should not inherit**
  ([#77](https://github.com/manoochehri/trazo/issues/77) options 1 and 2) — rejected: both
  are maintenance of an install path that then has to be kept correct forever. Retiring the
  path removes the class of problem instead of enumerating files.

## Consequences

**Easier:** a rule change is an ordinary edit to `src/` and ships with a version. A host
receives the framework and not this repository's memory. Upgrading is safe by
construction — managed files are overwritten, `project/` is not.

**Harder, on purpose:** this repository runs on frozen rules until `v0.1.0` ships, so
rule changes are staged rather than felt. Expect the pull request "just edit `.trazo/`" and
treat it as this record says.

**Cost, measured:** 55 files and 258 references to `.trazo/` need repointing — 61 of those
references are in 11 test files, `tests/test_trazo_layout.py` alone accounting for 17.
Records [0005](0005-pivot-to-trazo.md)–[0008](0008-agents-md-is-the-cross-tool-adapter.md)
describe the old layout and are **superseded, not edited**; they are append-only.

**To revisit:** if the pinned install ever needs to be edited to unblock a host, the split
has failed and this record should be superseded rather than worked around.

1. **Never hand-edit `.trazo/`.** Edits go to `src/` and ship with the next version. This
   is the self-governing circularity fix: editing `src/overlay/rules.md` does not change
   the rules governing the current session.
2. **`.trazo/project/` is unmanaged.** Partitioning `.trazo/` into framework files and
   project state is what lets the updater overwrite one without touching the other's
   decision history — the ownership map [0006](0006-release-process.md) left open.
3. **Hosts install from `src/`.** They receive `src/overlay/` plus the adapter for their
   agent, not this repository's state. **The GitHub-template path
   (`gh repo create --template`, the `/generate` button) is retired** — it is the only
   route by which a host inherits Trazo's own charter, ADRs and STATUS. Removing the
   install path resolves [#77](https://github.com/manoochehri/trazo/issues/77) as a
   consequence of the architecture, not as a maintained exception. Tracked as
   [#107](https://github.com/manoochehri/trazo/issues/107).
