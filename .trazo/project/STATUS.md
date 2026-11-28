# Status

**Status:** current

**Updated:** 2026-11-27 by eng (/wrapup after the v0.6.0 release)
**Phase / milestone:** v0.6.0 is tagged and installed in this repository: [milestone](https://github.com/manoochehri/trazo/milestone/13) (0 open issues, still open in GitHub) and [tag v0.6.0](https://github.com/manoochehri/trazo/tree/v0.6.0) (release commit 0fb61f3).

## Running now
- Permissive guard work is done: issues [378](https://github.com/manoochehri/trazo/issues/378) and [379](https://github.com/manoochehri/trazo/issues/379) are closed.
- Design behind it is [ADR 0032](https://github.com/manoochehri/trazo/blob/main/.trazo/project/adr/0032-permissive-by-default.md), which still reads proposed.
- Known guard gaps: [hooks README, "What still gets through"](https://github.com/manoochehri/trazo/blob/main/.trazo/hooks/README.md#what-still-gets-through).

## Blocked / needs a decision
- [#380](https://github.com/manoochehri/trazo/issues/380) stays open until the owner runs the one-time scripts: `scripts/drop_verdict_check.sh`, `scripts/scratch_drop_verdict_test.sh`, `scripts/allow_release_app.py`. Once they have run, the owner is out of routine merges and releases.
- [#377](https://github.com/manoochehri/trazo/issues/377) is open with `needs-decision`: default permissions for reversible repository operations.
- [#280](https://github.com/manoochehri/trazo/issues/280) and [#363](https://github.com/manoochehri/trazo/issues/363) carry `needs-pm`.

## Next
- Owner: decide #377, then run the #380 scripts when ready.
- Open items, linked not copied: [#366](https://github.com/manoochehri/trazo/issues/366) (reviewer App pin and restricted token), [#247](https://github.com/manoochehri/trazo/issues/247) (live drive run), [#280](https://github.com/manoochehri/trazo/issues/280), [#327](https://github.com/manoochehri/trazo/issues/327), [#363](https://github.com/manoochehri/trazo/issues/363).
- Open P0 and P1 issues, live: [P0](https://github.com/manoochehri/trazo/issues?q=is%3Aopen+is%3Aissue+label%3AP0) and [P1](https://github.com/manoochehri/trazo/issues?q=is%3Aopen+is%3Aissue+label%3AP1).
