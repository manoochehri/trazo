# 0017: Senior tier routing and escalation are accepted

**Date:** 2026-10-13  **Status:** accepted — settles the open points of [0016](0016-senior-engineer-tier.md)

Owner decisions on [#192](https://github.com/manoochehri/trazo/issues/192), given 2026-10-13
after 0016 was proposed. This record accepts them and completes 0016. It does not edit 0016's
decision text; 0016 is superseded only in its status line, and this record is the source for
the answers it left open.

## Context

[0016](0016-senior-engineer-tier.md) set up `eng` as the default and `senior-eng` as an
escalation tier, and left three points for the owner: the escalation count N, whether path or
size routes work to senior automatically, and the label name. Until these were answered the
routing rule could not be applied.

## Decision

- **N = 2.** Escalate to senior after two consecutive failed review rounds, as 0016 proposed.
- **Path and size route to senior automatically.** Issues that touch any of the following are
  labeled `tier:senior` at triage, and the PM may apply it on size or ambiguity grounds:
  - CODEOWNERS and the safety limits it protects
  - `.github/workflows/` (CI and CD workflows)
  - core dependency manifests and locks (for example `pyproject.toml`, `package.json`)
  - security configuration
  - `src/` and `.trazo/` governance schemas, rules and roles (`src/` is canonical, ADR 0010)
  - interface or contract definitions, and cross-workstream integration
  - high architectural uncertainty, such as the baseline contracts in a new milestone
  Path rules are a floor for routing, not a permission. A path match still gets the separate
  security review that `.trazo/rules.md` ("Roles are separated") requires for these paths.
- **Label: `tier:senior`.** It is the only routing field. `status:escalated` is not used. It
  already exists on the repository with the description "Escalated to the senior engineer tier
  (ADR 0016)".
- Everything else in 0016 stands: default is `eng`, senior does not review ordinary PRs,
  reviewer, security and skeptic keep their separate contexts, and the cost share remains
  UNVERIFIED until measured.

## Alternatives considered

- **Path and size left to PM judgment only.** Rejected by the owner. Path rules make the
  routing predictable for the high-risk areas, and they do not depend on the PM noticing.
- **A second label for eng self-escalation.** Rejected. One label keeps "what needs senior" a
  single query.

## Consequences

- Routing is now a rule, so the next step is to make the path match mechanical: a workflow or
  script that applies `tier:senior` when a PR or issue touches a listed path. That is not built
  here. Until it is, the PM applies the label at triage and the reviewer checks it.
- The `/senior-eng` command, the senior role file and the Codex agent are still not shipped.
  They wait for a release install (ADR 0010) and are tracked in
  [#203](https://github.com/manoochehri/trazo/issues/203).
- The measurement that settles the cost share is still owed: count `tier:senior` labels over
  the next 20 closed issues in the milestone.

**Revisit** when the measured escalated share is known, or when the path rules prove wrong in
practice.
