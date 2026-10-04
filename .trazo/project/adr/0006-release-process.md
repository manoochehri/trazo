# 0006: A Trazo release is an immutable git tag, cut by `make release`

**Date:** 2026-09-30  **Status:** accepted

## Context
Trazo is consumed by mounting `.trazo/` into another repo. For that to work, "the
latest Trazo" has to name one unambiguous, immutable thing a consumer can resolve.

There was nothing to resolve. The repository had **zero tags**, and `.template/VERSION`
was a hand-edited file. `CONTRIBUTING.md` said "bump `.template/VERSION`" and that was
the whole release process. Three things followed from that:

- A consumer could not pin a version at all. There was no `v0.5.0` to check out.
- Nothing tied a version to a commit, so a stated version was a claim, not a fact.
- An installer could not tell "latest" from "whatever is on the branch now".

A branch cannot serve as the answer: it moves. That is the whole problem. If a host
installs "latest" and the ref shifts underneath it, their `.trazo/` is now a mix of two
releases with no way to tell which.

Measured while writing this ADR: `git tag -l | wc -l` returned `0` on a repository
whose changelog claimed seven released versions.

## Decision
- A release is an **annotated git tag** `vX.Y.Z` on an already-pushed commit.
- `latest` means **the highest release tag**, and nothing else.
- `make release` (`scripts/release.sh`) is the only supported way to cut one. It
  refuses to proceed unless the tree is clean, the branch is the default branch, HEAD
  matches `origin`, the version is `MAJOR.MINOR.PATCH`, the changelog has an entry for
  that version, and the tag does not already exist.
- `.template/VERSION` records the version being cut. It is the input to the script,
  not the thing a consumer pins to.
- A version is cut **after** its change is merged, not as part of the PR that made it.
  The release commit therefore always exists before it is tagged.
- Tags are never moved. A new change is a new version.

## Alternatives considered
- **`AGENTS.md`-style "just use main":** rejected. Mutable, and an installer resolving
  it would silently mix releases.
- **Publishing to a package registry:** rejected for now. Trazo ships rules, docs and
  templates, not code a host imports; a registry adds a dependency and a signing story
  for no benefit at this size. Revisit if an installer ever needs to run code.
- **Tagging from the PR instead of after merge:** rejected. It makes the tag point at a
  commit that CI has not yet gated, and it makes "released" mean "proposed".
- **Letting the script bump the version itself:** rejected. The version and its changelog
  entry belong in the reviewed change, not in an unreviewed commit made at tag time.

## Consequences
A host can now pin `v0.5.0` and get byte-identical files, and an installer can resolve
"latest" mechanically. `make release --dry-run` shows what would happen without tagging.

Two things this deliberately does **not** decide: prerelease versions (`v1.0.0-rc.1`)
and what a consumer resolves when the newest tag is a prerelease. Both need a stated
default, so neither is guessed at here.

Still open and dependent on this landing: an installer that resolves these tags, and
the ownership map that stops an `upgrade` from overwriting a host's `charter.md` or
`adr/`.
