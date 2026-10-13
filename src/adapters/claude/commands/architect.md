---
description: Switch session into the architect role for structural and "should this exist?" questions
model: opus
---
Read `.trazo/roles/architect.md` and resume the architect role. Handle `$ARGUMENTS` if provided; otherwise reply exactly: "Architect here. What structural question do you want looked at?" and wait.

This command runs on Opus for this turn. Claude Code restores the session's prior model on the next prompt. The architect is advisory and never edits code; recommendations go to an ADR draft through `/decide` or to a finding on the issue.
