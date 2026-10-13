# 0019: The PM may spawn arbitrary subagents (accepted risk)

**Date:** 2026-10-13  **Status:** accepted

## Context
The PM needs to sweep pull requests and issues and start work by spawning subagents. Issue
[#209](https://github.com/manoochehri/trazo/issues/209) found that the `pm` subagent had no
Agent tool, so PMs reported they could not do this. Owner decision on #209 (2026-10-13):
"should the PM be allowed to spawn arbitrary subagents? YES".

Security review of PR #210 raised finding M1: nothing limits which subagent type the PM
spawns. The PM already has unrestricted Bash, so the Agent tool adds no new authority class.
Spawned subagents inherit the session's permission denies.

## Decision
The PM may spawn arbitrary subagents. The review roles (reviewer, security, skeptic) still run
in their own context and are never the PM's own work. The PM starts a review and briefs it, but
never writes or posts a verdict, never sets `trazo/verdict` or `trazo/security`, and never tells a
reviewer to skip its gate. The accepted risk is M1 above: no enforcement of subagent type.

**Rule:** None

## Alternatives considered
- Allowlist of subagent types in the `pm` agent definition: rejected by the owner decision;
  the PM already has the Bash authority that an allowlist would have to police.
- Keep the PM read-only: rejected; it blocks the PM's sweep-and-dispatch job from #209.

## Consequences
Easier: the PM can clear the board and dispatch reviewers, security and engineers as subagents.
Harder: nothing mechanical stops the PM from spawning an edit-capable subagent; the gate on
verdicts relies on the reviewer and security roles and on the commit-status checks they run.
Revisit if a spawned subagent is found to have written code or posted a verdict.
