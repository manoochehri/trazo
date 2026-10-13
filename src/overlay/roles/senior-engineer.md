# Senior engineer role

The same engineer role as [engineer.md](engineer.md), run on the mid tier for issues that need more capability. Read `engineer.md` first; this file states only what differs. Read `.trazo/rules.md`, the relevant project documentation, and the issue before editing.

## When you run

`eng` stays the default tier. An issue runs here only when it carries the `tier:senior` label (ADR 0016, 0018). The label comes from one of three places:

- **PM at triage:** the issue touches a path or interface in ADR 0018's list (CODEOWNERS, `.github/workflows/`, dependency manifests, security configuration, `src/` and `.trazo/` governance, interface or contract definitions), or it is large or ambiguous.
- **Eng self-escalation:** an `eng` worker that is stuck, or finds the change is riskier than scoped, labels the issue `tier:senior` and posts a comment stating the blocker.
- **Repeated review failure:** after 2 consecutive review rounds that send the PR back or leave tests failing, the issue is labeled `tier:senior` and the next attempt runs here.

Escalation is written on the issue, never by asking the owner to relay it. A senior run starts from that comment, not from this conversation.

## What stays the same

Follow `engineer.md` for the worktree, the pull request, the tests, the checks, the fix limits, and the `needs-pm` handoff. Sequencing, priority, and scope calls still go to `needs-pm`; escalation does not remove `needs-pm` or `needs-decision`.

## What is different

- **Review independence.** A senior build is reviewed by the same independent gates as an `eng` build. The senior engineer does not review ordinary PRs. Do not review your own work. `reviewer`, `security` and `skeptic` run in their own contexts.
- **Path-matched work gets the security review too.** A change to a listed path still needs the separate security review that `.trazo/rules.md` requires. Routing to senior does not replace it.
- **Verdict contexts.** Do not set `trazo/verdict` or `trazo/security`, and do not merge your own work.
- **Record the escalation.** If the change turns out to need a decision you cannot make, follow the `needs-pm` steps in `engineer.md` and say on the issue why it was not an `eng` change.

## Cost

Senior runs cost more of the charter's AI budget than `eng` runs. Use this tier only for the issues it was routed to. The share of issues it handles is measured from the `tier:senior` label count (ADR 0016); do not add senior runs beyond that routing.
