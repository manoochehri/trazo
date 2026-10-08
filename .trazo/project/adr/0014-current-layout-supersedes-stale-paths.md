# 0014: Current Trazo layout supersedes stale path guidance

**Date:** 2026-10-08  **Status:** proposed — owner review requested on #99

## Context

ADRs 0005–0008 remain the historical record of Trazo's pivot, release model, and adapter
choices. Their measured facts and paths were true when written, but later changes moved the
product into `src/`, made `.trazo/` the installed framework, and added a tested installer and
Codex adapter. Future work needs to distinguish those historical facts from current guidance
without rewriting append-only decisions.

## Decision proposed

Keep the original records unchanged. Apply these current interpretations:

| ADR | Still stands | Historical or superseded guidance |
|---|---|---|
| [0005](0005-pivot-to-trazo.md) | Trazo is a mountable, tool-neutral governance framework; preserve mechanical and judgment rails; the host supplies its own reproducible environment. | The name `semilla`, the product definition as `.trazo/` plus `.claude/`, the template-sync rationale, and file counts/paths measured on commit `b42b6d0` describe the pivot's context, not today's product layout. The product source is now `src/overlay/` plus `src/adapters/`. |
| [0006](0006-release-process.md) | Releases are immutable annotated `vX.Y.Z` tags, cut from an already-pushed default-branch commit; version and changelog are reviewed before tagging. | The installer and ownership map described as future work are implemented. The rule that `make release` checks an existing changelog entry remains current; changelog generation from milestone issues is tracked separately by #130. |
| [0007](0007-claude-is-an-adapter.md) | `.trazo/` is the tool-neutral overlay; Claude's files are an optional adapter; host-owned adapters must be preserved. | The statement that hosts must write their own adapter is superseded by the installed generic `AGENTS.md` and tested Codex adapters. #53's manual-only distribution context is historical; the file-based installer is implemented. |
| [0008](0008-agents-md-is-the-cross-tool-adapter.md) | Keep the governance rules in one tool-neutral source, use native instruction discovery, and do not publish an npm package without a demonstrated need. | `AGENTS.md` is not the only adapter anymore: Claude and Codex have native discovery files too. The claim that there is no install step is historical; installation is provided by `scripts/install.sh`. |

When current implementation and an old path disagree, use the current repository layout and
handbook. Preserve old counts, names, and paths when they are clearly evidence about the
state at the time of the original decision.

## Alternatives considered

- Edit ADRs 0005–0008 in place: rejected because decisions are append-only and those records
  document what was decided at the time.
- Add a record that says only to ignore the old paths: rejected because the record should
  identify what remains binding and what has since changed, per ADR.

## Consequences

Readers can retain the original decision history without treating old file paths or open
follow-up lists as current implementation instructions. Later changes should supersede this
record with another ADR rather than editing it.
