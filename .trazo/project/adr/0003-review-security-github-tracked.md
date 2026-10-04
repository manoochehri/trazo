# 0003: Review and security findings are always tracked in GitHub, never chat-only

**Date:** 2026-09-28  **Status:** accepted

## Context
`/reviewer`/`/security` as role-switch commands let the same conversation review code it just wrote, with the verdict living only in chat — never posted anywhere. This session: reviewer-subagent (fresh-context) review found real, fixable bugs on 4 separate PRs (#11, #13, #17, #20). The role-switch `/reviewer` path was never actually used to review anything in that same window.

## Decision
- `reviewer`/`security` become subagent-only — no role-switch command.
- Every subagent verdict on a PR posts as a real `gh pr review` (approve / request-changes).
- A security finding not tied to a PR becomes a GitHub issue.
- `/work` opens the PR after the first commit, not after review, so there's something to comment on.
- No auto-loop: picking up a review stays a deliberate step (the owner asks, or the optional GitHub Actions layer).

## Alternatives considered
- Full auto-loop (reviewer → engineer auto-fix → re-review): rejected, unbounded cost/risk with no human checkpoint.
- Keep `/reviewer` as role-switch but block it from reviewing its own conversation's work: rejected, simpler to just not offer the mode.

## Consequences
Two true role-switches left (`pm`, `eng`); `reviewer`/`security` are subagent-only. One review pathway instead of three. DevOps role stays deferred (not rejected). Revisit if the optional GitHub Actions layer ships and full auto-pickup becomes worth the cost/risk tradeoff.
