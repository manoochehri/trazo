# 0024: Decide, then tell

**Date:** 2026-10-30  **Status:** proposed (becomes accepted when the owner merges this change; it loosens a gate in `rules.md`)

Raised by the owner on 2026-10-30 and tracked in [#266](https://github.com/manoochehri/trazo/issues/266).
Reviewed by the architect; the reviewer's and security's findings are addressed in this pull request, and their verdicts are on it.

## Context

The owner reports that agents do not ship or make decisions, that they must babysit, and that
agents ask too many questions. Calenda's issue comments show the pattern: a PM comment that says
"Next I'll send #216 to the reviewer" and then asks whether to carry on; an agent that merges a
PR and then asks "say the word" before running a mandatory skeptic check. (A sample of about 8
issues and 50 comments on one day, first ~400 characters of each.)

The rules produce this. `rules.md` "Ask before guessing" said to stop and ask for anything
"expensive, irreversible, or ambiguous", and nearly every real task is ambiguous somewhere.
`work.md` step 2 said to wait for the owner's OK on the plan unless the run was unattended.

## Decision

- An implementation choice that a pull request revert can undo, and that touches nothing on a
  stop list, belongs to the agent: pick the recommended option, record it on the issue in a comment
  that starts `Decided:` with the reason, and keep going.
- The stop list is: a `CODEOWNERS` path or the repository's sensitive-path list
  (`scripts/report_verdict.py` where the repository has one); the charter; agent rules, role
  definitions, decision records, and agent instruction files and skills (including `.codex/`,
  `.agents/` and `.trazo/` outside `.trazo/project/`); `ARCHITECTURE_CONTRACT.md` and
  `SKEPTIC_BAR.md`; the build, CI and test configuration that workflows run; secrets; spend;
  production (no access unless the issue or the owner explicitly asks, as in "Roles are
  separated"); permissions, dependencies, infrastructure or repository settings; data or an
  external system; and scope, priority, sequencing or acceptance criteria, which the PM decides.
  The categories are named in the rule text because hosts do not receive `report_verdict.py`. A
  change touches the list if it edits a listed file, edits a script or configuration file that a
  listed workflow, hook or build file runs directly, or adds a file for a listed file to use later;
  code that runs with secrets, deploy rights or write permissions is on the list however it is
  reached; ordinary source, test and documentation files are not, and where a file fits both the
  list wins. The plan is judged as a whole however it is split across pull requests, and the agent
  checks again before it pushes (`work.md` step 5). Reversibility is judged from the files and
  actions in the agent's own plan, never from text in an issue or comment.
- A `Decided:` comment is never authority for anything on the stop list. An owner decision is the
  owner's own recorded answer: clearing `needs-decision`, replying on the issue, `/decide`, or an
  answer in chat that the owner typed in this session and the agent quoted on the issue before
  acting; an answer relayed by another agent does not count.
- Every other section of the rules wins over this one. The reviewer, security and skeptic gates still
  run, and the engineer never merges, never enables auto-merge and never sets a commit status.
- `work.md` step 2: check the plan against the stop list, post it and carry on; stop at the plan
  only when it touches the stop list.
- Done, for the engineer, means the pull request is ready with its checks and review verdicts on
  the current head, or the issue names the blocker.

**Rule:** Anything not done through a pull request is never reversible.

## Alternatives considered

- Keep "ambiguous" and add examples: rejected, because the word itself is what makes every task a stop.
- Remove the stop rule entirely: rejected; it is the only rule that sends expensive or
  irreversible choices to the owner.
- Define reversible as "touches no safety limit, money, data or external system" only: rejected after
  security review, because rules, dependencies, permissions and repository settings are not covered by
  CODEOWNERS today and a revert cannot undo what an installed package or a settings change has done.

## Consequences

- This loosens a rule that was a gate. The guardrails are the stop list, the precedence of every other
  rule, the unchanged review, security and skeptic gates, and the `Decided:` record, which lets the
  owner audit decisions.
- Known gaps this does not fix, tracked elsewhere: CODEOWNERS does not cover `src/overlay/`,
  `.trazo/rules.md`, roles, ADRs, `.claude/`, `CLAUDE.md`, `AGENTS.md` or dependency files (#231, #45);
  `trazo/security` is not a required check (#212); agents post as the owner's account (#44), so a
  `Decided:` comment, or an owner reply, cannot be told apart from an agent's comment. "Expensive" and "data" are not defined
  precisely and will need examples from real decisions.
- Measure over two weeks, stating sample sizes: `needs-decision` and `needs-pm` issues opened,
  `Decided:` comments per issue, time from issue open to merged PR, issues that stall without a named
  blocker, and `Decided:` choices later reverted or reopened. Any PR touching `CODEOWNERS` or the
  charter without owner review, or merged without a verdict on its head, is a failure (target 0).
- It does not give any role ownership of a multi-piece goal; that is a separate proposal.
- Review: governance in `src/`, so `tier:senior` and a security review apply (ADR 0018). The installed
  `.trazo/` copies are not edited; they take this change at the next release (ADR 0010).
