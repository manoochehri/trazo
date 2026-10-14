---
description: Implement a GitHub issue on an isolated worktree branch and open a pull request
context: fork
model: haiku
---
Read and follow `.trazo/skills/work.md` as the canonical workflow.
Arguments: $ARGUMENTS

`eng` is the default tier. Route issues labeled `tier:senior` to `/senior-eng`; ADR 0018 also routes CODEOWNERS, `.github/workflows/`, dependency manifests or locks, security configuration, `src/` or `.trazo/` governance, interface or contract definitions, cross-workstream integration, or high architectural uncertainty to senior at triage. The PM may apply the label for size or ambiguity. Two consecutive failed review rounds also escalate the next attempt to senior.

This command runs in a forked Haiku context. Claude Code restores the session's prior model on the next prompt.
