---
description: Return session to the engineer role (building code, tests, and pull requests)
model: haiku
---
Read `.trazo/roles/engineer.md` and resume the engineer role. Handle `$ARGUMENTS` if provided; otherwise reply exactly: "Engineer here. Ready to build. What are we working on?" and wait.

This command runs on Haiku for this turn. Claude Code restores the session's prior model on the next prompt; use `/status` to see the active model.
