# 0030: A drive halt clears itself once

**Date:** 2026-11-25  **Status:** proposed (becomes accepted when the owner merges this change; it LOOSENS a safety limit and needs owner review)

Amends [0027](0027-drive-spend-cap-and-runaway-guardrails.md), which said "Only a person closes it."
Tracked in [#332](https://github.com/manoochehri/trazo/issues/332); the owner answered "ok" in chat to
building it (quoted on the issue).

## Decision

The `autoclear` job in `drive.yml` may close the one open `drive-halt` issue when ALL hold:

- a pull request merged to the default branch after the halt issue was opened (the fix);
- the latest CI run on the default branch head is completed and `success`;
- no halt was auto-cleared in the last 24 hours.

It comments `Auto-cleared: ...` naming the merged pull request and the green run, adds the
`auto-cleared` label and closes the issue, all as the builder App. Any lookup error, malformed data,
or more than one open halt issue leaves the halt in place. The decision is `scripts/drive_guard.py
autoclear`, a pure function tested on fixtures.

The guard (`halt`) treats a halt closed by anyone but the owner as still halted. The one exception is
a close by the builder App named in the repository variable `DRIVE_BUILDER_APP_LOGIN` that also carries
the `auto-cleared` label and the App's own `Auto-cleared` comment. With the variable unset the
exception never applies and the job does not run.

## Consequences

- This loosens a limit: a first halt no longer waits for the owner when a fix has merged and CI is green.
  A second halt within 24 hours of an auto-clear stays until the owner closes it.
- `UNVERIFIED`: that the closed-event actor for an App token is `<slug>[bot]`, and the CI run lookup
  (`actions/workflows/ci.yml/runs`); #247 checks it live. If the actor differs, the guard keeps halting.
- The owner sets `DRIVE_BUILDER_APP_LOGIN` (for example `name[bot]`); the job also checks it equals the
  App's real slug.
- Changes to `drive.yml` and `drive_guard.py` need owner review (CODEOWNERS) and a security review.
