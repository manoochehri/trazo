# 0005: Pivot from a starter template to Trazo, a mountable governance overlay

**Date:** 2026-09-30  **Status:** accepted

## Context
semilla assumes a new project. Most software work happens in repos that already exist, with their own runtime, toolchain and pipeline; forcing a starter pack onto them means deleting most of it first.

Verified scale of this repo at the time of writing, measured on `origin/main` (`b42b6d0`): 86 tracked files. Of those, `src/` is 2 files (`src/app/__init__.py`, `src/app/main.py`) and `infra/` carries three full provider trees (`aws`, `fly`, `gcp`), of which only `aws` has a working bootstrap. The ratio of governance surface to shipped product is the problem in one number: 84 tracked files that are not application code, against 2 that are — **42:1**. Counting by directory on the same commit: `.claude/` 17, `docs/` 15, `handbook/` 9, `.template/` 9, `infra/` 6, `src/` 2.

The owner decided to pivot on 2026-09-30. The full brief is [#33](https://github.com/manoochehri/semilla/issues/33); this record is the part of #48 that must be settled before any file moves.

## Decision
Convert to **Trazo**: a mountable, stack-agnostic governance overlay — `.trazo/` plus `.claude/` — that governs how agents work in any repo, new or existing.

Preserve both the **mechanical rails** (worktree isolation per #0002, role separation, GitHub as the state engine, secrets discipline) **and** the **judgment rails** (charter, budget, success criteria, stop rule, evidence with sample sizes). The judgment rails are the reason to keep going; the mechanical rails are table stakes.

## Alternatives considered
- *Keep the starter-template shape.* Rejected: it only serves day one, and the AWS/Python assumptions have to be removed before any real work starts.
- *Ship `.trazo/specs/` and `.trazo/adr/` only, per the original brief.* Rejected: specs and ADRs answer *what to build*; the charter and stop rule answer *whether to keep going*. Agents remove attrition as a stop mechanism — continuing a doomed project is nearly free and produces plausible commits throughout — so dropping the judgment layer cuts the differentiator and keeps the commodity.
- *Build Trazo in a fresh repo.* Rejected on setup cost: a rename keeps issues, PRs and stars and redirects old URLs, so a derived project's `/template-sync` keeps working, while a clone means re-doing branch protection, CODEOWNERS, labels, Pages, Dependabot and secrets, and repointing `UPSTREAM`.
- *Mandate Docker and uv on mounted repos.* Rejected: the same mistake as the AWS starter, different noun. Trazo keeps Docker and uv for its **own** repo; a mounted repo only has to declare a one-command reproducible environment.

## Binding amendments to the brief in #33
Two clauses in #33 conflict with decisions already accepted here. #33 is a brief, not a decision record; where they disagree, this record wins.

1. **The Reviewer does not merge.** #33 §5.3 has the Reviewer Agent "merges approved PRs, auto-closing linked GitHub issues". That contradicts `CLAUDE.md` rules 2 and 5 and decision 0003: an agent that both approves and merges is the only reviewer of its own work, and it makes the owner's review optional. The Reviewer posts `gh pr review`; the owner merges.
2. **Native GitHub issue dependencies replace the `Blocked by #N` text convention.** #33 §5.1 has the PM managing blockers as issue text. Native `blockedBy` / `blocking` relationships are available in `gh` 2.101.0 and are queryable as data, so a text convention cannot be relied on by a work queue that filters on it.

Also note for whoever implements this: on a squash merge only the commit message lands on `main`, so a closing keyword in a PR body does not close the issue (#61). This decision's own follow-through depends on that being handled.

## Consequences
Trazo becomes stack- and cloud-neutral, usable on existing codebases, and portable across agent tools via thin adapters.

Costs: the repo rename breaks hardcoded URLs — 5 occurrences across 3 tracked files at the time of writing, plus any bookmark not covered by GitHub's redirect — and the derived project must be watched through the transition. `/kickoff` and `infra/` need an explicit decision; that is open on #48 and deliberately not settled here.

Revisit if mounting onto a real existing repo turns out to need more than `.trazo/` and `.claude/`.

## Supersedes nothing
Decisions 0001 (state in the repo), 0002 (per-issue worktrees), 0003 (review tracked in GitHub) and 0004 (public positioning) all stand. This record is numbered 0005 rather than 0004 as [#49](https://github.com/manoochehri/semilla/issues/49) originally specified, because 0004 was taken by [#30](https://github.com/manoochehri/semilla/pull/30) on 2026-09-28.
