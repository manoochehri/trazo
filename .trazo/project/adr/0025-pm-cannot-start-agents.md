# 0025: The PM cannot start agents; the front door dispatches

**Date:** 2026-11-19  **Status:** accepted

Decided by the owner on [#279](https://github.com/manoochehri/trazo/issues/279) (option 1,
2026-11-19), after the security review of PR #283 found the PM's `Agent` tool defeated the PM's
Bash restrictions. Supersedes [0019](0019-pm-may-spawn-subagents.md).

## Context

[0019](0019-pm-may-spawn-subagents.md) let the PM spawn arbitrary subagents and accepted that
nothing limited their type, reasoning that the PM already held unrestricted Bash. #279 removes
that premise: the `pm` agent's Bash is now an allowlist enforced by a PreToolUse hook. A subagent
the PM starts is a different agent with its own tools; the PM's frontmatter hook does not apply
to it (hooks in subagent frontmatter run only while that subagent is active; Claude Code docs,
sub-agents page). So with the `Agent` tool, a PM that cannot run `fly deploy` can ask a
general-purpose agent to run it. The security review of PR #283 found exactly this bypass.

## Decision

The `pm` subagent has no `Agent` tool. The PM records the dispatch (which agent, which inputs)
on the issue; the front door, which is the main session, starts the agent. The review roles
(reviewer, security, skeptic) still run in their own context, and the PM still never writes or
posts a verdict or sets `trazo/verdict` or `trazo/security`.

The Claude adapter enforces this by omitting `Agent` from `tools:`; a test fails if it returns.

**Rule:** None

## Alternatives considered
- Keep the PM's `Agent` tool and restrict spawnable types with `Agent(type)` in `tools`: leaves
  the PM able to start any listed agent with a prompt of its choosing; not chosen by the owner.
- Register the Bash guard for every agent: blocks engineers, who must push and build.

## Consequences

Easier: the PM's authority is exactly its Bash allowlist plus read tools, so it can be audited.
Harder: the PM can no longer sweep and dispatch in one turn; the main session reads the
dispatch on the issue and starts the agent. Revisit if the front door cannot keep up with the
dispatch queue, or if Claude Code lets a parent's hooks bind the subagents it starts.
