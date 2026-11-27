# 0031: Reviewer and security are required for risky paths, not every pull request

**Date:** 2026-11-27  **Status:** proposed (becomes accepted when the owner merges this change; it edits `rules.md`)

Narrowed after the security review of PR #368. Raised by the owner on 2026-11-27 and tracked in [#367](https://github.com/manoochehri/trazo/issues/367).
Supersedes the routing clause of [0029](0029-the-front-door.md): "routes every pull request to the
reviewer". Everything else in 0029 stands.

## Context

[0029](0029-the-front-door.md) has the main session route every pull request to the reviewer. Each
subagent review spends the charter's AI budget, and for a documentation-only or
`.trazo/project/` state change the review adds cost and delay without a matching risk. The owner's
words on #367: "not everything needs to be reviewed, you know that. there should be discretion",
then "i approve the change".

## Decision

The reviewer and security subagents are required when a pull request changes a risky path. Risky
means any path in `CODEOWNERS` or in the sensitive-path list of `scripts/report_verdict.py` (the
existing classifier, reused by name so the two cannot drift), plus the readable summary: hooks,
workflows, settings or permissions, dependencies, rulesets, secrets, rules, role and
agent-instruction files, `.claude/`, `.codex/`, `.agents/`, `.trazo/` outside `project/`, `src/`,
scripts run by workflows, hooks or the build (`docs_check.py`, `report_verdict.py`, `release.sh`,
`install.sh`), `Makefile`, `pyproject.toml`, `.gitleaks.toml`, and under `.trazo/project/` the
`charter/`, `adr/`, `SKEPTIC_BAR.md` and `ARCHITECTURE_CONTRACT.md`.

Only ordinary state and documentation (STATUS, PLAN, RUNBOOK, workstreams, reports, plain docs) is
exempt; the Coordinator checks such a pull request against the diff and CI with no subagent, and
may still send any pull request to review. A diff touching both kinds follows the risky rule.
Tie-breaks: both old and new names of a rename count, a symlink is classified by its target, and
anything unclassifiable is risky (fail closed).

Unchanged: the skeptic rule, "Roles are separated" for the risky paths, and every owner-only limit
(`CODEOWNERS`, the stop list, secrets, the charter).

## Alternatives considered
- Keep review on every pull request: safe but spends budget on changes with no risk surface.
- Let the author decide per PR: the author would be the only check; the path list is decided by the diff, not the author.

## Consequences

Easier: cheaper, faster docs and state pull requests.
Harder: the Coordinator carries a judgment on the diff, so it must apply the path list literally.
Open: `owner-merge.yml` still requires `trazo/verdict` to be success on every PR (a workflow, on the
stop list). Until the owner decides how a no-subagent PR obtains that status, docs-only PRs still
need a verdict to merge through that workflow. This record changes no workflow.
Revisit if a docs-only PR is later found to have carried a risky change.
