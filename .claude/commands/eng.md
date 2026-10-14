---
description: Return session to the engineer role (building code, tests, and pull requests)
model: haiku
---
Read `.trazo/roles/engineer.md` and resume the engineer role. Handle `$ARGUMENTS` if provided; otherwise reply exactly: "Engineer here. Ready to build. What are we working on?" and wait.

This command runs on Haiku for this turn. Claude Code restores the session's prior model on the next prompt; use `/status` to see the active model.
Use `/work` for the `needs-pm` handoff on sequencing, priority, or scope calls. `eng` is the default tier. If ADR 0018 routes the issue by path or the PM labels it for size or ambiguity, start in `/senior-eng`. If you are stuck, discover greater risk than scoped, or have 2 consecutive failed review rounds, put `tier:senior` on the issue with the blocker and route the next attempt to senior. Do not ask the owner to relay escalation.
