---
description: Switch session into PM / advisor role for planning, priorities, and issues
model: sonnet
---
Read `.trazo/roles/pm.md` and `.trazo/ADVISOR.md` and resume the PM role. Handle `$ARGUMENTS` if provided; otherwise reply exactly: "PM here. What's on your mind? The pm subagent is pinned to Sonnet." and wait.

This command runs on Sonnet for this turn. Claude Code restores the session's prior model on the next prompt. For subsequent PM work, invoke the pinned `pm` subagent.
