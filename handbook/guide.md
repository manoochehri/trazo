# Using Trazo

A practical guide: how to start a project, run it day to day, and get unstuck.
For what Trazo is and what's included, see the [README](https://github.com/manoochehri/trazo#readme). For what the overlay actually contains, see [What is `.trazo/`](overlay.md). For the daily loop and a full FAQ once a project is running, see the [playbook](playbook.md).

---

## 1. The AI team

Trazo runs a small team: you plus several Claude roles. **The agents don't talk to each other directly; they communicate through GitHub.** The PM writes issues, the engineer turns issues into pull requests, the reviewer comments on pull requests, and you approve and merge. Everything is visible, and nothing depends on a chat surviving.

| Role | Who | Where they work | Triggered by |
|---|---|---|---|
| **Owner** | You | GitHub (phone or laptop), Claude app | You |
| **PM / advisor** | Claude, the `pm` subagent pinned to Opus | Claude chat; scheduled GitHub runs | You, or a daily schedule |
| **Engineer** | Claude Code, the main session, on the model you choose | VS Code on your machine, or GitHub Actions | You, or `@claude` on an issue |
| **Reviewer** | Claude, the `reviewer` subagent pinned to Opus | GitHub pull requests | Automatically on every pull request (once the section 3 workflows are added), or on request in Claude Code |

**Neither AI keeps memory between sessions.** The repo does. Every session starts by reading the docs and ends by updating them.

| | Claude (desktop/web app) | Claude Code (VS Code / terminal / GitHub) |
|---|---|---|
| **Good at** | Planning, deciding, reviewing results, writing issues | Changing files, running tests, git, pull requests |
| **Reads** | The repo (connect GitHub under *claude.ai Settings → Connectors*) | `CLAUDE.md` automatically, then `.trazo/project/` |
| **Uses** | The **project-kickoff** skill; `.trazo/ADVISOR.md` | Role commands `/pm`, `/eng`; subagents `pm`, `reviewer`, `security`; commands (type `/`, or `/trazo` for a menu) |

---

### The team inside Claude Code: role commands and subagents
Roles live in `.claude/agents/` and commands in `.claude/commands/`:
- **Role commands:** type `/pm` to switch the session directly into the PM role for the rest of the conversation; `/eng` returns to building. While in the PM role, instructions enforce that it does not edit code or configuration. Note that because slash command frontmatter `model:` only applies to the invoking turn and tool restrictions cannot dynamically lock tools across subsequent turns, the role command enforces "no edits" via instructions.
- **Subagents:** **reviewer**, **security**, and **skeptic** are subagent-only — never role-switch commands — so a review can't grade the same conversation's own work. **pm**, **reviewer**, **security**, and **skeptic** are pinned to Opus (`model: opus`), run in their own context and can't edit code; the main session is the engineer, and its model is your choice via `/model`. A role command does not switch the model (tracked in [#116](https://github.com/manoochehri/trazo/issues/116)). The engineer role delegates to them automatically as part of `/work` and `/check-pr`, or ad hoc ("have security check this", "is this number real?"). Manage them with the built-in `/agents` command. See `.trazo/project/adr/0003-review-security-github-tracked.md`.

**You don't need to memorize commands.** Talk normally ("catch me up", "work on issue 12", "can I merge #15?", "wrap up"); `CLAUDE.md` maps requests to routines. If you want a menu, type `/trazo`. Typing `/` lists every command.

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
| `/brief` | Quick status, changes nothing |
| `/decide …` | Draft a decision record |
| `/kickoff` | New-project setup |
| ask for lessons to be promoted | note them in the project; promote by hand when working in Trazo |

**Several windows?** Fine for talking and reviewing in parallel. Two windows *editing* the same folder will collide; use git worktrees under `.worktrees/` (or Claude Code's `--worktree` flag) for isolated parallel building. See [RUNBOOK.md](https://github.com/manoochehri/trazo/blob/main/.trazo/project/RUNBOOK.md#parallel-work-git-worktrees) for worktree commands.

## 2. How you interact

Your two main tools: **a Claude chat for thinking, GitHub for approving.**

| You want to… | Do this |
|---|---|
| Think through an idea or problem | In Claude Code, `/pm` or just ask a planning question directly. From the Claude app: *"Act as the advisor for <owner>/<repo> per .trazo/ADVISOR.md."* |
| Add a task | Create a GitHub issue yourself, or ask the PM to. |
| Get work done (hands-on) | Open Claude Code in the repo and say *"work on issue 12"* (or `/work 12`). |
| Get work done (hands-off) | Comment `@claude implement this` on the issue. It opens a pull request when done. |
| Approve work | Read the reviewer's comments and CI result on the pull request, then merge. |
| Make a call | Answer `needs-decision` issues in a comment. The PM clears the label only after a comment quoting your words verbatim, from you in session or posted by you on the issue; a quote relayed by another agent does not count. |
| Know what's going on | Read the daily review on the pinned "Daily review" issue, or `.trazo/project/STATUS.md`. |

A typical loop:
```
you + PM (chat)  →  issues  →  engineer  →  pull request  →  reviewer + CI  →  you merge
                                    ↑                                              |
                                    └──────── daily PM review flags what's next ───┘
```

---

## 3. Setting up the automated team (GitHub Actions)

The automatic parts run on GitHub using Anthropic's official Claude Code GitHub Action. Three workflows:

| Workflow | Role | Runs when |
|---|---|---|
| `.github/workflows/claude.yml` | Engineer | Someone writes `@claude` in an issue or pull request |
| `.github/workflows/claude-review.yml` | Reviewer | A pull request is opened or updated |
| `.github/workflows/daily-review.yml` | PM | Every morning on a schedule (cron), plus a manual "Run workflow" button |

### One-time setup
1. **API key:** create one in the Anthropic Console. Usage is billed per token, separately from a Claude subscription. **Set a monthly spending limit in the Console.**
2. **Install the Claude GitHub app** on the repo. In Claude Code, run `/install-github-app`; it walks you through the app and the `ANTHROPIC_API_KEY` secret.
3. **Add the three workflows.** Ask Claude Code: *"Add claude.yml, claude-review.yml and daily-review.yml per handbook/guide.md section 3, using the current Claude Code Action docs. PM and reviewer on Opus, engineer on Sonnet. Cap turns per run. The daily review reads .trazo/ADVISOR.md and posts to a pinned 'Daily review' issue."*
4. **Test:** comment `@claude what's in this repo?` on any issue, and use "Run workflow" on the daily review.

### Guardrails
- The engineer only opens pull requests; branch protection means nothing reaches `main` without CI and your merge.
- CODEOWNERS still requires you for safety-critical paths, whoever wrote the change.
- Workflows get the minimum GitHub permissions they need.
- Cap turns/time per run and set the Console spending limit, so a loop can't run up a bill.

### Alternative: scheduled Claude tasks
The Claude app can also run scheduled tasks: a fresh session on a timer, with the repo attached (needs GitHub connected to Claude). Simpler to start, but it lives in your Claude account rather than the repo, so it doesn't copy to other projects. The GitHub workflows are the portable default.

---
## 4. Start a project

Trazo is installed into a repository by one script, from a release tag. It works the same on a brand-new empty repo and on one you already have. If you have an existing codebase, nothing about it changes.

### Option A: from a Claude chat (recommended for a new project)
1. Make sure the **project-kickoff** skill is saved in your Claude account.
2. Start a new chat: *"Let's kick off a new project."*
3. Answer its interview (idea, success criteria, budget, deadline, constraints, stop rule, UI, where it runs).
4. Approve the charter and plan it shows you.
5. It sets things up, or gives you instructions to run in Claude Code.

### Option B: install into a repo, then kick off
From the root of your git repository:
```bash
curl -fsSL https://raw.githubusercontent.com/manoochehri/trazo/v0.1.0/scripts/install.sh -o install.sh
bash install.sh install v0.1.0
claude
```

!!! note "No release exists yet"
    The first tag, `v0.1.0`, is cut by [#100](https://github.com/manoochehri/trazo/issues/100); the command works once it is published.
Then type `/kickoff`. Options, upgrade and uninstall are in [Install, upgrade and uninstall](install.md).

### Option C: what the installer does to an existing repo
Your repo keeps its runtime, its build system and its pipeline. The installer adds one directory, optionally an adapter for your agent, and you satisfy one contract.

1. **Declare the environment.** Trazo requires *a one-command, reproducible build/test environment an agent can run hermetically from a fresh worktree*. If you do not have one, this is the only thing to build first, whether a `Makefile` target, a `docker compose run test`, a nix shell or a devcontainer. See [What is `.trazo/`](overlay.md).
2. **Install.** The framework lands in `.trazo/` (from `src/overlay/` at the release tag), and `.trazo/project/` is created from blank templates only if it does not exist.
3. **Add the adapter for your agent.** The installer inserts it into `CLAUDE.md` and/or `AGENTS.md` between markers and copies `.claude/` for Claude Code. Any other agent reads the same `.trazo/rules.md` through its own equivalent. If your repo already has these files, everything outside the markers is left untouched; an existing `AGENTS.md` is the host's file, see [`AGENTS.md` and Trazo](agents.md).
4. **Fill in the charter.** Run `/kickoff` and answer the interview. The stop rule is the part worth taking seriously: it is the only thing that decides whether to keep going, and it has to be written before the results exist.
5. **Leave `docs/` blank, and do not copy Trazo's own state across.** A repo's Trazo state is in `.trazo/project/`, which `/kickoff` fills from the blank templates. Trazo's own `.trazo/project/` is about Trazo, not about your project.

You can mount now and keep your own layout; nothing here is a one-way choice.

### What you'll be asked to do yourself
- Approve the charter, plan, and any cloud resources (with their monthly cost)
- Enter secrets (never in chat; kickoff tells you how)
- Confirm alert emails from your cloud provider (otherwise no alerts arrive)
- Turn on settings your GitHub plan doesn't allow via the API (kickoff will say which)

---

## 5. Day to day

### A work session (Claude Code)
```
/start      reads the docs, summarizes state, proposes work, waits for your OK
  ...it works on a branch and opens a pull request...
/wrapup     updates STATUS, records decisions, updates issues, pushes
```
Then review the pull request on GitHub. If CI is green and it looks right, merge.

### Getting advice (Claude)
Start a **fresh** chat and say:
> Act as the advisor for <owner>/<repo> per .trazo/ADVISOR.md.

Ask it what you'd ask a PM: *Are we on track? Is this result real? What should we do next? Is this worth the cost?* It writes conclusions back into the repo (decision records, issues, reports).

### Making a decision
In Claude Code: `/decide <what you decided>`. It drafts a numbered record with context, alternatives, and consequences for you to approve.

### Where to look
| Question | Look at |
|---|---|
| What's going on right now? | `.trazo/project/STATUS.md` |
| What's left to do? | GitHub Issues (filter by milestone) |
| What needs me? | Issues labeled `needs-decision` |
| Why did we do X? | `.trazo/project/adr/` |
| How is experiment Y going? | `.trazo/project/workstreams/` |
| How do I deploy / roll back? | `.trazo/project/RUNBOOK.md` |
| Is the code healthy? | The **Actions** tab on GitHub |

---

## 6. Handing instructions from the advisor to the builder

When the advisor writes instructions for Claude Code, good instructions:
- **Stand alone.** A fresh session must understand them without the chat.
- **Define terms and include the numbers.** Don't say "the usual threshold."
- **Say what to verify** before relying on it.
- **Ask for the plan back first.** "Before starting, explain your plan and list anything unclear. Wait for my OK."
- **End with `/wrapup`**, so results land in the repo.

Better still: have the advisor open GitHub issues with those instructions, then tell Claude Code *"work the open issues in the current milestone."*

---

## 7. Secrets

- **Never paste a secret into any chat**, including this one. If you do by accident, replace (rotate) that key.
- **Local:** copy `.env.example` to `.env` and fill it in. It's git-ignored, and Claude Code is blocked from reading it.
- **Cloud:** use your provider's secret store, and never put a secret in the repo.
- **Check anytime:** `make scan` searches the whole git history for leaked secrets. CI runs the same check on every pull request.

---

## 8. CI, pull requests, and Dependabot

- **CI** runs on GitHub's servers every time you push or open a pull request. Results show on the pull request and in the **Actions** tab. You don't host anything.
- **Red X?** Click it, open the failed job, and paste the error to Claude Code: *"CI failed with this, fix it."*
- **Dependabot** opens pull requests weekly when tools have newer versions (grouped by type). If CI is green, merge. If red, the new version changed something; let Claude Code look.
- **Branch protection** (set at kickoff) means nothing reaches `main` without a passing pull request.

---

## 9. Deploying

**Trazo ships no deploy target.** That is deliberate: the overlay governs how agents work, and your build and your cloud are yours. Kickoff records where the project runs; the rest is yours to wire.

Whatever you choose, record these in `.trazo/project/RUNBOOK.md`:
- the one command that deploys, and the one that shows what is running
- rollback to the previous version
- the budget alert, and the monthly cost you expect
- teardown: one command that removes everything

If you deploy from CI, gate it on a GitHub `production` environment so a deploy needs your approval — one click, no cloud login.

**Cost tip:** estimates often miss disks, public IP addresses, and storage. Ask for a per-resource price list before approving.

---

## 10. Improving Trazo

Trazo is mounted onto a host repo, not forked from a template. So there is no automated
round trip between a project and the overlay, and that is deliberate: a mounted project
has its own runtime, its own docs and its own decisions, and there is no merge that can
tell which of the two should win.

**To take an improvement into a mounted project:** copy the changed files from Trazo into
it, or re-run `/kickoff`, and review the diff like any other change. The project's own
decision records win on anything they disagree about.

**To improve Trazo from what a project taught you:** write it down in that project first —
its decision records and workstreams are the right home, and they are the project's to
keep. When you are next working in Trazo, promote what is genuinely reusable by hand, on a
branch, by promoting reusable guidance into `.trazo/rules.md` or a new ADR and including it in the versioned change.

**Working on Trazo itself:** open the Trazo repo in Claude Code as you would any project. `src/` is the product and is where every change is made; `.trazo/` is the pinned install that governs the repo and is never hand-edited, so a rule you change in `src/` governs this repo only after it is released. Its own state lives in `.trazo/project/`, which is never shipped to hosts; the blank scaffolding hosts receive is under `src/overlay/templates/`. Changes go through pull requests like anything else.

**Releasing:** a release is a GitHub milestone named `vX.Y.Z`. Its description is the goal and its issues are the scope. When it has 0 open issues and CI is green, bump `.template/VERSION` with the changelog entry and run `make release`, which refuses while the milestone has open issues. Tags are immutable: never move one that exists.

---

## 11. Troubleshooting

| Problem | What to do |
|---|---|
| **The AI forgot what we were doing** | Start a fresh session. Claude Code: `/start`. Advisor: point it at `.trazo/ADVISOR.md`. That's what the docs are for. |
| **A session got long and confused** | Same: start fresh. Long sessions degrade; the repo doesn't. |
| **"Safeguards flagged this message" errors** | Sessions heavy on security topics (keys, permissions, network setup) can trip automatic filters by mistake. Start a fresh session; state is in the repo. |
| **Cloud login expired** | Sign in again (e.g., `aws login --profile <name>`). For deploys, use the GitHub workflow instead; it doesn't need your login. |
| **A scheduled job didn't run** | Check whether it was installed after its scheduled time. Ask for a "first run verified" check. |
| **Disk or cost growing unexpectedly** | Ask for status with disk-days-remaining and month-to-date cost. Recheck retention settings. |
| **An agent wants to loosen a safety limit** | Only you change those: CODEOWNERS requires your review. Ask it to show the evidence and write a decision record first. |
| **`@claude` does nothing** | Check the Claude GitHub app is installed, the `ANTHROPIC_API_KEY` secret exists, and the workflow run in the Actions tab for errors. |
| **API bill surprise** | Set a Console spending limit; cap turns per workflow run; turn off workflows you don't use. |
| **Results look great** | Ask how they're measured. Against external reality, with sample sizes? Or against the system's own assumptions? |

---

## 12. Glossary

- **Charter:** the one-page why/goal/constraints/stop-rule document.
- **Decision record:** a short numbered file explaining one decision; never edited, only superseded.
- **Workstream:** one feature, experiment, or strategy, with its hypothesis, tests, and evidence.
- **CI:** automatic checks on every change (tests, lint, secret scan, build).
- **Pull request (PR):** a proposed change, reviewed and checked before merging into `main`.
- **Dependabot:** GitHub's bot that proposes version updates.
- **Milestone:** a GitHub milestone `vX.Y.Z` is a release: the goal in its description, the scope as its issues. The tag is cut at 0 open issues.
- **Pinned install:** `.trazo/`, the copy of `src/` that governs a repo; never hand-edited.
- **Deploy target:** where the project runs; Trazo ships none.
- **GitHub Action / workflow:** an automated job defined in `.github/workflows/`, run by GitHub on its own servers.
- **`@claude`:** mentioning Claude in an issue or pull request, which triggers the engineer workflow.
- **Stop rule:** the evidence, decided in advance, that means stop or rethink.
