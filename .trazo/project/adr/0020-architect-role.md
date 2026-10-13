# 0020: Architect is an on-demand advisory role above engineering

**Date:** 2026-10-13  **Status:** accepted

Owner decision on [#193](https://github.com/manoochehri/trazo/issues/193). The proposal in the
2026-10-13 comment was accepted by the owner. Two points were read by the engineer and confirmed by
the owner in the same thread: the Anthropic tier is Opus (not the "Claude 3.5 Sonnet" the proposal
named), and the Codex top-tier model is Astra. This record amends [0015](0015-role-model-defaults.md)
by adding a fifth role mapping. It does not edit 0015.

## Context

The owner wants a role that keeps the big picture: whether the system is structured the right way,
and whether new work fits it. The PM already answers "are we solving the right problem?", but gets
pulled into issue management and nothing owns structure. A role that runs continuously would spend
the charter's AI budget for little return, so the role runs only when a trigger fires.

## Decision

- **Name and purpose:** the Architect (`architect`). It owns system architecture, cross-repository
  technical standards, technology stack selection, technical debt, infrastructure guardrails, and
  review of ADRs. Canonical definition: `src/overlay/roles/architect.md`.
- **Boundary with PM:** the PM keeps product objectives, feature prioritization, backlog grooming,
  release roadmaps, and user-experience decisions. The Architect keeps structure and technical
  constraints.
- **Cadence:** on-demand and on triggers only. Triggers: a new ADR is proposed, a major epic touching
  a core system boundary is opened, a phase transition between architecture milestones, or an
  engineer or the reviewer hits an architectural deadlock. Never a scheduled or background run.
- **Authority:** design authority to block a PR or ADR that violates a core design invariant, a
  system contract, or an architectural standard. Advisory only on product direction. Destructive
  infrastructure rollbacks, production deployments, and token-budget overrides stay human-only.
- **Model mapping (amends 0015):**
  - Claude Code: Opus, through an `/architect` command that sets Opus for its turn, like `/pm`.
    The Architect has no pinned subagent in this record.
  - OpenAI Codex: `gpt-6-astra` (the owner's name for the Codex top tier). **UNVERIFIED:** the exact
    model identifier was not checked against OpenAI's documentation; confirm it before the Codex
    agent is installed.
  - Cline: unchanged. Each user selects both provider and model.
- **Non-builder:** the Architect does not write application code, implement features, or manage task
  worktrees.

**Rule:** None

## Alternatives considered

- **A status-keeping CTO role:** rejected by the owner. The role is reframed as architecture, not
  status.
- **Architect as a blocking gate on every PR:** rejected by the owner. Blocking applies only to
  design-invariant violations, and it is triggered, not routine.
- **Sonnet for the Architect (the "Claude 3.5 Sonnet" in the proposal):** rejected. The owner's own
  comment named Opus, and the Claude 5 family is current.
- **Architect as a lead mode of engineering (#192):** not chosen for this record. The engineer
  lead/integrator mode is a separate decision on #192 and #196–#199. This record does not settle it.

## Consequences

- The role is a file set that does not run until installed. `src/` carries the canonical role and
  the adapters. `.trazo/` is the installed copy and is not hand-edited (ADR 0010), so the Architect
  reaches this repository's own `.trazo/roles/` only at the next release install. The same applies to
  the `/architect` command and the Codex agent. The install is tracked with the release, as ADR 0016
  does for `senior-eng`.
- The Codex model identifier is `UNVERIFIED` until checked against OpenAI's documentation.
- The `needs-decision` label on #193 is cleared only when this record merges. The #192 engineer-tier
  question remains open and is not settled here.

**Revisit** when the first Architect invocation shows whether the triggers fire at the expected rate,
when the Codex identifier is verified, or when #192's lead/integrator decision lands.
