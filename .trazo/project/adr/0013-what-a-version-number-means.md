# 0013: What a version number means

**Date:** 2026-10-05  **Status:** accepted

Decided by the owner, 2026-10-05, on #153.

## Context

0006, 0009 and 0012 define what a release is (an immutable `MAJOR.MINOR.PATCH` tag), when one
is due (its milestone has 0 open issues), and exclude prereleases. None says which part of the
number to bump, so the next milestone's name is a guess. Hosts pin to a tag, so the number is
the only signal a host gets about whether an upgrade changes anything for them.

## Decision

The bump is chosen from the milestone's scope when the milestone is created:
- **PATCH** (`0.1.0` → `0.1.1`): bug and doc fixes only; nothing a host receives changes how its agents behave.
- **MINOR** (`0.1.x` → `0.2.0`): adds or changes anything a host receives that changes behavior — a rule in `rules.md`, a role, a command, an agent file, installer behavior.
- **MAJOR**: stays `0` until the owner declares the overlay stable. Under `0.x`, a MINOR may break; the changelog says how.

If a behavior-changing issue joins a PATCH milestone, the milestone is renamed to the next MINOR before tagging. The milestone description states which kind it is.

## Alternatives considered
- Bump the same part every release: the number stops telling a host anything.
- Date-based versions: conflicts with 0009's `MAJOR.MINOR.PATCH` rule and `release.sh`.

## Consequences
A host can tell from the number alone whether an upgrade changes agent behavior. Everything planned before the first tag ships in v0.1.0; the bump rule applies from the next milestone on. Revisit at 1.0.
