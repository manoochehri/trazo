# 0016: Senior engineer is an escalation tier above eng

**Date:** 2026-10-13  **Status:** superseded in part by [0017](0017-senior-tier-routing-accepted.md) (N, path routing and label accepted there)

Owner direction on [#192](https://github.com/manoochehri/trazo/issues/192#issuecomment-6095022087),
[#192 escalation](https://github.com/manoochehri/trazo/issues/192#issuecomment-6095043089) and the
[#192 decision comment](https://github.com/manoochehri/trazo/issues/192#issuecomment-6147002417).
This record proposes answers to the open points those comments left: the escalation count, review
independence, and cost. It amends [0015](0015-role-model-defaults.md) by adding a second
engineer mapping. It does not edit 0015.

## Context

Engineering work currently has one tier, `eng`, mapped to the cheap model in each adapter
(Haiku on Claude Code, `gpt-6-luna` on Codex). Some issues need more capability: an interface
decision, a cross-cutting change, or a change riskier than its scope said. The owner wants
`eng` to stay the default and a stronger tier to be used only when a task needs it. A
stronger tier used for every issue would cost more of the charter's AI budget than the
owner wants to spend.

## Decision

- **Default:** every issue is `eng` work unless it is escalated.
- **Senior engineer (`senior-eng`):** the same engineer role, run on the mid tier. Claude
  Code: Sonnet, through a `/senior-eng` command that is not yet shipped (see
  Consequences). Codex: `gpt-6.1-sol`. Cline stays user-selected.
- **Escalation to senior** happens in one of three ways:
  1. **PM at triage:** the PM applies the `tier:senior` label when the issue is harder from
     the start.
  2. **Eng self-escalation:** an `eng` worker that is stuck, or finds the change is riskier
     than scoped, labels the issue `tier:senior` and posts a comment stating the blocker.
  3. **Repeated review failure:** after **2** consecutive review rounds that send the PR back
     or leave tests failing, the issue is labeled `tier:senior` and the next attempt runs at
     senior. The count is 2 because one failed round is ordinary review; two means the first
     attempt's scope or approach was wrong.
- Escalation is written on the issue, never by asking the owner to relay. Expanding the
  escalation path does not remove `needs-pm` or `needs-decision`; those keep their meaning.
- **Review independence:** senior engineers do not review ordinary implementation PRs.
  `reviewer`, `security` and `skeptic` run in their own contexts as before. A senior build is
  reviewed by the same independent gates as an `eng` build. When the senior and reviewer
  models are both Sonnet, independence comes from the separate context, not from a different
  model.
- **Cost:** senior runs only for escalated issues. The owner's estimate was 15–20% of
  issues. **UNVERIFIED:** no sample exists yet. Measure it by counting `tier:senior` labels
  over the next 20 closed issues in the milestone, and revisit this record with that count.

**Rule:** None

## Alternatives considered

- **Route by path or size** (CODEOWNERS, workflows, dependency manifests, `.trazo/`): left as
  owner question (b). Those paths already get a separate security review (ADR 0003); whether
  routing on them would add anything beyond that review is for the owner to decide.
- **Senior reviews eng's PRs:** rejected. It makes the builder's tier the reviewer, which is
  the same-context problem the separated roles exist to prevent.
- **Escalate after one failed review:** rejected as too eager for the cost budget.
- **Senior as the default for everything:** rejected by the owner.

## Consequences

Engineering has two mapped tiers per adapter. The `tier:senior` label is the only routing
field, so the queue answers "what needs senior" without parsing prose. The cost of the senior
tier is bounded by the escalation rules, and it is measured rather than assumed. The
lead/integrator and CTO role questions are separate decisions (#193, #196–#199) and are not
settled here.

**Open for the owner:** (a) confirm N = 2; (b) whether path or size should route to senior, as
the 2026-10-13 comment proposed; (c) the label name: the same comment used `status:escalated`
for eng self-escalation, and this record uses `tier:senior`. The role file, `/senior-eng`
command and Codex agent are not in the PR that adds this record. They wait for a release
install (ADR 0010) and are tracked in #203.

**Revisit** when the measured escalated share is known, or when an adapter changes how it
pins models.
