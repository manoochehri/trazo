# 0015: Role model defaults by adapter

**Date:** 2026-10-08  **Status:** accepted

Decided by the owner in session and recorded on [#116](https://github.com/manoochehri/trazo/issues/116#issuecomment-6066816642).

## Context

The role model choices need to be visible in the installed adapters and handbook. Model
selection works differently in each tool: Claude Code supports project defaults, command
turn overrides, and subagent model pins; Codex supports model fields on role agents; Cline
asks each user to select a provider and model.

## Decision

- **Claude Code:** Haiku is the fresh-install default and the engineering model. `/work`
  runs in a forked Haiku context; `/eng` applies Haiku for its command turn. PM, reviewer,
  security, and skeptic use Sonnet. Their Claude subagents are pinned to Sonnet, and `/pm`
  applies Sonnet for its command turn.
- **OpenAI Codex:** the engineer role agent uses `gpt-6-luna`; PM, reviewer, security, and
  skeptic use `gpt-6.1-sol`.
- **Cline:** Trazo does not choose a provider or model. Each user selects both in Cline.

Claude command model overrides end with the command's turn; the session then resumes its
previous model. Existing Claude and Codex settings may override the installed defaults.

## Alternatives considered

- Keep Sonnet for engineering and Opus for other roles: rejected by the owner's updated
  model mapping on #116.
- Set a Trazo model for Cline: rejected because Cline users choose their own provider and
  model.

## Consequences

Role tables and implementation files name the same model per adapter. Users can see where
a tool pins a role and where their own selection remains in control. Revisit the mapping
when an adapter changes its model configuration behavior or the owner chooses new tiers.
