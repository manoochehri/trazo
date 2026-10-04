# 0012: A release is a GitHub milestone

**Date:** 2026-10-03  **Status:** accepted

Decided by the owner, 2026-10-03, on [#119](https://github.com/manoochehri/trazo/issues/119).

## Context

[0006](0006-release-process.md) defines what a release *is* (an immutable tag) but not what
decides that one is due. "A coherent body of work has landed" was a judgement with nowhere to
live: no list of what was in scope, no goal to check it against, and nothing a script could
refuse on. GitHub issues already carry scope; milestones group them.

## Decision

A release is a GitHub milestone named `vX.Y.Z`.

- The milestone description is the release goal; its issues are the scope.
- The tag is cut when the milestone has 0 open issues and CI is green.
- The changelog comes from the milestone's closed issues.
- A Projects board is optional, as a view only; the milestone is the record.
- `make release` refuses to tag while milestone `v<VERSION>` has open issues, and fails
  closed (refuses) if `gh` is unavailable, the lookup fails, or no such milestone exists.

The immutable-tag rule of 0006 is unchanged.

## Alternatives considered
- Keep judging "coherent body of work" by hand: not checkable, drifts toward a release per PR.
- A Projects board as the record: a view over issues, not something a release script can
  query as simply, and optional by nature.
- Fail open when `gh` is missing: "could not check" would read as "nothing open".

## Consequences
Scope is visible and enforced before a tag. Generating the changelog from closed issues is
not yet implemented in `make release`; it is tracked as a follow-up. Releasing now requires
network access and `gh` authentication. Revisit if milestones prove too coarse.
