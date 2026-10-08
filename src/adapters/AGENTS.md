# Trazo adapter for Codex and AGENTS.md readers

This file connects the host's operating instructions to Trazo. Read
`.trazo/rules.md` before governed work. The host's own instructions say how to build and
test its code; Trazo says which roles, approvals, and acceptance gates apply.

Before the first file write, follow the repository instruction file's document map into
referenced rule and decision directories. Skim their indexes or contents and read applicable
current records; a pointer is not a read. If the map does not name them, check project-local
`decisions/`, `rules/`, `adr/`, or equivalent paths. Project layouts vary.

## Route plain-English requests

Use the matching Trazo skill for a request even when the owner does not name a command:

| Request | Skill or role |
|---|---|
| “Work on issue 12”, “fix this”, or another implementation request | `trazo-work` |
| “What is next?”, “catch me up”, or a status request | `trazo-start` |
| “Is PR 15 ready?”, “review this PR”, or “can I merge?” | `trazo-check-pr` |
| “Should we do this?” or a prioritization question | `trazo-pm` |
| “Help” or “what can I do?” | `trazo-menu` |

Codex skills are installed under `.agents/skills/`; role agents are under
`.codex/agents/`. If the matching skill is not available to invoke, read its installed
`SKILL.md` and follow it. Do not answer with a command for the owner to run when the
plain-English request already asks you to do the work.

The skills contain the workflows; this adapter only routes requests to them. Their
instructions and `.trazo/rules.md` remain canonical.
