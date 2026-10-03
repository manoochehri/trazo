<img src="handbook/assets/logo.svg" width="64" height="64" alt="Trazo logo">

# Trazo

**A governance overlay for AI coding agents. Mount it on any repo — new or existing — and agents start working to rules instead of improvising.**

Trazo is built specifically for **Claude Code**, and opinionated in two places: how agents hand work to each other, and whether a result is real. It is deliberately neutral about everything else — language, framework, and where your code runs.

You bring a repo, or an idea. Trazo adds a `.trazo/` overlay and a thin `.claude/` adapter on top: rules, a charter with a pre-registered stop rule, decision records that outlive a session, and three agents that check each other's work. Your code, your build, your deploy — unchanged.

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
| **The judgment layer** | `.trazo/charter/` — goal, budget, success criteria, stop rule |
| **Decision records** | `.trazo/adr/` — numbered, append-only, supersede never edit |
| **Workstreams** | `.trazo/workstreams/` — one file per idea, with hypothesis and evidence |
| **Design records** | `.trazo/specs/`, `.trazo/ARCHITECTURE.md`, `.trazo/ADVISOR.md` |
| **AI team** | `/pm` and `/eng` switch the session's role. `reviewer`, `security` and `skeptic` are **subagent-only**, Opus. None of them edits a file — but each records its verdict on GitHub, and `/pm` may also reshape the issue graph. See [the team](team.md) |
| **Commands** | `/trazo` (menu), `/kickoff`, `/start`, `/work`, `/check-pr`, `/pm`, `/eng`, `/wrapup`, `/brief`, `/decide` — or just ask in plain English |
| **Secrets from day one** | `.gitignore`, `.env.example`, gitleaks (pre-commit + CI), `scripts/put_secret.sh` |
| **Containers** | Dockerfile (non-root, uv) — the toolchain and the tests, no service |
| **CI** | GitHub Actions on every PR: secret scan, lint, tests, Docker build, infra lint, docs check |
| **Guardrails** | CODEOWNERS on safety-critical paths, PR template with doc checkboxes, branch protection at kickoff |
| **Deploy (optional)** | Pluggable targets: none, Fly.io, AWS (budget alerts + GitHub OIDC + ECR), GCP (stub) |

The one thing a **mounted** repo must supply is an environment, not a tool: *a one-command, reproducible build/test environment an agent can run hermetically from a fresh worktree.* Docker, nix, devcontainers or a `Makefile` all satisfy it. Trazo mandates nothing — that mistake was already made once, with a cloud provider.

---

## Requirements

- A GitHub account and the [GitHub CLI](https://cli.github.com/) (`gh auth login`)
- [Claude Code](https://docs.claude.com/) (or another agent that can read `CLAUDE.md` and run commands)
- A way to run your tests in one command — see the mount-time contract above. For a *new* Trazo-owned repo, that means [uv](https://docs.astral.sh/uv/) and Docker.
- Optional: a Fly.io, AWS, or GCP account if the project deploys somewhere

---

## Quick start

Two different jobs: **starting a new repo with Trazo in it**, and **mounting Trazo onto a repo you already have**. If you have an existing codebase, you want the second.

### Option A: let Claude do it (new project)
In a Claude session that has the **project-kickoff** skill, say:

> Let's kick off a new project.

It interviews you, writes the charter and plan for your approval, creates the repo from this template, and sets everything up.

### Option B: by hand (new repo)
```bash
gh repo create my-project --private --template manoochehri/trazo --clone
cd my-project
make setup          # installs dependencies and git hooks
claude              # start Claude Code in the repo
```
Then type `/kickoff`.

### Option C: mounting onto a repo you already have
Your repo keeps its runtime, its build system and its pipeline.

1. **Declare the environment** — one command that runs your tests hermetically from a fresh worktree. If you don't have one, that's the only thing to build first.
2. **Copy `.trazo/` in** from this repository. That is the whole overlay, and it is tool-neutral.
3. **Add the adapter for your agent.** `.claude/` if you use Claude Code; any other agent reads the same `.trazo/rules.md` through its own equivalent. If your repo already has a `.claude/` or `CLAUDE.md`, merge into it rather than replacing it. An `AGENTS.md` is yours as well — it describes your codebase, while Trazo governs the work done on it ([`AGENTS.md` and Trazo](https://manoochehri.github.io/trazo/agents/)).
4. **Run `/kickoff`** and answer the interview. The stop rule is the part worth taking seriously: it is the only thing that decides whether to keep going, and it has to be written before the results exist.
5. **Leave `docs/` blank.** It is per-project scaffolding — do not copy this repo's own `docs/` across.

The layout is documented in [What is `.trazo/`](https://manoochehri.github.io/trazo/overlay/).

Kickoff asks about: the idea, measurable success criteria, budget and deadline, hard constraints, a stop rule, UI needs, and where it runs. It shows you the charter and plan before building anything, and shows every cloud resource and its cost before creating it.

---

## Day-to-day workflow

```
/start    → agent reads the docs, summarizes state, proposes the session's work, waits for OK
   ...work on a branch, open a pull request...
/wrapup   → agent updates STATUS, records decisions, updates issues, pushes, opens/updates the PR
```

- **Tasks** live in GitHub Issues, grouped by milestone. Anything waiting on you is labeled `needs-decision`.
- **Advice:** start a fresh session (a strong reasoning model works best) and say *"act as advisor per .trazo/ADVISOR.md"*. It reviews progress, evidence quality, safety, cost, and the stop rule, and writes its conclusions into the repo.
- **Decisions:** `/decide <what>` drafts a numbered decision record for your approval.

### How state is organized

| File | Changes | Answers |
|---|---|---|
| `.trazo/charter/charter.md` | Rarely | Why, goal, success criteria, budget, constraints, stop rule |
| `docs/PLAN.md` | When dates or scope change | Milestones and risks |
| `.trazo/ARCHITECTURE.md` | When the system changes | How it's built (with diagram) |
| `docs/STATUS.md` | Every session (replaced) | Where things stand right now |
| `.trazo/adr/` | Append-only | What was decided and why |
| `.trazo/workstreams/` | As work progresses | Each feature/experiment: hypothesis, test, evidence, status |
| `docs/reports/` | Generated | Results over time |
| `docs/RUNBOOK.md` | When procedures change | How to run, deploy, roll back, recover |
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
| `VERSION` | Template version a project was created from |
| `CHANGELOG.md` | What changed, by version |
| `LESSONS.md` | Real problems from real projects, and how the overlay now prevents them |
| `decisions/` | Why the overlay is designed this way |

Trazo is **mounted** onto a host repo, not forked from a template, so there is no upstream
to sync with and no automated way to send a host project's lessons back. A mounted project
records its own lessons in its own decision records; copy files across (or re-run
`/kickoff`) to take an improvement in, and the host's decisions win on any conflict.

---

## Repository layout

```
.trazo/                    the overlay: rules, charter, adr, workstreams, specs
  rules.md                 the rules, tool-neutral
  charter/                 goal, budget, success criteria, stop rule
  adr/                     numbered decision records (append-only)
  workstreams/             one file per idea, with hypothesis and evidence
CLAUDE.md                  the Claude Code adapter for .trazo/rules.md
.claude/                   commands, agents, and permissions
docs/                      per-project state: PLAN, STATUS, RUNBOOK, reports
.github/                   CI, PR template, CODEOWNERS, issue templates, Dependabot
.template/                 Trazo's own memory: version, changelog, lessons, decisions
handbook/                  the published documentation
scripts/                   helper scripts (put_secret.sh, scan.sh)
tests/                     guard tests for the overlay itself
Dockerfile                  container (toolchain + tests; no service)
Makefile, pyproject.toml   tooling
```

The first two lines are the overlay. Everything after them is either this repository's own scaffolding or the harness that protects it — a mounted repo takes `.trazo/`, adds the adapter for whichever agent it uses, and leaves the rest alone.

---

## FAQ

**Can I use this for private projects?** Yes. Create a private repo from this public template, or mount `.trazo/` onto a private repo you already have.

**I already have a repo. Do I have to delete my files first?** No — that is the point of the overlay. Your code, build and pipeline stay; you add `.trazo/`, plus an adapter for whichever agent you use, and satisfy the mount-time contract.

**Does it cost anything?** Trazo is free. GitHub Actions is free for public repos and includes a monthly allowance for private ones. Cloud costs depend on your deploy target; kickoff sets a budget alert first.

**Not Python?** Nothing in `.trazo/` or `.claude/` assumes a language. `pyproject.toml`, the Makefile targets and the CI test job are this repo's own harness — a mounted repo replaces them with whatever runs its tests.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
