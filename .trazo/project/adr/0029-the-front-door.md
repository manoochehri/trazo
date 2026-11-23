# 0029: The front door is the main session, and it acts

**Date:** 2026-11-22  **Status:** proposed (becomes accepted when the owner merges this change; it adds a standing rule to `rules.md`)

Raised by the owner on 2026-11-22 and tracked in [#304](https://github.com/manoochehri/trazo/issues/304).
Extends [0025](0025-pm-cannot-start-agents.md).

## Context

[0025](0025-pm-cannot-start-agents.md) says the PM cannot start agents and that "the front door
starts the agent", but no file defines the front door. The term appears only in passing in
`ADVISOR.md`, `rules.md`, the PM role and the hook README.

Observed on Trazo v0.3.0 (Claude Code adapter, one host project, one session): after the upgrade
the owner ran `/trazo`. It printed a menu with "You could say: ..." suggestions and stopped. When
the owner replied "so, ask the pm?", the main session asked a question back instead of
dispatching the PM. The roles were in context the whole time. The failure was not missing
knowledge; nothing told the main session to act. The `/trazo` skill pulled the other way: it
required "You could say" suggestions, which hand the dispatch work back to the owner, and the
adapter's routing table sent "what can I do / help / menu" to that screen. One session is a
sample of one; the fix is a definition, not a measured rate.

## Decision

The front door is the main session. It reads the project state, dispatches the PM for any
what's-next or planning question, starts the agents the PM records on issues, and routes every
pull request to the reviewer, plus security and skeptic when their triggers apply. It is the
owner's chat interface to the whole team, ready to act the moment it opens, brief and plain, and
it asks the owner only for owner decisions. `rules.md` carries the definition in a "Front door"
section, both adapters point their "what's next" and "help/menu" rows at it, and the `/trazo`
skill reports what the front door is doing instead of printing a menu.

**Rule:** The main session is the front door: it reads the project state, dispatches the PM for any what's-next or planning question, starts the agents the PM records on issues, and routes every pull request to the reviewer, plus security and skeptic when their triggers apply.

## Alternatives considered
- Define it only in each adapter: the behavior would then differ by tool, and `rules.md` is the one file every tool loads.
- Give the PM an Agent tool again: rejected by [0025](0025-pm-cannot-start-agents.md); it defeats the PM's Bash allowlist.
- Keep the menu and add "dispatch if asked": still waits to be told, which is the failure observed.

## Consequences

Easier: any session knows what the main session is for, and the owner talks to one place.
Harder: the main session now acts without a prompt, so it must stay inside the stop list in
`rules.md` ("Ask before guessing"); this record loosens no gate. Revisit if the front door
starts agents the PM did not record, or if its replies stop being brief.
