# 0008: AGENTS.md is the cross-tool adapter; packaging waits for a working install path

**Date:** 2026-09-30  **Status:** proposed

## Context

[0007](0007-claude-is-an-adapter.md) established `.trazo/rules.md` as the tool-neutral source and
`CLAUDE.md` as one adapter. [0005](0005-pivot-to-trazo.md) and #53 want the same rules to reach tools
that do not read `CLAUDE.md`, and #53's instinct was to ship an npm package so a host could run
`npx trazo`.

Two facts changed the shape of that decision.

**One.** `AGENTS.md` is no longer a convention-in-progress. It is stewarded by the **Agentic AI
Foundation under the Linux Foundation**, used in 60k+ public repositories, and read by Codex
(OpenAI), Amp, Cursor, Gemini CLI, GitHub Copilot, Windsurf, Augment, Aider, goose, opencode, Zed,
Warp, VS Code, Factory, Jules and Junie. A bare root-level `AGENTS.md` with no plugin is the
mechanism, and the spec resolves conflicts by nearest-file-wins and allows nested files per
subproject.

**Two.** The npm package was never the hard part, and it is the *last* part. What a host actually
needs is a mechanical pointer from a file their tool already reads to `.trazo/rules.md`. npm is
only one delivery mechanism for that pointer; a symlink, a committed file, or a line in a setup
script all satisfy the same need. Building the package first means spending the effort on the part
with no proof, and deferring the part that does.

Publishing a package is also not free in the ways that matter here: the name is permanently taken,
every published version is immutable and public, and the first version sets an API. Doing that
before there is a proven install path is spending a permanent cost on an unproven design.

## Decision

**No npm package yet.** Distribution stays file-based, because a committed file is inspectable,
diffable in review, and fixable without a release — the same properties the rest of this overlay
is built on.

**`AGENTS.md` becomes the cross-tool adapter**, alongside `CLAUDE.md`, both pointing at
`.trazo/rules.md`. It is the better default than per-tool files: one widely-read filename beats N
narrow ones, and it is already the thing most of the ecosystem reads.

**npm is deferred until the file-based path is proven**, and revisited when at least one of these
is true:

- a real host repo has mounted Trazo by hand and the manual steps proved error-prone
- a tool has been observed to ignore or mishandle the pointer, so a generator is needed
- the adapter needs to be rewritten or re-run, which a file cannot do for you

## Alternatives considered

- **`npx trazo` now.** Rejected: spends an immutable public name and a first-version API on an
  install path nobody has run end to end, and does not make the rules reach a single extra tool.
- **Per-tool files** (`.clinerules`, `.cursor/rules`, `.gemini/GEMINI.md`). Rejected as the default:
  N files to maintain and keep in sync, for a subset of tools when one widely-read filename covers
  most of the ecosystem. Worth adding later only for a tool *observed* to ignore `AGENTS.md`.
- **Symlinks** (`.clinerules -> .trazo/rules.md`). The right tool for a specific tool that wants its
  own filename, but a poor universal answer: git tracks them, yet checkout behaviour varies by
  platform and some tools resolve through the link in ways that break the nearest-file rule.

## Consequences

Cross-tool reach gets much cheaper, and the "one rules file" invariant from #53 holds by
construction rather than by discipline.

Someone running a non-Claude agent today can copy `.trazo/` and add an `AGENTS.md` that points at
`.trazo/rules.md`, with no package and no install step. What that costs is a manual step, which is
the honest price of not having a proven install path yet.

This does not close #53. It reorders it: the cheap, verifiable part (a working `AGENTS.md`
adapter) comes first, and packaging follows only if the manual path proves inadequate in practice.
Observed behaviour for each tool will be recorded in
`.trazo/workstreams/tool-adapters.md` — per #53, an adapter is not claimed until it has been run.
