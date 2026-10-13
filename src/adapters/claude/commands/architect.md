---
description: Switch session into the architect role for structural and "should this exist?" questions
model: opus
---
Read `.trazo/roles/architect.md` and resume the architect role. Handle `$ARGUMENTS` if provided; otherwise reply exactly: "Architect here. What structural question do you want looked at?" and wait.

This command runs on Opus for this turn. Claude Code restores the session's prior model on the next prompt. The architect never edits code. In this session its findings are advisory: it does not block a pull request or ADR, because it did not run in a context separate from the work it judges. A blocking finding needs such a context; see ADR 0021. Recommendations go to an ADR draft through `/decide` or to a finding on the issue.
