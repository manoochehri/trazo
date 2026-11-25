---
description: Ask the senior engineer to build an escalated issue (runs the senior-engineer subagent)
---
Do not build in this session. Launch the `senior-engineer` subagent with the Agent tool, fresh each time, passing `$ARGUMENTS` (the issue number or the change asked for). If `$ARGUMENTS` is empty, reply exactly: "Senior engineer ready. Which issue?" and wait. Relay its report to the owner briefly, with the pull request URL.

Use this for issues labeled `tier:senior` only. Use `/eng` for everything else, and `/work` for the `needs-pm` handoff on sequencing, priority or scope calls.

The `senior-engineer` subagent reads `.trazo/roles/senior-engineer.md` and runs on Sonnet with no `Agent` tool. A path-matched change still gets its separate security review from the front door.
