# ADR index

**Status:** current

This is the entry point for Trazo's append-only architecture decision records. A reader
should use this index before relying on a decision. The numbered files are the source
records; this index classifies them without rewriting their history.

## Conflict rule

An accepted ADR controls the decision it explicitly supersedes or amends, with the later
accepted record taking precedence for that scope. Otherwise, the current architecture
document describes the present system shape, and the architecture contract records its
boundaries and checks. Proposed, historical, and superseded records are not authority for
new work. If the documents still conflict, stop the affected choice and send it to the
architect/PM for resolution; do not infer a new rule from a stale path or a PR description.

The canonical architecture source is [`src/overlay/ARCHITECTURE.md`](../../../src/overlay/ARCHITECTURE.md).
The installed `.trazo/ARCHITECTURE.md` is the pinned release copy and is not hand-edited.

## Current accepted decisions

These records are accepted and remain applicable within the scope stated by each record.

| ADR | Decision |
|---|---|
| [0001](0001-record-decisions.md) | Keep project state in the repository |
| [0002](0002-per-issue-git-worktrees.md) | Use an isolated worktree per issue |
| [0003](0003-review-security-github-tracked.md) | Track review and security findings in GitHub |
| [0004](0004-docs-site-claude-aws-focus.md) | Public positioning is built for Claude Code and opinionated toward AWS |
| [0005](0005-pivot-to-trazo.md) | Trazo is a mountable, tool-neutral governance overlay; later records refine parts of its old layout description |
| [0006](0006-release-process.md) | Releases are immutable tags cut by `make release` |
| [0007](0007-claude-is-an-adapter.md) | Claude is an optional adapter, not part of the tool-neutral overlay |
| [0009](0009-tag-immutability-binds-from-first-consumer.md) | Tag immutability binds from the first external consumer |
| [0010](0010-src-canonical-trazo-pinned.md) | `src/` is canonical, `.trazo/` is the pinned install |
| [0011](0011-ours-in-project-hosts-get-templates.md) | Repository state stays in `.trazo/project/`; hosts receive templates |
| [0012](0012-a-release-is-a-milestone.md) | A release is a GitHub milestone |
| [0013](0013-what-a-version-number-means.md) | Version changes reflect the milestone's scope |
| [0015](0015-role-model-defaults.md) | Role model defaults are adapter-specific |
| [0018](0018-senior-tier-routing-accepted.md) | Senior-tier routing and escalation are accepted; it settles 0016's open points |
| [0020](0020-verdict-success-from-bot-review.md) | The bot review may set `trazo/verdict` to success within its stated scope |
| [0021](0021-architect-role.md) | Architect is an on-demand advisory role above engineering |
| [0022](0022-native-review-subagents.md) | Native reviewer subagents are the default; hosted review is optional |
| [0023](0023-bind-review-verdict-to-head.md) | Automatic verdicts bind to the exact reviewed head |
| [0024](0024-unattended-drive-workflow.md) | The unattended drive workflow may auto-merge after its gates pass |
| [0025](0025-pm-cannot-start-agents.md) | The front door dispatches agents; the PM cannot start them |
| [0027](0027-drive-spend-cap-and-runaway-guardrails.md) | Drive spend and runaway guardrails apply |
| [0028](0028-report-job-sets-verdict-as-reviewer-app.md) | The report job writes the verdict as the reviewer App |

## Proposed or partially superseded decisions

These records are discoverable and useful context, but are not accepted authority for new
work. Follow their linked accepted successor where one exists.

| ADR | State and successor |
|---|---|
| [0008](0008-agents-md-is-the-cross-tool-adapter.md) | Proposed; its adapter guidance is historical context for the current adapter set |
| [0014](0014-current-layout-supersedes-stale-paths.md) | Proposed; records the current interpretations of 0005–0008 |
| [0016](0016-senior-engineer-tier.md) | Superseded in part by [0018](0018-senior-tier-routing-accepted.md) |
| [0017](0017-automatic-review-on-push.md) | Proposed and partially superseded by [0020](0020-verdict-success-from-bot-review.md) and [0022](0022-native-review-subagents.md) |
| [0026](0026-decide-then-tell.md) | Proposed; acceptance is tied to its stated owner review |
| [0029](0029-the-front-door.md) | Proposed; acceptance is tied to its stated owner review |
| [0030](0030-drive-halt-clears-itself-once.md) | Proposed; acceptance is tied to its stated owner review |
| [0031](0031-review-by-path-not-every-pr.md) | Proposed; supersedes 0029's "every pull request" routing clause once the owner merges |

## Superseded decisions

| ADR | Superseded by |
|---|---|
| [0019](0019-pm-may-spawn-subagents.md) | [0025](0025-pm-cannot-start-agents.md) |

The older records named by [0010](0010-src-canonical-trazo-pinned.md) remain append-only
historical evidence. Their stale layout paths are not instructions for current work.
