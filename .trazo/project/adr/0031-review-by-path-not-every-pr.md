# 0031: Reviewer and security are required for risky paths, not every pull request

**Date:** 2026-11-27  **Status:** proposed (becomes accepted when the owner merges this change; it edits `rules.md`)

Raised by the owner on 2026-11-27 and tracked in [#367](https://github.com/manoochehri/trazo/issues/367).
Supersedes the routing clause of [0029](0029-the-front-door.md): "routes every pull request to the
reviewer". Everything else in 0029 stands.

## Context

[0029](0029-the-front-door.md) has the main session route every pull request to the reviewer. Each
subagent review spends the charter's AI budget, and for a documentation-only or
`.trazo/project/` state change the review adds cost and delay without a matching risk. The owner's
words on #367: "not everything needs to be reviewed, you know that. there should be discretion",
then "i approve the change".

## Decision

The reviewer and security subagents are required only when a pull request changes a risky path:
hooks, workflows, settings or permissions, dependencies, rulesets, secrets, `CODEOWNERS`, and rules,
role and agent-instruction files. A pull request that changes only documentation or
`.trazo/project/` state is checked by the Coordinator against the diff and CI, with no subagent.
The Coordinator may still send any pull request to review. A diff that touches both kinds follows
the risky-path rule.

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
