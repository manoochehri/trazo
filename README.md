<img src="handbook/assets/logo.svg" width="64" height="64" alt="Trazo logo">

# Trazo

**A governance overlay for AI coding agents. Mount it on any repo — new or existing — and agents start working to rules instead of improvising.**

Trazo is built specifically for **Claude Code**, and opinionated in two places: how agents hand work to each other, and whether a result is real. It is deliberately neutral about everything else — language, framework, and where your code runs.

You bring a repo, or an idea. Trazo adds a pinned `.trazo/` overlay and a thin `.claude/` adapter on top: rules, a charter with a pre-registered stop rule, decision records that outlive a session, and three agents that check each other's work. Your code, your build, your deploy — unchanged.

> Status: early, and **not yet released**. Distilled from one real project; expect rough edges. The first release, `v0.1.0`, is tracked by the [v0.1.0 milestone](https://github.com/manoochehri/trazo/milestone/1); no tag exists until it closes.

[📖 Full documentation](https://manoochehri.github.io/trazo/) · new here? [the guide](handbook/guide.md) · already running a project? [the playbook](handbook/playbook.md)

---

## Why this exists

Almost every serious repo already exists, with its own runtime, toolchain and pipeline. Point a coding agent at it and the same problems happen again and again:

- **Agents forget.** Sessions end, contexts reset, and plans or decisions kept only in chat are lost.
- **Copy-paste glue.** Moving notes between an "advisor" chat and a coding agent by hand loses information.
- **Secrets leak easily.** Keys end up in `.env` files, logs, commits, or chat.
- **No project management.** No charter, no milestones, no record of *why* something was decided.
- **Results look better than they are.** Agents grade work against their own assumptions instead of reality.
- **Safety limits drift.** An agent "helpfully" loosens a threshold nobody approved.

A starter template does not fix these — it fixes them for the empty repo you start from, and you are not starting from one. And the tool it mandates is the tool you were trying to escape.

Trazo's answer: **the repo is the memory, and the rails are mounted rather than imposed.** Everything durable — goal, budget, design, decisions, status, results — lives as plain markdown in the repo, so any fresh agent session reads it and picks up where the last one stopped.

---

## What you get

### What the installer gives your repo

`install.sh` writes only what is in `src/overlay/` and `src/adapters/`, and nothing else:

| Area | What's included |
|---|---|
| **The rules** | `.trazo/rules.md` — tool-neutral, read once by any tool's adapter |
| **Design records** | `.trazo/ARCHITECTURE.md`, `.trazo/ADVISOR.md` (framework files, overwritten on upgrade) |
| **Blank project state** | `.trazo/project/` created from templates: `charter/charter.md`, `STATUS.md`, `PLAN.md`, `RUNBOOK.md`, `SKEPTIC_BAR.md`, `reports/`, plus blank ADR and workstream templates. Never overwritten on upgrade |
| **The adapter** | `CLAUDE.md` and `.claude/` for Claude Code, `AGENTS.md` for other agents, written between Trazo's own markers |
| **AI team** | If you use Claude Code, `.claude/agents/`: `reviewer`, `security`, `skeptic` and `pm`, **pinned to Opus**; the first three are **subagent-only**. `/pm` and `/eng` switch the session's role (they do not switch the model; that is your choice via `/model`). None of them edits a file, but each records its verdict on GitHub, and `/pm` may also reshape the issue graph. See [the team](handbook/team.md) |
| **Commands** | If you use Claude Code, `.claude/commands/`: `/trazo` (menu), `/kickoff`, `/start`, `/work`, `/check-pr`, `/pm`, `/eng`, `/wrapup`, `/brief`, `/decide` — or just ask in plain English |
| **Secret-read denial** | If you use Claude Code, `.claude/settings.json` denies Claude Code reads of `.env`, `.env.*`, `secrets/`, `*.pem` and `*.key` (only if you have no `settings.json` of your own) |

### What `/kickoff` sets up, or asks you to add

Run after install. It interviews you, then writes and configures:

- the charter (goal, budget, success criteria, stop rule) and `PLAN.md`, shown to you for approval before anything is built
- a `SKEPTIC_BAR.md` specialised to what counts as a valid result in your domain
- GitHub labels, milestones and first issues; a Project board if `gh` supports it
- a ruleset on `main` (no force pushes or deletion, pull request and passing CI required) and GitHub secret scanning with push protection
- `make setup`, `make test` and `make scan` run once, with failures fixed
- where the project runs, recorded in the runbook and architecture; if it deploys anywhere, a budget alert and the teardown command

What neither step provides: **CI workflows, gitleaks, pre-commit, a Dockerfile, a PR template, `.env.example`, `scripts/put_secret.sh`, or CODEOWNERS.** Those are this repository's own harness. The installer prints suggested CODEOWNERS lines for you to add (safety limits only count if you review them), and CI and secret scanning are yours to bring.

Beneath the files, the design has two layers. The second is the one that matters.

**The mechanical rails** — table stakes, and easy to copy:

- worktree isolation per change, so two agents never fight over a dirty tree
- role separation, so an agent never grades its own work
- GitHub as the state engine — issues, pull requests, labels — not a database
- secrets discipline: nothing secret is ever read, printed or committed by an agent

**The judgment layer** — the reason to keep going:

- a **charter** with a goal, a budget, success criteria, and a **stop rule** written *before* the results exist
- **evidence with sample sizes**, judged against external ground truth, never against the agent's own model
- a **skeptic** subagent that tries to break every quantitative result before it is acted on

The one thing a **mounted** repo must supply is an environment, not a tool: *a one-command, reproducible build/test environment an agent can run hermetically from a fresh worktree.* Docker, nix, devcontainers or a `Makefile` all satisfy it. Trazo mandates nothing — that mistake was already made once, with a cloud provider.

---

## Requirements

- A GitHub account and the [GitHub CLI](https://cli.github.com/) (`gh auth login`)
- [Claude Code](https://docs.claude.com/) (or another agent that can read `CLAUDE.md` and run commands)
- A way to run your tests in one command — see the mount-time contract above. For a *new* Trazo-owned repo, that means [uv](https://docs.astral.sh/uv/) and Docker.
- Optional: an account with wherever your project deploys; Trazo ships no deploy target

---

## Quick start

Trazo mounts onto a repo you already have, or onto a new empty one.

### Install

From the root of your git repository (a new empty one, or the one you already have):

```bash
curl -fsSL https://raw.githubusercontent.com/manoochehri/trazo/v0.1.0/scripts/install.sh -o install.sh
bash install.sh install v0.1.0
```

> **No release exists yet.** The first tag, `v0.1.0`, is cut by [#100](https://github.com/manoochehri/trazo/issues/100); the command works once it is published.

Your repo keeps its runtime, its build system and its pipeline. The installer copies the framework into `.trazo/`, adds the adapter for your agent (`.claude/` and `CLAUDE.md` if you use Claude Code, `AGENTS.md` for other agents; if your repo already has them, the installer merges between its own markers and never replaces yours), and creates `.trazo/project/` from blank templates. Full options, upgrade and uninstall: [Install, upgrade and uninstall](https://manoochehri.github.io/trazo/install/).

Then:

1. **Declare the environment** — one command that runs your tests hermetically from a fresh worktree. If you don't have one, that's the only thing to build first.
2. **Run `/kickoff`** and answer the interview. The stop rule is the part worth taking seriously: it is the only thing that decides whether to keep going, and it has to be written before the results exist.
3. **Leave `docs/` and Trazo's own state alone.** A repo's Trazo state lives in `.trazo/project/`, created blank for you; never copy this repository's own `.trazo/project/` across, because it is about Trazo, not your project.

The layout is documented in [What is `.trazo/`](https://manoochehri.github.io/trazo/overlay/).

Kickoff asks about: the idea, measurable success criteria, budget and deadline, hard constraints, a stop rule, UI needs, and where it runs. It shows you the charter and plan and waits for your OK before building anything.

---

## Day-to-day workflow

```
/start    → agent reads the docs, summarizes state, proposes the session's work, waits for OK
   ...work on a branch, open a pull request...
/wrapup   → agent updates STATUS, records decisions, updates issues, pushes, opens/updates the PR
```

- **Tasks** live in GitHub Issues, grouped by milestone. Anything waiting on you is labeled `needs-decision`. The PM removes that label only to record your decision: right after a comment that quotes your words verbatim, typed by you in the session or posted by you on the issue. A quote relayed by another agent never counts.
- **Advice:** start a fresh session (a strong reasoning model works best) and say *"act as advisor per .trazo/ADVISOR.md"*. It reviews progress, evidence quality, safety, cost, and the stop rule, and writes its conclusions into the repo.
- **Decisions:** `/decide <what>` drafts a numbered decision record for your approval.

### How state is organized

| File | Changes | Answers |
|---|---|---|
| `.trazo/project/charter/charter.md` | Rarely | Why, goal, success criteria, budget, constraints, stop rule |
| `.trazo/project/PLAN.md` | When dates or scope change | Milestones and risks |
| `.trazo/ARCHITECTURE.md` | When the system changes (framework file, upgraded with Trazo) | How it's built (with diagram) |
| `.trazo/project/STATUS.md` | Every session (replaced) | Where things stand right now |
| `.trazo/project/adr/` | Append-only | What was decided and why |
| `.trazo/project/workstreams/` | As work progresses | Each feature/experiment: hypothesis, test, evidence, status |
| `.trazo/project/reports/` | Generated | Results over time |
| `.trazo/project/RUNBOOK.md` | When procedures change | How to run, deploy, roll back, recover |
| GitHub Issues | Constantly | What's being done, by when |

---

## Secrets

Secrets never go in git, images, logs, or chat.

- **Local:** keep secrets in a git-ignored `.env`; Claude Code is denied read access to it.
- **Cloud:** your provider's secret store, injected at runtime. Trazo ships no secret-entry script; the human enters secrets, never an agent.
- **Enforced by:** if you use Claude Code, `.claude/settings.json` denies agent reads of `.env` and `secrets/`, and `/kickoff` turns on GitHub secret scanning and push protection. Scanning in CI (this repository uses gitleaks) is yours to add.

---

## CI and deployment

The installer adds no CI. Your repo keeps its own pipeline, and `/kickoff` requires its passing checks on `main`. For reference, this repository's own workflows (`.github/workflows/`, not shipped) run gitleaks, ruff, pytest, a Docker build and a docs check on every pull request.

**Trazo ships no deploy target.** Your build, your cloud — that is the point of an overlay. Kickoff records where your project runs, and the runbook carries the budget alert and teardown command. Secrets go in your provider's secret store, never in git.

Suggested branch flow:
```
feature branch → pull request (CI) → main → deploy branch → approve → deployed
```

---

## How Trazo improves

Trazo's own memory lives in `.template/`: `CHANGELOG.md` and the decisions behind its design. `VERSION` names the version being cut, so before `v0.1.0` it does not describe a release.

**A release is a GitHub milestone.** The milestone `vX.Y.Z` carries the release goal in its description and its scope as its issues. The tag is cut when that milestone has 0 open issues and CI is green, and `make release` refuses to tag while any are open. Tags are immutable: a published tag is never moved, so a host that pinned it always gets the same files. A version is a coherent body of work, not one per merged pull request.

**`src/` is the product; `.trazo/` is the pinned install.** All changes to the framework are made in `src/` and ship with the next version. This repository is itself governed by the pinned copy in `.trazo/`, which is never hand-edited, so editing a rule never changes the rules governing the edit. The cost is deliberate: a rule fix cannot govern this repository until it is released.

Trazo is **mounted** onto a host repo, not forked, so there is no upstream to sync with and no automated way to send a host project's lessons back. A mounted project records its own lessons in its own decision records. To take an improvement in, run `bash install.sh upgrade <tag>` (add `--dry-run` to preview): it replaces the framework files in `.trazo/`, never touches `.trazo/project/`, and skips adapter files you have edited. See [Install, upgrade and uninstall](https://manoochehri.github.io/trazo/install/).

---

## Repository layout

```
src/                       the product: everything a host receives, edited here
  overlay/                 tool-neutral core: rules.md, ADVISOR.md, ARCHITECTURE.md
    templates/             blank charter, adr, workstream and docs/ for a host
  adapters/                AGENTS.md, CLAUDE.md and claude/ (commands, agents)
.trazo/                    the pinned install that governs this repo; never hand-edited
  rules.md                 the rules, tool-neutral
  project/                 this repo's own state; never shipped, never overwritten
    charter/               goal, budget, success criteria, stop rule
    adr/                   numbered decision records (append-only)
    workstreams/           one file per idea, with hypothesis and evidence
    STATUS.md PLAN.md RUNBOOK.md SKEPTIC_BAR.md reports/
CLAUDE.md                  the Claude Code adapter for .trazo/rules.md
.claude/                   commands, agents, and permissions
.github/                   CI, PR template, CODEOWNERS, issue templates, Dependabot
.template/                 Trazo's release version and changelog
handbook/                  the published documentation
scripts/                   install.sh (what a host runs) and this repo's helpers (scan.sh, release.sh)
tests/                     guard tests for the overlay itself
Dockerfile                  container (toolchain + tests; no service)
Makefile, pyproject.toml   tooling
```

A host receives `src/overlay/` plus the adapter for its agent, and starts from the blank templates, so it never inherits this repository's charter, decision records or STATUS. In a host, `.trazo/project/` is the host's own state; upgrades overwrite the framework files beside it and never touch `project/`.

---

## FAQ

**Can I use this for private projects?** Yes. Run the installer in any private repo you already have; nothing is sent anywhere.

**I already have a repo. Do I have to delete my files first?** No — that is the point of the overlay. Your code, build and pipeline stay; you add `.trazo/`, plus an adapter for whichever agent you use, and satisfy the mount-time contract.

**Does it cost anything?** Trazo is free. GitHub Actions is free for public repos and includes a monthly allowance for private ones. Cloud costs depend on your deploy target; if the project deploys, kickoff records a budget alert and the teardown command in the runbook.

**Not Python?** Nothing in `.trazo/` or `.claude/` assumes a language. `pyproject.toml`, the Makefile targets and the CI test job are this repo's own harness — a mounted repo replaces them with whatever runs its tests.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
