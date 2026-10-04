<!-- trazo:begin -->
# CLAUDE.md

The Claude Code adapter. It states no rules of its own: the rules live once, tool-neutral, in
[`.trazo/rules.md`](.trazo/rules.md), and the line below imports them at load.

@.trazo/rules.md

A repo mounted onto a different tool has a different adapter and the same `.trazo/rules.md`. What
follows is only what is specific to *this* tool: where Claude Code's commands and subagents live,
and how its roles satisfy rules the import already covers.

**Launch every session from the repository root.** An import resolves when the session starts in
the directory holding `CLAUDE.md`; from a subdirectory this line arrives unexpanded. That is
verified at runtime, not assumed. An import that does not resolve fails silently: no error, and the session runs with no rules.

**Read first, every session:** [`.trazo/project/charter/charter.md`](.trazo/project/charter/charter.md) and
[`.trazo/project/STATUS.md`](.trazo/project/STATUS.md). Then open GitHub issues for the current milestone.

## Where things live
| Doc | Purpose |
|---|---|
| `.trazo/rules.md` | The rules, tool-neutral. This file only adapts them. |
| `.trazo/project/charter/` | Why, goal, success criteria, budget, hard constraints, stop rule |
| `.trazo/project/adr/` | Numbered decision records. Append-only; supersede, never edit |
| `.trazo/project/workstreams/` | One file per feature/experiment/strategy, with status and evidence |
| `.trazo/specs/` | Design specs for features and tasks |
| `.trazo/ARCHITECTURE.md` | How the system is built (with diagram) |
| `.trazo/ADVISOR.md` | The advisor/PM role |
| `.trazo/project/PLAN.md` | Milestones and timeline |
| `.trazo/project/STATUS.md` | Current state only; replaced each session |
| `.trazo/project/RUNBOOK.md` | How to run, test, deploy, roll back, recover |
| `.trazo/project/SKEPTIC_BAR.md` | The bar a result must clear before the skeptic passes it; filled in per project |
| GitHub Issues | Tasks. Labels: bug, feature, research, infra, needs-decision, needs-pm, P0, P1, P2, epic |

`.trazo/project/` is this project's own state: charter, decision records, workstreams, STATUS,
PLAN, RUNBOOK, SKEPTIC_BAR and reports. An upgrade never overwrites it. Everything else in
`.trazo/` is the installed framework and is not hand-edited.

## The team (subagents in `.claude/agents/`, role commands in `.claude/commands/`)
Role commands (`/pm`) switch the session's role for the rest of the conversation until another role command is used; `/eng` returns to building. `reviewer`, `security`, and `skeptic` are subagent-only — the engineer role delegates one-off checks to them, invoked ad hoc or as part of the `/work` and `/check-pr` routines. How each satisfies a rule is in the table above.

| Role / Agent | Command | Model | Use for | Edits code? |
|---|---|---|---|---|
| Engineer (main session) | `/eng` | default (Sonnet) | Building: code, tests, git, pull requests | Yes |
| PM / advisor | `/pm` | Opus | Status, planning, priorities, "is this result real?", charter/budget/stop rule, writing issues | No |
| Reviewer (subagent only) | ask the **reviewer** subagent | Opus | Reviewing pull requests and diffs before merge | No |
| Security (subagent only) | ask the **security** subagent | Opus | Secrets, permissions, workflows, dependencies, infra, repo security settings | No |
| Skeptic (subagent only) | ask the **skeptic** subagent | Opus | Breaking a research/analysis result before it is acted on | No |

## Plain English → routine
The owner shouldn't need to remember commands. Map requests to routines:
| If the owner says something like… | Do |
|---|---|
| "catch me up", "where are we", "what's next" | `/start` routine (or `/pm` for strategy questions) |
| "what can I do", "help", "menu" | `/trazo` |
| "work on issue 12", "fix X" | `/work` routine; the commit message carries `Closes #12` |
| "is this PR ok", "review #15", "can I merge" | `/check-pr` routine (or ask the **reviewer** subagent directly) |
| "is this secure", "check permissions" | ask the **security** subagent |
| "is this number real?", "poke holes in this analysis", "what would make this wrong?" | ask the **skeptic** subagent |
| "should we…", "is this worth it", "plan the next milestone" | `/pm` |
| "back to building", "ready to code" | `/eng` |
| "we decided…" | `/decide` routine |
| "wrap up", "done for today" | `/wrapup` routine |
| "GitHub/CI says …" (settings, failures) | handle it directly; ask the **security** subagent for protection/permission settings |

## How this tool satisfies the rules

The rules above are the whole of what governs the work. What follows is only where *this* tool
answers each one. Nothing here restates a rule; if this section and `.trazo/rules.md` ever
disagree, `rules.md` is right and this section is the bug.

| Rule | Where Claude Code answers it |
|---|---|
| Secrets (never read, print, log, commit) | Never open `.env` or anything in `secrets/`. The human enters secrets; new config goes in the env example as a placeholder. |
| Safety limits are human-only | Anything in `.github/CODEOWNERS` (limits, infra, workflows) changes only with the owner's review. Automation may tighten, never loosen. |
| Roles are separated | The **reviewer**, **security** and **skeptic** subagents each run in their own context. `reviewer`, `security` and `skeptic` are subagent-only, never role-switch commands — a review that grades the same conversation that produced the work is not a review. |
| A result is not a result until it has been checked | The **skeptic** subagent checks it against [`.trazo/project/SKEPTIC_BAR.md`](.trazo/project/SKEPTIC_BAR.md) and returns *holds* / *holds with caveats* / *does not hold*. If it cannot run, say the result is unverified rather than proceeding. |
| Hand off through the repo | Every subagent verdict on a pull request posts as a real `gh pr review --comment`, verdict word as the first line. `--approve` / `--request-changes` are refused when the agent and the PR author are one account. A security finding not tied to a PR becomes a GitHub issue. |
| Leave state in the repo | End a session with `/wrapup`. A PR that claims to close an issue carries `Closes #<n>` in the **commit message**, not only the body: a squash merge keeps only the commit message. |
<!-- trazo:end -->
