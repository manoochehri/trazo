---
description: Ask the PM / advisor for planning, priorities, and issues (runs the pm subagent)
---
Do not act as the PM in this session. Launch the `pm` subagent with the Agent tool, fresh each time, passing `$ARGUMENTS` (or, if empty, "Where do things stand and what is next?") and the issue or PR numbers in play. Relay its answer to the owner unchanged and briefly. Do not summarise it into a decision of your own, and do not run the commands it asks for.

The `pm` subagent reads `.trazo/ADVISOR.md` and runs on Sonnet with a Bash allowlist enforced by a hook (issue #279). This session keeps every tool and a long context, which is why it never plays the PM: a role set by prompt fades, a subagent's tools do not.
