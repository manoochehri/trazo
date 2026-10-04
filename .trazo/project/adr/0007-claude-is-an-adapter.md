# 0007: `.claude/` is an optional adapter, not part of the overlay

**Date:** 2026-09-30  **Status:** accepted — supersedes the "`.trazo/` plus `.claude/`" clause of [0005](0005-pivot-to-trazo.md)

## Context
[0005](0005-pivot-to-trazo.md) defined the product as "a mountable, stack-agnostic governance overlay — **`.trazo/` plus `.claude/`**". That clause is wrong, and it was wrong in the one sentence that defines Trazo.

It contradicts 0005's own mount-time contract, two lines later: *"Do **not** mandate a particular tool for a mounted repo — that mistake was made once already, with a cloud provider, and it is why this contract is phrased as a capability rather than a product."* Naming `.claude/` as part of the overlay **is** mandating a tool, in the sentence that says not to.

Measured on `origin/main` at `7418002`: `.trazo/` is 12 files, and **not one names a tool** — every hit for "Claude" in it is a historical record (ADRs 0002/0004/0005, the workstream that studied Claude Code's import behaviour, and the charter's budget line). `.claude/` is 16 files in Claude Code's own format: YAML frontmatter plus `Read, Grep, Glob, Bash` grants. On another tool those are portable markdown to re-wrap, not a dependency.

The error propagated rather than being invented twice. Both `handbook/index.md` and `handbook/guide.md` say to copy "`.trazo/` and `.claude/`". A Cline or Cursor user reading that either installs files they do not need, or concludes Trazo does not support their tool. **Both readings are wrong, and the docs are the reason they would think so.**

## Decision
- **`.trazo/` is the overlay.** It is tool-neutral and travels.
- **`.claude/` is one adapter among several.** It is what Claude Code needs and nothing more. A host on another agent writes its own adapter against the same `.trazo/rules.md`.
- **Trazo mandates no adapter for a mounted repo.** A host with no agent gets the overlay and decides later.
- **An existing adapter is merged, never overwritten.** A repo that already has `.claude/` or a `CLAUDE.md` keeps its own; the mount instructions print what to add and let the owner place it.

### `AGENTS.md` is a different thing
Worth recording separately, because it is easy to confuse. `AGENTS.md` **describes a codebase** — build and test commands, style, gotchas. It is a Linux-Foundation-stewarded plain-markdown file read natively by ~25 tools, and it is rewritten as the project changes.

Trazo **governs the work done on that codebase** — roles, safety limits that are human-only, append-only decision records, a stop rule. It is not rewritten; it accumulates.

They are not alternatives and neither replaces the other. A mounted repo wants both, written by different parties. Note also that the `@` in `@AGENTS.md` is **not** part of that standard — it is Claude Code's import syntax, the same shim `CLAUDE.md` uses for `.trazo/rules.md` ([#38](https://github.com/manoochehri/trazo/issues/38) verified it). The portable part of the standard is nested files, nearest-wins.

## Alternatives considered
- **Edit 0005 in place:** rejected. ADRs are append-only (#0000); rewriting a record to match a later change makes it false (#49). This record supersedes the clause instead.
- **Ship `AGENTS.md` as a Trazo file:** rejected for now. The host owns it. Trazo may *offer* to create one when absent and must never overwrite one — the same rule as any adapter.
- **Say "copy `.claude/` only if you use Claude Code" and stop there:** rejected as insufficient. It leaves the reader to guess what to do instead, and the point of the overlay is that there is a rules file and the adapter is the small part.

## Consequences
`handbook/index.md` and `handbook/guide.md` now say to copy `.trazo/` and add an adapter for the agent actually in use, with `.claude/` named as the Claude Code case rather than a requirement. A test asserts that phrasing, so the universal claim cannot return.

Still open, and dependent on this landing: [issue #53](https://github.com/manoochehri/trazo/issues/53), an installer that resolves the release tag added by [0006](0006-release-process.md) and writes the right adapter for the agent it detects.
