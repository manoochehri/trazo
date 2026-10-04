# 0004: Public positioning is "built for Claude Code, opinionated toward AWS"

**Date:** 2026-09-28  **Status:** accepted

## Context
The published docs site (`handbook/index.md`, at https://manoochehri.github.io/semilla/) described semilla as tool-agnostic — "a self-improving template for starting software projects with AI coding agents" — and named no primary deploy target. That undersold what's actually true day to day: semilla is built and tested against Claude Code specifically, and of the three cloud deploy targets in `infra/`, AWS is the most complete (`infra/aws/` ships a working bootstrap stack — budget alerts, GitHub OIDC, ECR — while `infra/gcp/` is a stub kickoff fills in later, and `infra/fly/` is simple but has no bootstrap automation). The owner asked for the messaging to say so plainly, while keeping every existing option functionally available.

## Decision
- The docs site's tagline and framing now say semilla is built for **Claude Code** and is opinionated toward **AWS** as the primary, recommended deploy target.
- Fly.io, GCP, and local-only remain fully supported, unremoved, and still offered at `/kickoff` — this is a positioning change, not a scope cut. `kickoff.md`'s interview and `infra/` are untouched.
- Fixed stale `/reviewer`/`/security` role-switch language in `handbook/index.md`, `handbook/guide.md`, `handbook/playbook.md`, and `handbook/team.md` to match decision 0003: only `/pm` and `/eng` are true role switches; reviewer and security are subagent-only.

## Alternatives considered
- Leave the framing tool-agnostic: rejected — it doesn't match how the template is actually built or maintained, and reads as noncommittal.
- Remove Fly.io/GCP/local support to match the AWS-first message: rejected — out of scope (messaging only) and would cut working, supported functionality nobody asked to lose.

## Consequences
Easier: new visitors get an accurate, opinionated read of what semilla is for before they clone it. Harder: nothing functional; this is docs-only. Revisit if the primary deploy target changes, or if GCP/Fly.io reach parity with AWS's bootstrap automation and the ranking should be reconsidered.
