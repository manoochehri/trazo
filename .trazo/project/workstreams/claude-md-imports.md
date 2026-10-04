# Workstream: CLAUDE.md `@import` behavior

**Status:** researching — complete, no open questions (feeds the Trazo adapter design)
**Owner:** manoochehri   **Issue(s):** #38, parent #35, feeds #33 §4

## Hypothesis / goal

The proposed Trazo adapter puts a one-line root `CLAUDE.md` in every target repo:

```markdown
@.trazo/rules.md
```

The tool-neutral-core-plus-thin-adapters design rests on that import being **inlined at load**,
not on the agent choosing to read a file. Prose ("read `.trazo/rules.md`") is an instruction an
agent may skip, and costs a tool call when it complies. This workstream verifies the mechanism
before anything is built on it.

### Verdict

**The import mechanism works — but only when the session starts in the directory that contains
`CLAUDE.md`.** From any subdirectory the file still loads and the `@` line is still present, yet
the import is **not expanded**, silently. See [the subdirectory hazard](#the-subdirectory-hazard),
which was not one of #38's five questions and is the most consequential thing found here.

The adapter is viable as specified, with two guards ([Consequences](#consequences-for-the-adapter)).
The fallback #38 named — generate adapters from the core with a CI drift check — is **not needed
for correctness**.

## How it's tested

Runtime answers come from **fresh headless sessions**, not from recollection or documentation.

Each case is a throwaway mini-project with its own root `CLAUDE.md` and an imported file holding
a unique marker token. A fresh session starts in that directory with **all file-reading tools
denied**, and is asked to echo any marker already visible. Two things are then checked in the
JSON transcript:

1. the marker **is** present in the reply, and
2. the transcript contains **no `tool_use` block at all** — the harder half of the claim. A marker
   echoed after a `Read` call would prove nothing.

`case0_control` guards against false positives: marker on disk, no `@` line in `CLAUDE.md`. It
must return `NONE`, and does.

**Environment for every runtime row:** Claude Code **2.1.284**, model **`claude-opus-5`** (taken
from each transcript's `system/init` event), macOS 15 / Darwin 25.5.0, **2026-09-30**.

`claude` is not on `PATH` on this machine; the CLI used is the one bundled with the VSCode
extension:

```sh
CLI=~/.vscode/extensions/anthropic.claude-code-2.1.284-darwin-arm64/resources/native-binary/claude
```

Run once per case, from inside that case's directory:

```sh
# P1 — the marker-enumeration prompt used for most cases
P1='Answer from your existing context only. Do not use any tools. List every token visible in your context that begins with MARKER_ . Reply with only those tokens, comma separated, or exactly NONE if there are none.'

"$CLI" -p "$P1" \
  --disallowed-tools Read Glob Grep Bash Task Edit Write WebFetch WebSearch NotebookEdit \
  --permission-prompts none \
  --output-format stream-json --verbose \
  > case.jsonl 2>case.err < /dev/null
```

Two other prompts were used and are needed to reproduce specific rows. `stream-json` does not
emit a `user` event, so a prompt is **not** recoverable from a transcript — hence verbatim here:

```sh
# P2 — targeted present/absent, used for the depth boundary and the subdirectory re-runs
P2='Answer from existing context only, do not use tools. For each token say present or absent, one per line as TOKEN=present or TOKEN=absent: <tokens>'

# P3 — used to check whether an unexpanded @ line survives as literal text
P3='Answer from existing context only, do not use tools. Look at the project instructions in your context. Does any line there begin with the @ character? If yes, reply with that line copied exactly. If no, reply exactly NOLINE.'
```

A marker counts as inlined only if the transcript contains the token **and** no `{"type":"tool_use"}`
block. Verified by raw grep as well as by a helper script: the only `tool_use` substrings in any
transcript are `parent_tool_use_id` and `server_tool_use`, neither of which is a tool call.

*Reproduction note:* `case1_flat` was run before `< /dev/null` was added, so its `.err` holds a
harmless "no stdin data received in 3s" warning. Every other case used the command exactly as
printed above.

## Evidence

Sample size is 1 session per case except where stated. These are deterministic mechanism checks,
not measurements of a noisy quantity; the control case and the 3-run depth and subdirectory checks
guard the results where a single run could mislead.

Transcripts lived in a **session-scoped scratch directory that is reaped**, so there is no durable
link to cite — which is exactly why the observed reply is quoted verbatim below instead. Re-running
the commands above regenerates all of it.

| Date | Case | Observed reply (verbatim) | Conclusion | Sample size |
|---|---|---|---|---|
| 2026-09-30 | `case0_control` — marker on disk, no `@` line | `NONE` | not visible without an import | 1 |
| 2026-09-30 | `case1_flat` — `@notes.md` | `MARKER_FLAT_ZANZIBAR7741` | inlined, 0 tool calls | 1 |
| 2026-09-30 | `case2_nested` — chain to depth 5 | `MARKER_D1_ALFA7741, MARKER_D2_BRAVO7741, MARKER_D3_CHARLIE7741, MARKER_D4_DELTA7741` | depths 1–4 inlined, 5 absent | 3 |
| 2026-09-30 | `case3_outside` — `@.trazo/rules.md` | `MARKER_TRAZO_KILO7741` | resolves outside `.claude/` | 1 |
| 2026-09-30 | `case4_missing` — `@missing-rules.md` | `MARKER_INLINE_OSCAR7741` | **silent skip**, `is_error: false` | 1 |
| 2026-09-30 | `case5_symlink` — import target is a symlink | `MARKER_SYMLINK_SIERRA7741` | symlink followed | 1 |
| 2026-09-30 | `case6_symlink_claudemd` — `CLAUDE.md` *is* a symlink | `MARKER_LINKEDROOT_TANGO7741` | symlink followed | 1 |
| 2026-09-30 | `case7`/`case9` — cwd is a subdirectory | `MARKER_ROOTINLINE_INDIA7741` only | **file loads, import does not expand** | 3 |
| 2026-09-30 | `case10` — does the unexpanded `@` line survive? (P3) | `@.trazo/rules.md` | yes, survives as literal text | 2 |
| 2026-09-30 | `case12_abs` — absolute-path import from a subdirectory | `MARKER_ABSINLINE_ZULU7741` only | absolute fails the same way | 1 |
| 2026-09-30 | Cline `.clinerules` symlink | n/a — code read | follows symlinks (`stat`) | **source-verified, not runtime-verified** |

### The five questions

**Q1 — Does `@path` in root `CLAUDE.md` inline the file into the opening context?**
**Yes**, when the session starts in the directory containing `CLAUDE.md`.
*(runtime-verified, Claude Code 2.1.284 / `claude-opus-5`, 2026-09-30)*
`case1_flat` echoed its marker with **zero `tool_use` blocks** — checked for explicitly, since the
absence of a `Read` is what distinguishes inlining from the agent reading a file. `case0_control`,
same marker on disk but no `@` line, returned `NONE`. Boundary condition in
[the subdirectory hazard](#the-subdirectory-hazard).

**Q2 — How deep does import nesting go?**
**Four levels of imports below the root file — which matches the documented limit.**
*(runtime-verified, 3 sessions, Claude Code 2.1.284, 2026-09-30)*
Chain `CLAUDE.md → a.md → b.md → c.md → d.md → e.md`: markers in `a`–`d` (depths 1–4) inlined, the
marker in `e.md` (depth 5) **absent**. Reproduced in 3 independent sessions, two using P2 to rule
out the model merely omitting a token it could see.

This is **documented behavior, not emergent**. The Claude Code memory docs state: *"Imported files
can recursively import other files, with a maximum depth of four hops."* Observation and
documentation agree exactly, reading "four hops" as four imported files below the root file (five
files counting the root). *Not a constraint for the adapter, which needs 1 hop.*

**Q3 — Does it work for a file outside `.claude/`, e.g. `.trazo/rules.md`?**
**Yes.** *(runtime-verified, Claude Code 2.1.284, 2026-09-30)*
`case3_outside` used the exact proposed line `@.trazo/rules.md`; marker inlined, 0 tool calls. The
import path is an ordinary path and is not confined to `.claude/`. The docs agree: *"Both relative
and absolute paths are allowed."*

**Q4 — What happens when the imported file is missing?**
**Silent skip. No error, no warning.** *(runtime-verified, Claude Code 2.1.284, 2026-09-30)*
`case4_missing` imported a nonexistent file. The session finished `"subtype":"success"`,
`"is_error":false`, `stderr` empty, and the missing filename appeared **nowhere** in the
transcript. The rest of `CLAUDE.md` still loaded.

Scope of that claim: it describes the **headless startup path**. The CLI does track import
provenance elsewhere — the string `@-imported` is present in the 2.1.284 binary, apparently for
the `/memory` picker (*not runtime-verified*), so an interactive user may have some way to see
import state. Nothing surfaced it at startup, which is the path automation uses.

**This is a fail-open.** See [Consequences](#consequences-for-the-adapter).

**Q5 — Do non-Claude tools follow a symlink (`.clinerules -> .trazo/rules.md`)?**
**Claude Code: yes, runtime-verified. Cline: yes, source-verified only. No other tool tested.**

- *Claude Code* resolves both shapes: an imported file that is a symlink (`case5_symlink`), and a
  root `CLAUDE.md` that is itself a symlink to `.trazo/rules.md` (`case6_symlink_claudemd`). Both
  inlined the marker with 0 tool calls. *(runtime-verified, 2.1.284, 2026-09-30)*
- *Cline 4.1.21* — **source-verified, not runtime-verified.** Cline cannot be driven headlessly, so
  this was read out of its bundled `dist/extension.js` per `CLAUDE.md` rule 3. Its rule-discovery
  function resolves a candidate path with `fs/promises.stat()`:

  ```js
  // discoverFiles, minified as pWt()
  try { if ((await stat(t)).isFile())
          return [{ directoryPath: dirname(t), fileName: basename(t), filePath: t }] }
  catch (e) { if (!k0e(e)) throw e }
  ```

  `stat()` follows symlinks, so a `.clinerules` symlink pointing at a file resolves and loads. The
  candidate list (minified `ASr()`/`OOi()`) is `<workspace>/.clinerules`,
  `<workspace>/.cline/rules` and `<workspace>/AGENTS.md`.

  **Caveat:** the *directory* branch of the same function enumerates with
  `readdir(t, {withFileTypes: true}).filter(i => i.isFile() && …)`, and a `Dirent` for a symlink
  returns `false` from `isFile()`. So **symlinked files placed inside a `.clinerules/` directory are
  silently skipped**, even though a symlinked `.clinerules` *file* works. Symlink the top-level
  path, not individual entries inside a rules directory. One exception: that branch re-checks
  `AGENTS.md` separately with `stat().isFile()`, so a symlinked `AGENTS.md` inside a rules
  directory *is* picked up.

- **Installed is not in use.** Cline was chosen because its loader is readable, not because it is
  the only non-Claude tool present — Continue 2.0.0 is also installed and `~/.cursor` exists. **No
  non-Claude tool is confirmed to be in use in this project.** Nothing here claims anything about
  Cursor, Windsurf, Codex, Continue or Aider; none were tested.

### The subdirectory hazard

Not one of #38's five questions, found while checking Q1's assumptions, and the most important
result here.

Every case above ran with cwd equal to the directory holding `CLAUDE.md`. Real sessions often start
in a subdirectory. Tested with a root `CLAUDE.md` carrying both an inline marker and
`@.trazo/rules.md`, plus a decoy `src/deep/.trazo/rules.md` to reveal cwd-relative resolution:

| cwd | inline marker | imported marker | decoy marker |
|---|---|---|---|
| repo root | present | **present** | — |
| `src` | present | **absent** | absent |
| `src/deep` | present | **absent** | absent |

So from a subdirectory the root `CLAUDE.md` **is** loaded — its inline marker arrives — but the
import **does not expand**, and neither the intended target nor the decoy appears. Reproduced in
3 sessions across two depths.

Also established:

- The unexpanded `@.trazo/rules.md` line **survives verbatim** as literal text (P3, both cwds). The
  adapter therefore degrades to *prose* — precisely the weakness #38 set out to avoid: an
  instruction the agent may skip, costing a tool call when it complies. It does **not** degrade to
  nothing.
- **An absolute path fails identically** (`case12_abs`), so this is not about relative-path
  resolution.
- Neither `--add-dir <repo root>` nor `--dangerously-skip-permissions` changes the outcome.

**Mechanism not established — behavior only.** The docs say imports are *"expanded and loaded into
context at launch alongside the CLAUDE.md that references them"*, that *"Relative paths resolve
relative to the file containing the import, not the working directory"*, and that ancestor
`CLAUDE.md` files *"are loaded at launch"*. Taken together that predicts the import **should**
expand from a subdirectory. It does not. The observed behavior contradicts the documented contract,
in the fail-open direction. The docs' "external import" approval gate (an import resolving outside
the working directory needs one-time approval) is the obvious candidate cause, but the two flags
above did not lift it, so it is **unconfirmed** and recorded here as an open question rather than an
explanation. Worth an upstream bug report.

## Consequences for the adapter

1. **Build it as specified.** A one-line root `CLAUDE.md` containing `@.trazo/rules.md` works,
   costs no tool call, and needs no skippable prose — *for sessions launched at the repo root*,
   which is the normal case for Claude Code and for per-issue worktrees. The **drift** check the
   issue proposed is unnecessary; a **resolution** check is mandatory — see 2 and 3. Do not read
   this point as "no CI work owed".
2. **Guard the fail-open (Q4).** A missing or mistyped target means the agent runs with **no rules
   at all** and nothing reports it: no error, no warning, exit 0. A typo, a `.trazo/` missing from
   a sparse checkout, or a bad merge each degrade silently to an ungoverned agent. Cheapest
   sufficient guard: a pre-commit / CI step asserting every `@` target in `CLAUDE.md` exists — a
   pure filesystem check needing no agent session. Add a sentinel line in `.trazo/rules.md` so the
   check can also confirm content, not just presence.
3. **Do not assume rules load from subdirectories.** Any automation that launches an agent with cwd
   inside the repo gets the rules file *as an unexpanded `@` line* and may ignore it. Mitigations,
   cheapest first: launch every agent from the repo root (document it in the runbook and make the
   wrapper enforce it); or keep rules where subdirectory sessions still load them, e.g.
   `.claude/rules/`, which the docs say loads at launch — **untested here**, and worth verifying
   before relying on it.
4. **Symlinks are safe at the top level only.** `.clinerules -> .trazo/rules.md` is fine for Claude
   Code (verified) and Cline (source-verified). Never symlink individual files inside a rules
   *directory*. And prefer the `@import` over a symlinked `CLAUDE.md` for the adapter: a committed
   symlink needs Administrator or Developer Mode on Windows, and Git checks it out as a plain text
   file unless `core.symlinks` is on, leaving that clone with a one-line `CLAUDE.md` instead of
   instructions.
5. **Depth is a non-issue** — 4 levels available, 1 needed.
6. **`AGENTS.md` may beat a per-tool symlink.** Cline reads `AGENTS.md` from the same `stat()`
   branch, and Claude Code documents reading it too. If the core wants one filename multiple
   vendors already honor with no adapter, that is the stronger candidate. Out of scope for #38 —
   flagged for the adapter issue.

## When to re-verify

The import syntax and the four-hop depth are documented; the Q4 silent skip and the subdirectory
behavior are **observed behavior of one CLI version**, and the subdirectory result contradicts the
docs, so it is the most likely to change. Re-run the probes when:

- **Claude Code is upgraded** past 2.1.284 — re-check Q4 and the subdirectory hazard first. A fix
  to either would let us delete a guard in consequence 2 or 3.
- **Cline is upgraded** past 4.1.21, or any non-Claude tool is actually adopted — then Q5 deserves
  a runtime test for that tool rather than a source read.
- **The adapter changes shape** — a different path, a rules *directory* instead of one file, or
  more than one hop.

Deliberately not automated: a script spawning nested headless sessions cannot run in CI (no `claude`
on `PATH`), spends usage per run, and would flake — it would rot quietly and give false assurance.
The durable check is the filesystem-level assertion in consequence 2.

## Decision

No decision record for the finding itself. Two requirements fall out for the Trazo adapter issue
under #33 §4: the import-resolution assertion (consequence 2) and the launch-from-root rule or a
`.claude/rules/` alternative (consequence 3).
