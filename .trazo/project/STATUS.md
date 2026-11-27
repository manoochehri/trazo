# Status

**Status:** current

**Updated:** 2026-11-27 by eng (STATUS refresh after v0.4.2)
**Phase / milestone:** v0.4.2 is released and this repo's install is v0.4.2 ([release PR](https://github.com/manoochehri/trazo/pull/358), [PR 361](https://github.com/manoochehri/trazo/pull/361) merged). Current goal: [v0.5.0](https://github.com/manoochehri/trazo/milestone/10). Milestones [v0.4.0](https://github.com/manoochehri/trazo/milestone/7), [v0.4.1](https://github.com/manoochehri/trazo/milestone/11) and [v0.4.2](https://github.com/manoochehri/trazo/milestone/12) are closed.

## Running now
- [PR 360](https://github.com/manoochehri/trazo/pull/360) (#359): bind review gates to current evidence. `trazo/verdict` is failing.
- Until #364 lands, reviewer and security cannot set their own status, so the owner sets `trazo/verdict` by hand.

## Blocked / needs a decision
- #320 (GitHub as the lock) is P0, `needs-pm`, `tier:senior`.
- #311 (Dependabot PRs fail the evidence check) is an owner decision. Dependabot PRs [299](https://github.com/manoochehri/trazo/pull/299) and [300](https://github.com/manoochehri/trazo/pull/300) have failing `test` checks.
- #280 and other open issues have no milestone: [open issues without a milestone](https://github.com/manoochehri/trazo/issues?q=is%3Aissue+is%3Aopen+no%3Amilestone).

## Next
- [v0.5.0](https://github.com/manoochehri/trazo/milestone/10) is the goal and scope. Its open issues are the source of truth; this file does not list them.
- Priorities: #359, #320, #319, #252, #247, #363, #364.
