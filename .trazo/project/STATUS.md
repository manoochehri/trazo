# Status

> Replaced (not appended) at the end of every session by `/wrapup`. Keep under one screen.

**Updated:** 2026-10-01 by engineer (Cline)
**Phase / milestone:** the `src/`-is-canonical epic (#92) is filed and waits on the owner's OK of the #33 / #48 brief; #68 is in review.

## Running now
- **#68 → PR #105** — the closing-keyword rule as a standalone first line.
- **#54 → this change** — STATUS and PLAN brought current, `/wrapup` root-caused.

## Recently done
- **#103 merged:** `infra/` deleted — Trazo ships no deploy target.
- **#92–#104 filed:** the `src/` + `.trazo/` split as a P0 chain (#93 → #96 → #97 → #98 → #99 → #100 `v0.1.0`), plus #77 and #104.
- **#68 measured:** the repo's squash settings (`COMMIT_OR_PR_TITLE`, `COMMIT_MESSAGES`) explain why PR-body keywords never reached a landing commit, and why every issue had to be closed by hand.

## Blocked / needs a decision
- **#33 / #48 — the pivot brief** is unapproved; #49–#53 and the #92 chain wait on it.
- **#44 — agents share the owner's identity**, so `needs-decision` is unauditable and no guard workflow can fire; needs a bot account and a fine-grained PAT.
- **#45 — owner review is not enforced** (0 required approvals; CODEOWNERS omits `.claude/` and `CLAUDE.md`). Blocked by #44 — raise the count only after #44, or every PR becomes unmergeable.
- **#42 — this repo's charter** is filled with Trazo's own content; whether that ships to clones is being reworked under #92 / #77.

## Next
1. **#93 (P0)** — ADR 0010: `src/` canonical, `.trazo/` pinned. Every other issue in the epic cites it.
2. **#96 (P0)** — repoint the adapters and fix the tests naming the old layout (after #93).
3. **#77 (P0)** — clones inherit the harness's charter, ADRs and STATUS; the template-clone vector is not covered by #92, question and recommendation posted on the ticket.
