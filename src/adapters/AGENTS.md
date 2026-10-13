# Trazo adapter for Codex and AGENTS.md readers

This file connects the host's operating instructions to Trazo. Read
`.trazo/rules.md` before governed work. The host's own instructions say how to build and
test its code; Trazo says which roles, approvals, and acceptance gates apply.

Before the first file write, follow the repository instruction file's document map into
referenced rule and decision directories. Skim their indexes or contents and read applicable
current records; a pointer is not a read. If the map does not name them, check project-local
`decisions/`, `rules/`, `adr/`, or equivalent paths. Project layouts vary.

For GitHub attribution, use the adapter and active model identified by the current role
context. Codex agent-file model settings are defaults and may be overridden. Include a
session or agent ID only when the runtime explicitly provides it to the role; do not depend
on undocumented environment variables or inspect local runtime data. For another tool that
loads only `AGENTS.md`, name that tool when known; otherwise use `AGENTS.md` as the adapter
label. Omit unknown model or ID fields.

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
