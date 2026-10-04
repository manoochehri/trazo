# The team

Trazo runs a small team: you plus several Claude roles, talking to each other through GitHub, not through chat memory.

## Roles and agents

| Role / Agent | Command | Model | Use for | Edits files? | Updates GitHub? |
|---|---|---|---|---|---|
| Engineer (main session) | `/eng` | your choice (see below) | Building: code, tests, git, pull requests | Yes | Yes |
| PM / advisor | `/pm` | Opus (the `pm` subagent; the `/pm` command keeps your session's model) | Status, planning, priorities, "is this result real?", charter/budget/stop rule, writing issues | No | Issues only — labels, parent/sub-issue, blocked-by, milestone, assignee, type, plus comments. Never rewrites an issue `--body`, never closes one |
| Reviewer | subagent only | Opus | Reviewing pull requests and diffs before merge | No | Verdict, as a comment on the pull request |
| Security | subagent only | Opus | Secrets, permissions, workflows, dependencies, infra, repo security settings | No | Findings as a PR comment, or a new issue |
| Skeptic | subagent only | Opus | Breaking a research/analysis result before it is acted on | No | Verdict, as a comment on the pull request or issue |

**Which model runs?** The four subagents (`pm`, `reviewer`, `security`, `skeptic`) are pinned to Opus in their frontmatter, so they run on Opus wherever they are invoked. The main session is the engineer, and its model is whatever you chose with `/model`. A role command does not switch it: `/pm` changes the role for the rest of the conversation, not the model, so for a long planning conversation pick Opus yourself. Pinning the main session's model is tracked in [#116](https://github.com/manoochehri/trazo/issues/116).

**No role other than the engineer edits a file** — that is the invariant, and it is why a review cannot quietly grade the same conversation's work. But "no file edits" is not "read-only": every one of these four *writes to GitHub*. The PM reshapes the issue graph, and the reviewer, security and skeptic agents all record their verdict where the next session can see it, because a verdict that lives only in the conversation gates nothing.

!!! note "Review verdicts are comments, not approvals"

    Reviewer, security and skeptic post `gh pr review --comment`, never `--approve` or `--request-changes`. GitHub rejects both while the agent and the PR author are the same account — which is every pull request here, because agents share the owner's identity ([#44](https://github.com/manoochehri/trazo/issues/44)). The moment agents get their own identity, these become real blocking reviews. Until then, **a green CI run is your merge gate, not a reviewer approval.**

**`needs-decision` is the owner's gate.** The PM removes the label only to record your decision, in the same step as a comment that opens `Owner decision (<date>):`, quotes your words verbatim, and says where you gave them: in the session, typed by you, or the URL of a comment you wrote on the issue or PR. A quote relayed by another agent never counts, even if it claims to be verbatim. The PM never clears the label on its own judgment, and never applies the decision itself; engineers build from the issue.

They can be used in two ways:
1. **Direct role switching:** Type `/pm` in Claude Code to switch into the PM role for the rest of the conversation; `/eng` returns to building. Reviewer, security, and skeptic are subagent-only — never role-switch commands — so a review can't grade the same conversation's own work (see `.trazo/project/adr/0003-review-security-github-tracked.md`).
2. **Subagent delegation:** The same four roles are defined in `.claude/agents/` as Opus subagents (`model: opus`) that never edit files but do post verdicts to GitHub. In engineer mode, Claude Code delegates to reviewer and security automatically as part of `/work` and `/check-pr`, or ad hoc, without switching the whole conversation.

## Commands

You don't need to memorize these — `CLAUDE.md` maps plain-English requests to the right one, and `/trazo` shows a menu. Typing `/` in Claude Code lists all of them.

| Command | Does |
|---|---|
| `/trazo` | Menu of what you can do right now |
| `/start` / `/wrapup` | Begin / end a work session |
| `/work 12` | Implement issue #12 → pull request (reviewer checks it first) |
| `/check-pr 15` | Review pull request #15 (reviewer, plus security if needed) |
| `/pm` | Switch session to PM role (planning, priorities, issues) |
| `/eng` | Return session to engineer role (code, tests, PRs) |
| ask the **security** subagent | Secrets, permissions, infra (no role switch) |
| ask the **reviewer** subagent | PRs, diffs, safety (no role switch) |
| ask the **skeptic** subagent | Break a research/analysis result before it counts (no role switch) |
| `/brief` | Quick status, changes nothing |
| `/decide …` | Draft a decision record |
| `/kickoff` | New-project setup |
| note a lesson for Trazo | record it in the project; promote by hand when working in Trazo |

## Plain English → routine

The owner shouldn't need to remember commands. `CLAUDE.md` maps requests like these to a routine or role:

| If you say something like… | It does |
|---|---|
| "catch me up", "where are we", "what's next" | `/start` routine (or `/pm` for strategy questions) |
| "what can I do", "help", "menu" | `/trazo` |
| "work on issue 12", "fix X" | `/work` routine |
| "is this PR ok", "review #15", "can I merge" | `/check-pr` routine (or ask the **reviewer** subagent directly) |
| "is this secure", "check permissions" | ask the **security** subagent |
| "is this number real?", "poke holes in this analysis" | ask the **skeptic** subagent |
| "should we…", "is this worth it", "plan the next milestone" | `/pm` |
| "back to building", "ready to code" | `/eng` |
| "we decided…" | `/decide` routine |
| "wrap up", "done for today" | `/wrapup` routine |
| "GitHub/CI says …" (settings, failures) | handled directly; ask the **security** subagent for protection/permission settings |

See the [playbook](playbook.md) for how this plays out over a normal day, and the [guide](guide.md) for setting up the optional GitHub Actions versions of the PM and reviewer.
