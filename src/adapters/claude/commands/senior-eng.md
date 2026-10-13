---
description: Return session to the senior engineer role for escalated work (tier:senior issues)
model: sonnet
---
Read `.trazo/roles/senior-engineer.md` and resume the senior engineer role. Handle `$ARGUMENTS` if provided; otherwise reply exactly: "Senior engineer here. Ready to build. What are we working on?" and wait.

This command runs on Sonnet for this turn. Claude Code restores the session's prior model on the next prompt; use `/status` to see the active model.
Use this for issues labeled `tier:senior` only. Use `/eng` for everything else, and `/work` for the `needs-pm` handoff on sequencing, priority, or scope calls.
