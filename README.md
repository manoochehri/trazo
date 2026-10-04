<img src="handbook/assets/logo.svg" width="64" height="64" alt="Trazo logo">

# Trazo

**A governance overlay for AI coding agents. Mount it on any repo — new or existing — and agents start working to rules instead of improvising.**

Trazo is built specifically for **Claude Code**, and opinionated in two places: how agents hand work to each other, and whether a result is real. It is deliberately neutral about everything else — language, framework, and where your code runs.

You bring a repo, or an idea. Trazo adds a pinned `.trazo/` overlay and a thin `.claude/` adapter on top: rules, a charter with a pre-registered stop rule, decision records that outlive a session, and three agents that check each other's work. Your code, your build, your deploy — unchanged.

> Status: early. Distilled from one real project; expect rough edges. See [`.template/VERSION`](.template/VERSION) for the current version.

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

Two layers. The second is the one that matters.

**The mechanical rails** — table stakes, and easy to copy:

- worktree isolation per change, so two agents never fight over a dirty tree
- role separation, so an agent never grades its own work
- GitHub as the state engine — issues, pull requests, labels — not a database
- secrets discipline: nothing secret is ever read, printed or committed by an agent

**The judgment layer** — the reason to keep going:

- a **charter** with a goal, a budget, success criteria, and a **stop rule** written *before* the results exist
- **evidence with sample sizes**, judged against external ground truth, never against the agent's own model
- a **skeptic** subagent that tries to break every quantitative result before it is acted on

| Area | What's included |
|---|---|
| **The rules** | `.trazo/rules.md` — tool-neutral, read once by any tool's adapter |
| **The judgment layer** | `.trazo/project/charter/` — goal, budget, success criteria, stop rule |
| **Decision records** | `.trazo/project/adr/` — numbered, append-only, supersede never edit |
| **Workstreams** | `.trazo/project/workstreams/` — one file per idea, with hypothesis and evidence |
| **Design records** | `.trazo/ARCHITECTURE.md`, `.trazo/ADVISOR.md` (framework files, overwritten on upgrade) |
| **AI team** | `/pm` and `/eng` switch the session's role. `reviewer`, `security`, `skeptic` and `pm` are subagents **pinned to Opus**; `reviewer`, `security` and `skeptic` are **subagent-only**. The model of the main session is your choice (`/model`); a role command does not switch it. None of them edits a file — but each records its verdict on GitHub, and `/pm` may also reshape the issue graph. See [the team](team.md) |
| **Commands** | `/trazo` (menu), `/kickoff`, `/start`, `/work`, `/check-pr`, `/pm`, `/eng`, `/wrapup`, `/brief`, `/decide` — or just ask in plain English |
| **Secrets from day one** | `.gitignore`, `.env.example`, gitleaks (pre-commit + CI), `scripts/put_secret.sh` |
| **Containers** | Dockerfile (non-root, uv) — the toolchain and the tests, no service |
| **CI** | GitHub Actions on every PR: secret scan, lint, tests, Docker build, docs check |
| **Guardrails** | CODEOWNERS on safety-critical paths, PR template with doc checkboxes, branch protection at kickoff |

The one thing a **mounted** repo must supply is an environment, not a tool: *a one-command, reproducible build/test environment an agent can run hermetically from a fresh worktree.* Docker, nix, devcontainers or a `Makefile` all satisfy it. Trazo mandates nothing — that mistake was already made once, with a cloud provider.

---

## Requirements

- A GitHub account and the [GitHub CLI](https://cli.github.com/) (`gh auth login`)
- [Claude Code](https://docs.claude.com/) (or another agent that can read `CLAUDE.md` and run commands)
- A way to run your tests in one command — see the mount-time contract above. For a *new* Trazo-owned repo, that means [uv](https://docs.astral.sh/uv/) and Docker.
- Optional: an account with wherever your project deploys; Trazo ships no deploy target

---

## Quick start

Two different jobs: **starting a new repo with Trazo in it**, and **mounting Trazo onto a repo you already have**. If you have an existing codebase, you want the second.

### Install

From the root of your git repository (a new empty one, or the one you already have):

```bash
curl -fsSL https://raw.githubusercontent.com/manoochehri/trazo/v0.1.0/scripts/install.sh -o install.sh
bash install.sh install v0.1.0
```

Your repo keeps its runtime, its build system and its pipeline. The installer copies the framework into `.trazo/`, adds the adapter for your agent (`.claude/` and `CLAUDE.md` if you use Claude Code, `AGENTS.md` for other agents; if your repo already has them, the installer merges between its own markers and never replaces yours), and creates `.trazo/project/` from blank templates. Full options, upgrade and uninstall: [Install, upgrade and uninstall](https://manoochehri.github.io/trazo/install/).

Then:

1. **Declare the environment** — one command that runs your tests hermetically from a fresh worktree. If you don't have one, that's the only thing to build first.
2. **Run `/kickoff`** and answer the interview. The stop rule is the part worth taking seriously: it is the only thing that decides whether to keep going, and it has to be written before the results exist.
3. **Leave `docs/` and Trazo's own state alone.** A repo's Trazo state lives in `.trazo/project/`, created blank for you; never copy this repository's own `.trazo/project/` across, because it is about Trazo, not your project.

The layout is documented in [What is `.trazo/`](https://manoochehri.github.io/trazo/overlay/).

Kickoff asks about: the idea, measurable success criteria, budget and deadline, hard constraints, a stop rule, UI needs, and where it runs. It shows you the charter and plan before building anything, and shows every cloud resource and its cost before creating it.

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

- **Local:** copy `.env.example` to `.env` (git-ignored; Claude Code is denied read access).
- **Cloud:** the provider's secret store, injected at runtime. For AWS: `scripts/put_secret.sh <name>` prompts without echoing.
- **Enforced by:** gitleaks as a pre-commit hook and in CI (full history), GitHub secret scanning and push protection (turned on at kickoff), and `make scan` for a manual check.

---

## CI and deployment

CI runs on GitHub's own servers (no extra system needed). Workflows live in `.github/workflows/`; results appear in the repo's **Actions** tab and on each pull request.

Every pull request runs: gitleaks, ruff, pytest, a Docker build, and a check that deploy workflow changes come with ARCHITECTURE or RUNBOOK updates.

**Trazo ships no deploy target.** Your build, your cloud — that is the point of an overlay. Kickoff records where your project runs, and the runbook carries the budget alert and teardown command. Secrets go in your provider's secret store, never in git.

Suggested branch flow:
```
feature branch → pull request (CI) → main → deploy branch → approve → deployed
```

---

## How Trazo improves

Trazo's own memory lives in `.template/`: `VERSION`, `CHANGELOG.md`, the lessons it has learned, and the decisions behind its design.

| File | Purpose |
|---|---|
| `VERSION` | The version being cut; the git tag of the same name is what a host pins to |
| `CHANGELOG.md` | What changed, by version |
| `LESSONS.md` | Real problems from real projects, and how the overlay now prevents them |
| `decisions/` | Why the overlay is designed this way |

**A release is a GitHub milestone.** The milestone `vX.Y.Z` carries the release goal in its description and its scope as its issues. The tag is cut when that milestone has 0 open issues and CI is green, and `make release` refuses to tag while any are open. Tags are immutable: a published tag is never moved, so a host that pinned it always gets the same files. A version is a coherent body of work, not one per merged pull request.

**`src/` is the product; `.trazo/` is the pinned install.** All changes to the framework are made in `src/` and ship with the next version. This repository is itself governed by the pinned copy in `.trazo/`, which is never hand-edited, so editing a rule never changes the rules governing the edit. The cost is deliberate: a rule fix cannot govern this repository until it is released.

Trazo is **mounted** onto a host repo, not forked, so there is no upstream
to sync with and no automated way to send a host project's lessons back. A mounted project
records its own lessons in its own decision records; copy files across (or re-run
`/kickoff`) to take an improvement in, and the host's decisions win on any conflict.

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
.template/                 Trazo's own memory: version, changelog, lessons, decisions
handbook/                  the published documentation
scripts/                   helper scripts (put_secret.sh, scan.sh, release.sh)
tests/                     guard tests for the overlay itself
Dockerfile                  container (toolchain + tests; no service)
Makefile, pyproject.toml   tooling
```

A host receives `src/overlay/` plus the adapter for its agent, and starts from the blank templates, so it never inherits this repository's charter, decision records or STATUS. In a host, `.trazo/project/` is the host's own state; upgrades overwrite the framework files beside it and never touch `project/`.

---

## FAQ

**Can I use this for private projects?** Yes. Run the installer in any private repo you already have; nothing is sent anywhere.

**I already have a repo. Do I have to delete my files first?** No — that is the point of the overlay. Your code, build and pipeline stay; you add `.trazo/`, plus an adapter for whichever agent you use, and satisfy the mount-time contract.

**Does it cost anything?** Trazo is free. GitHub Actions is free for public repos and includes a monthly allowance for private ones. Cloud costs depend on your deploy target; kickoff sets a budget alert first.

**Not Python?** Nothing in `.trazo/` or `.claude/` assumes a language. `pyproject.toml`, the Makefile targets and the CI test job are this repo's own harness — a mounted repo replaces them with whatever runs its tests.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
