---
description: Ask the engineer to build an issue (runs the engineer subagent)
---
Do not build in this session. Launch the `engineer` subagent with the Agent tool, fresh each time, passing `$ARGUMENTS` (the issue number or the change asked for). If `$ARGUMENTS` is empty, reply exactly: "Engineer ready. Which issue?" and wait. Relay its report to the owner briefly, with the pull request URL.

Use the `senior-engineer` subagent (`/senior-eng`) for an issue labeled `tier:senior`, or one that ADR 0018 routes there by path, size or ambiguity. If the engineer reports it is stuck, finds the change riskier than scoped, or has 2 consecutive failed review rounds, it puts `tier:senior` on the issue with the blocker; route the next attempt to senior from that comment, never by asking the owner to relay it. Use `/work` for the `needs-pm` handoff on sequencing, priority or scope calls.

The `engineer` subagent reads `.trazo/roles/engineer.md` and runs on Haiku with no `Agent` tool. This session keeps every tool and a long context, which is why it does not build: a role set by prompt fades, a subagent's tools do not.
