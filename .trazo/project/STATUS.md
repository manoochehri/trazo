# Status

**Status:** current

**Updated:** 2026-11-27 by eng (STATUS refresh after v0.4.2)
**Phase / milestone:** v0.4.2 is released. Tags v0.4.0, v0.4.1 and v0.4.2 are published ([release PR](https://github.com/manoochehri/trazo/pull/358)). Next scope is [v0.5.0](https://github.com/manoochehri/trazo/milestone/10).

## Released
- [v0.4.0](https://github.com/manoochehri/trazo/milestone/7): front door merges via `owner-merge.yml`, pinned roles only, drive halt self-clears, engineer Bash hardening.
- [v0.4.1](https://github.com/manoochehri/trazo/milestone/11): reviewer and security set their own status, upgrade removes dropped deny rules, PR template matches the evidence checker, 3-line front door.
- [v0.4.2](https://github.com/manoochehri/trazo/milestone/12): action-first Coordinator, canonical architecture and design index.

## Milestone close pending (owner or PM)
- v0.4.0, v0.4.1 and v0.4.2 have every issue closed (11, 8 and 2 respectively, 0 open), but GitHub still lists them as open. Close them in GitHub.

## Running now
- [PR 361](https://github.com/manoochehri/trazo/pull/361): upgrade of this repo's pinned Trazo install. Checks green; awaiting reviewer verdict.
- [PR 360](https://github.com/manoochehri/trazo/pull/360) (closes #359): bind review gates to current evidence. `trazo/verdict` is failing with "automatic review did not finish".
- Main CI and drive runs are green as of 2026-11-27.

## Blocked / needs a decision
- Owner decision: #320 (GitHub as the lock, P0, needs-decision).
- Owner decision: #311 (Dependabot PRs fail the evidence check, P1, needs-decision). Dependabot PRs [299](https://github.com/manoochehri/trazo/pull/299) and [300](https://github.com/manoochehri/trazo/pull/300) are red for this reason.
- #359 is `needs-pm` and `tier:senior`, with no milestone.

## Next
- [v0.5.0](https://github.com/manoochehri/trazo/milestone/10): 27 open, 0 closed. P0s are #327 (epic; owner out of the routine loop), #320 (decision), #319 (front door does engineer work and cannot merge, `tier:senior`), #280 (decisions persist without the owner, `tier:senior`), #252 (drive workflow identity decision) and #247 (verify drive on a live run).
