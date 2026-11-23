<img src="handbook/assets/logo.svg" width="64" height="64" alt="Trazo logo">

# Trazo

**A governance overlay for AI coding agents. Mount it on any repo — new or existing — and agents start working to rules instead of improvising.**

Trazo ships tested adapters for **Claude Code** and **OpenAI Codex**, and is opinionated in two places: how agents hand work to each other, and whether a result is real. It is deliberately neutral about everything else — language, framework, and where your code runs.

You bring a repo, or an idea. Trazo adds a pinned `.trazo/` overlay and the adapter for your agent: rules, a charter with a pre-registered stop rule, decision records that outlive a session, and roles that check each other's work. Your code, your build, your deploy — unchanged.

Engineer and PM are working roles (`/eng` and `/pm` in Claude Code, Codex agents for Codex). Reviewer, security, and skeptic are **subagent-only** review roles, kept separate from the agent that builds the change.

> Status: early; distilled from one real project, so expect rough edges. The first release, [`v0.1.0`](https://github.com/manoochehri/trazo/tree/v0.1.0), is published; the current release is [`v0.3.1`](https://github.com/manoochehri/trazo/tree/v0.3.1), scoped in the [v0.3.1 milestone](https://github.com/manoochehri/trazo/milestone/8).

[📖 Full documentation](https://manoochehri.github.io/trazo/) · new here? [the guide](handbook/guide.md) · already running a project? [the playbook](handbook/playbook.md)

---

## Set it up

Run these from the root of your repo, in a terminal. You need `git`, `curl` and the [GitHub CLI](https://cli.github.com/) (`gh auth login`). `v0.3.1` is the newest release; check [the tags](https://github.com/manoochehri/trazo/tags) for a newer one and use it instead.

### 1. Install Trazo into a repo

1. Go to your repo and make sure it is committed and clean:
   ```bash
   cd path/to/your-repo
   git status
   ```
2. Download the installer from the release you want:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/manoochehri/trazo/v0.3.1/scripts/install.sh -o install.sh
   ```
3. Install. The default adds the Claude Code and `AGENTS.md` adapters; for OpenAI Codex add `--adapter codex`:
   ```bash
   bash install.sh install v0.3.1
   ```
4. Read what it printed, then commit the new files on a branch and open a pull request.
5. In your agent, run `/kickoff` and answer the questions.

Your code, build and pipeline are not changed. Nothing in `.trazo/project/` is ever overwritten. To remove Trazo: `bash install.sh uninstall`. All options (`--source`, `--sha`, `--adapter`): [Install, upgrade and uninstall](handbook/install.md).

### 2. Upgrade an existing install

1. Download the installer from the newer release (replace `v0.3.1` with it):
   ```bash
   curl -fsSL https://raw.githubusercontent.com/manoochehri/trazo/v0.3.1/scripts/install.sh -o install.sh
   ```
2. Preview. This shows what would change and changes nothing:
   ```bash
   bash install.sh upgrade v0.3.1 --dry-run
   ```
3. Apply it:
   ```bash
   bash install.sh upgrade v0.3.1
   ```
4. Commit and open a pull request. Your own state in `.trazo/project/` is never touched, and a file you edited is skipped with a warning.

### Or hand it to your LLM

Paste one of these into your coding agent, from the root of the repo. Replace nothing: it works out the repo itself.

**Install:**
> Install Trazo v0.3.1 into this repo. Download `https://raw.githubusercontent.com/manoochehri/trazo/v0.3.1/scripts/install.sh`, run `bash install.sh install v0.3.1`, then delete `install.sh`. Tell me what it placed and the owner-only steps it printed. Do not set secrets or variables.

**Upgrade:**
> Upgrade Trazo to v0.3.1 in this repo. Download the installer from the v0.3.1 tag, run `bash install.sh upgrade v0.3.1 --dry-run`, show me the diff, then run it without `--dry-run` and delete `install.sh`. If you see `.claude/settings.json` deny rules for `fly`, `flyctl`, `clasp push`, `clasp deploy` or `scripts/deploy`, remove those lines: the installer never edits that file. Do not touch `.trazo/project/`.

**Uninstall:**
> Remove Trazo from this repo. Download `https://raw.githubusercontent.com/manoochehri/trazo/v0.3.1/scripts/install.sh`, run `bash install.sh uninstall` (keeps `.trazo/project/`), then delete `install.sh`. Do not use `--purge` unless I say so.

### 3. Owner-only setup (secrets, switches, GitHub Apps)

Agents never do these; they are yours. The installer prints the same list, with your repo name filled in, when it finishes. This list applies to releases that ship the review and drive workflows (`v0.3.0` and later). Replace `owner/name` with your repo. For automatic review, do steps 1, 2 and 3 in that order: the key, then the `trazo-apps` environment and the Apps (step 2 creates both), then the switch. Steps 4 and 5 are for the driver and the code owner.

1. **Give agents their key.** Needed for automatic review and drive:
   ```bash
   gh secret set ANTHROPIC_API_KEY -R owner/name
   ```
   `gh` asks you to paste the key. In a GitHub organization, set it once as an organization secret.
2. **Create the two GitHub Apps.** The reviewer App is needed for automatic review to record its verdict; the builder App is needed for the driver. The script is not installed in your repo. Get it from a clone of Trazo, then point it at your repo. It ships in the Trazo repo at `v0.3.1`; check out the tag you installed:
   ```bash
   git clone https://github.com/manoochehri/trazo.git
   cd trazo
   zsh scripts/setup_github_apps.zsh --dry-run --repo owner/name   # shows what it would do, changes nothing
   zsh scripts/setup_github_apps.zsh --repo owner/name
   ```
   It needs `zsh`, `gh` (signed in as the repo owner with admin rights), `jq`, `openssl`, `curl` and `python3`. It creates the `trazo-apps` environment, opens your browser twice (click "Create GitHub App", then install it on this one repo only) and stores the keys itself. You never see or paste a key.
   The script only accepts a default branch named `main`: it limits `trazo-apps` to `main` and stops if that fails. If your default branch has another name, stop here and ask for a follow-up.
3. **Turn on automatic review.** Last, once the key and the Apps exist. It is off until you do this:
   ```bash
   gh variable set AUTO_REVIEW_ENABLED --body true -R owner/name
   ```
4. **Turn on the driver, carefully.** The driver (`drive.yml`) works through open issues on a timer: it picks one, an agent edits a copy of the code, and a plain script opens the pull request, which is merged only after review and passing checks. It does nothing until you set:
   ```bash
   gh variable set DRIVE_ENABLED --body true -R owner/name
   ```
   It has **not been verified on a live run** ([#247](https://github.com/manoochehri/trazo/issues/247), release v0.4.0). Watch the first run, and switch it off if anything looks wrong:
   ```bash
   gh variable delete DRIVE_ENABLED -R owner/name
   ```
5. **Check `.github/CODEOWNERS`.** The installer guesses your handle from `origin`. It must be a person or team that can review.

More on what each step does and why: [Owner setup](handbook/install.md#owner-setup).

---

## Why this exists

Almost every serious repo already exists, with its own runtime, toolchain and pipeline. Point a coding agent at it and the same problems happen again and again:

- **Agents forget.** Sessions end, contexts reset, and plans or decisions kept only in chat are lost.
- **Copy-paste glue.** Moving notes between an "advisor" chat and a coding agent by hand loses information.
- **Secrets leak easily.** Keys end up in `.env` files, logs, commits, or chat.
- **No project management.** No charter, no milestones, no record of *why* something was decided.
- **Results look better than they are.** Agents grade work against their own assumptions instead of reality.
- **Safety limits drift.** An agent "helpfully" loosens a threshold nobody approved.

A starter template only fixes these for a new repo, and most projects already have a codebase. Trazo mounts into an existing repo instead.

Trazo's answer: **the repo is the memory, and the rails are mounted rather than imposed.** Everything durable — goal, budget, design, decisions, status, results — lives as plain markdown in the repo, so any fresh agent session reads it and picks up where the last one stopped.

---

## What you get

### What the installer gives your repo

`install.sh` writes only what is in `src/overlay/`, `src/adapters/` and `src/harness/`, and nothing else:

| Area | What's included |
|---|---|
| **The rules** | `.trazo/rules.md` — tool-neutral, read once by any tool's adapter |
| **Design records** | `.trazo/ARCHITECTURE.md`, `.trazo/ADVISOR.md` (framework files, overwritten on upgrade) |
| **Blank project state** | `.trazo/project/` created from templates: `charter/charter.md`, `STATUS.md`, `PLAN.md`, `RUNBOOK.md`, `SKEPTIC_BAR.md`, `reports/`, plus blank ADR and workstream templates. Never overwritten on upgrade |
| **The adapter** | `CLAUDE.md` and `.claude/` for Claude Code; `AGENTS.md`, `.codex/agents/`, and `.agents/skills/` for Codex; `AGENTS.md` for other agents that read it |
| **AI team** | Canonical roles live in `.trazo/roles/`. Claude Code maps them to `.claude/agents/`; Codex maps them to project agents in `.codex/agents/`. Both adapters use the same role definitions. |
| **Commands and workflows** | Claude Code gets slash commands in `.claude/commands/`; Codex gets discoverable skills in `.agents/skills/`. The adapter maps each tool's entry points to Trazo's shared roles and project docs. |
| **Secret-read denial** | If you use Claude Code, `.claude/settings.json` denies Claude Code reads of `.env`, `.env.*`, `secrets/`, `*.pem` and `*.key` (only if you have no `settings.json` of your own) |

`/kickoff` (run after install) interviews you and sets up the charter, plan, labels, branch rules and first issues. The installer also places CI, secret-scanning and PR-evidence files, and never overwrites a path you already have. What is placed, and what `/kickoff` does: [Install, upgrade and uninstall](handbook/install.md#what-the-installer-places).

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
- Claude Code, or [OpenAI Codex](https://developers.openai.com/codex/)
- A way to run your tests in one command — see the mount-time contract above. For a *new* Trazo-owned repo, that means [uv](https://docs.astral.sh/uv/) and Docker.
- Optional: an account with wherever your project deploys; Trazo ships no deploy target

---

## Quick start

Trazo mounts onto a repo you already have, or onto a new empty one.

### Install

See [Set it up](#set-it-up) above. Your repo keeps its runtime, build system and pipeline; the installer adds `.trazo/` and the adapter for your agent. The layout: [What is `.trazo/`](https://manoochehri.github.io/trazo/overlay/).

Then:

1. **Declare the environment** — one command that runs your tests hermetically from a fresh worktree. If you don't have one, that's the only thing to build first.
2. **Run `/kickoff`** and answer the interview. The stop rule is the part worth taking seriously: it is the only thing that decides whether to keep going, and it has to be written before the results exist.
3. **Leave `docs/` and Trazo's own state alone.** A repo's Trazo state lives in `.trazo/project/`, created blank for you; never copy this repository's own `.trazo/project/` across, because it is about Trazo, not your project.

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

Trazo's own release notes live in `.template/CHANGELOG.md`; `.template/VERSION` names the current version. The first published release is `v0.1.0`.

**A release is a GitHub milestone.** The milestone `vX.Y.Z` carries the release goal in its description and its scope as its issues. The tag is cut when that milestone has 0 open issues and CI is green, and `make release` refuses to tag while any are open. Tags are immutable: a published tag is never moved, so a host that pinned it always gets the same files. A version is a coherent body of work, not one per merged pull request.

**`src/` is the product; `.trazo/` is the pinned install.** All changes to the framework are made in `src/` and ship with the next version. This repository is itself governed by the pinned copy in `.trazo/`, which is never hand-edited, so editing a rule never changes the rules governing the edit. The cost is deliberate: a rule fix cannot govern this repository until it is released.

Trazo is **mounted** onto a host repo, not forked, so there is no upstream to sync with and no automated way to send a host project's lessons back. A mounted project records its own lessons in its own decision records. To take an improvement in, run `bash install.sh upgrade <tag>` (add `--dry-run` to preview): it replaces the framework files in `.trazo/`, never touches `.trazo/project/`, and skips adapter files you have edited. See [Install, upgrade and uninstall](https://manoochehri.github.io/trazo/install/).

---

## Repository layout

```
src/                       the product: everything a host receives, edited here
  overlay/                 tool-neutral core: rules.md, ADVISOR.md, ARCHITECTURE.md
    templates/             blank charter, adr, workstream and docs/ for a host
  adapters/                AGENTS.md, CLAUDE.md, claude/ and codex/ (agents, skills)
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
