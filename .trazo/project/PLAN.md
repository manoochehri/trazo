# Plan

> Milestones mirror GitHub milestones. Update when dates or scope change.
> Target dates below are proposals recorded on #54; the owner moves them, and
> `/wrapup` updates this table when scope or dates change.

| Milestone | Target date | Exit criteria | Status |
|---|---|---|---|
| M0 Kickoff | 2026-09-27 | Charter, plan, repo, CI, secrets setup done | Done |
| M1 `src/` canonical, `.trazo/` pinned (#92) | 2026-10-08 | ADR 0010 recorded (#93), adapters repointed and tests renamed (#96), charter and ADRs moved to `.trazo/project/` (#97), handbook and README updated (#98), stale ADRs superseded (#99), `v0.1.0` cut (#100) | Not started |
| M2 Decision point | 2026-10-15 | Go / pivot / stop, per the charter's stop rule, read against `.trazo/project/reports/` | Not started |

## Risks
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| The #33 / #48 brief is unapproved, so the #92 chain has no owner sign-off | Medium | M1 slips and #77's design stays open | Decide the brief; #93 is a record rather than a change and can proceed either way |
| #44: agents share the owner's identity, so `needs-decision` is unauditable and no guard workflow can fire | High | Every escalation gate is honour-system | Bot account plus a fine-grained PAT (#44) |
| A clone inherits the harness's own charter, ADRs and STATUS | Medium | Host projects start from Trazo's diary as their state | The `src/` template split (#97) plus the decision on #77 |
