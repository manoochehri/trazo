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
Before the first file write, follow the repository instruction file's document map into referenced
rule and decision directories, skim their indexes or contents, and read applicable current records.
If the map does not list them, check project-local `decisions/`, `rules/`, `adr/`, or equivalent paths;
the layout is project-specific.

## Where things live
| Doc | Purpose |
|---|---|
| `.trazo/rules.md` | The rules, tool-neutral. This file only adapts them. |
| `.trazo/roles/` | Canonical role definitions (engineer, PM, reviewer, security, skeptic) |
| `.trazo/project/charter/` | Why, goal, success criteria, budget, hard constraints, stop rule |
| `.trazo/project/adr/` | Numbered decision records. Append-only; supersede, never edit |
| `.trazo/project/workstreams/` | Open hypotheses and the evidence gathered while work continues |
| `.trazo/project/reports/` | Completed investigations and their cited evidence |
| `.trazo/ARCHITECTURE.md` | How the system is built (with diagram) |
| `.trazo/ADVISOR.md` | The advisor/PM role |
| `.trazo/project/PLAN.md` | Link to the GitHub milestone that owns current scope and ordering |
| `.trazo/project/STATUS.md` | Short pointer to current project state; replaced each session |
| `.trazo/project/RUNBOOK.md` | How to run, test, deploy, roll back, recover |
| `.trazo/project/SKEPTIC_BAR.md` | The bar a result must clear before the skeptic passes it; filled in per project |
| GitHub Issues | Tasks. Labels: bug, feature, research, infra, needs-decision, needs-pm, P0, P1, P2, epic |

`.trazo/project/` is this project's own state: charter, decision records, workstreams, STATUS,
PLAN, RUNBOOK, SKEPTIC_BAR and reports. Documents carry `**Status:** current` or a link to the
file that supersedes them. An upgrade never overwrites this state. Everything else in
`.trazo/` is the installed framework and is not hand-edited.

## The team (subagents in `.claude/agents/`, role commands in `.claude/commands/`)
Claude Code implements the canonical Trazo roles defined in `.trazo/roles/`. Role commands (`/pm`, `/eng`) set the role prompt for that command turn; the model override does not persist to the next turn. `/work` runs in a forked Haiku context. `pm`, `reviewer`, `security`, and `skeptic` are pinned subagents; reviewer/security checks are delegated automatically in `/work` and `/check-pr` or invoked ad hoc.

| Canonical Role | Claude Implementation | Model | Edits code? |
|---|---|---|---|
| **Engineer** (`.trazo/roles/engineer.md`) | `/eng` command (main session) | Haiku for the `/eng` turn; Haiku recommended for engineering | Yes |
| **PM / Advisor** (`.trazo/roles/pm.md`) | `/pm` command and `pm` subagent | Sonnet for the `/pm` turn and pinned `pm` subagent | No |
| **Reviewer** (`.trazo/roles/reviewer.md`) | `reviewer` subagent | Sonnet (pinned) | No |
| **Security** (`.trazo/roles/security.md`) | `security` subagent | Sonnet (pinned) | No |
| **Skeptic** (`.trazo/roles/skeptic.md`) | `skeptic` subagent | Sonnet (pinned) | No |

Claude Code restores the session's previous model after a role command's turn. Use the pinned subagents for PM, reviewer, security, and skeptic work that must run on Sonnet. `/eng` sets Haiku for its turn; a fresh host install uses Haiku as the default when the host has no existing `.claude/settings.json`.

For complete role definitions including purpose, permissions, and constraints, see the canonical files in `.trazo/roles/`.

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

## This repository

Notes specific to Trazo's own repo, outside the shipped block above. Claude Code does not
load `AGENTS.md`, so the repo-specific guidance is repeated here.

- Secrets: the owner enters them with `scripts/put_secret.sh`; new config goes in `.env.example`.
- Verdicts post as `gh pr review --comment`. `--approve` and `--request-changes` are refused
  while the agent and the PR author are the same account, which is every PR here (#44).
- The closing keyword (`Closes #<n>:`) must be the first line of the commit message. A squash
  merge keeps only commit messages, so a body-only or mid-prose keyword closes nothing (#61, #68).
- Decision records: `.trazo/project/adr/0003-review-security-github-tracked.md` (review and
  security tracked on GitHub) and `.trazo/project/adr/0010-src-canonical-trazo-pinned.md`
  (`src/` is canonical; `.trazo/` is the installed copy, never hand-edited).
- Why the import must load from the repository root: `.trazo/project/workstreams/claude-md-imports.md` (#38).
- A host receives blank templates (`src/overlay/templates/`) and `/kickoff` copies them into
  its own `.trazo/project/`; this repo's `.trazo/project/` is its own state and is never shipped.
