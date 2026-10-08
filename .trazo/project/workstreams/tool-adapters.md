# Workstream: tool adapters beyond Claude Code

**Status:** current
**Workstream status:** researching — decision recorded in
[0008](../adr/0008-agents-md-is-the-cross-tool-adapter.md); Codex is now an observed adapter
**Owner:** manoochehri   **Issue(s):** #53, #87, parent #48

## Hypothesis / goal

`.trazo/rules.md` is the single source of truth for how agents work in a repo, and every tool that
reads an adapter pointing at it inherits those rules without a second copy drifting out of sync.

`AGENTS.md` is the leading candidate for that adapter: it is stewarded by the Agentic AI
Foundation under the Linux Foundation, appears in 60k+ public repositories, and is read by Codex,
Amp, Cursor, Gemini CLI, Copilot, Windsurf, Augment, Aider, goose, opencode, Zed, Warp, Factory and
Jules. If a plain root-level `AGENTS.md` containing a pointer to `.trazo/rules.md` is honoured by
those tools as-is, cross-tool reach costs one committed file.

**What is deliberately not decided yet:** the distribution mechanism. Per
[0008](../adr/0008-agents-md-is-the-cross-tool-adapter.md), npm is deferred until the file-based
path is proven in a real mounted repo.

## How it's tested

Not by asserting that a tool *should* read `AGENTS.md` — by mounting Trazo into a scratch repo,
opening it in each tool, and asking a question whose answer can only come from
`.trazo/rules.md`. A rule that names a specific behaviour is used as the probe, since a generic
greeting would be answered from the model rather than from the file.

Per #53: an adapter is not shipped as supported until it has been run and the observation is
recorded here. Tools considered and *not* tested are listed as such, rather than quietly omitted.

## Evidence

| Date | Result | Sample size | Link |
|---|---|---|---|
| 2026-09-30 | `AGENTS.md` is Linux-Foundation-stewarded (Agentic AI Foundation), used in 60k+ repos, nearest-file-wins, nested files supported | 1 standards site | [agents.md](https://agents.md/) |
| 2026-09-30 | No adapter observed working yet. Trazo ships `CLAUDE.md` only; `AGENTS.md`, `.clinerules`, `.cursor/rules`, `.gemini/GEMINI.md` are all absent from this repo | 0 tools run | — |
| 2026-10-08 | A fresh Codex session read `AGENTS.md` and `.trazo/rules.md`, understood a plain-English issue request, and created a branch and test. One sample; it did not prove explicit skill invocation or repeatability. | 1 Codex run | [#156 evidence](https://github.com/manoochehri/trazo/issues/156#issuecomment-6065955792) |

## Open questions

- Does a tool that reads `AGENTS.md` also follow a pointer *inside* it, or must the rules be
  inlined? This is the whole question, and it differs per tool. A pointer is an instruction; an
  import is mechanical. #53 requires the mechanical one, and does not say which tools can do it.
- Do any of these tools already read `.trazo/rules.md` by convention, making an adapter unnecessary?

## Decision

[0008](../adr/0008-agents-md-is-the-cross-tool-adapter.md) — `AGENTS.md` is the cross-tool adapter;
packaging waits for a proven install path. Revisit when a host mounts Trazo by hand and the manual
steps prove error-prone, or when a tool is observed to ignore the pointer.
