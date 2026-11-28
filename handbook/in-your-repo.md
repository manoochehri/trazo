# In your repo

Trazo adds a governance layer to a repository that already exists. This page covers what it
adds, what stays yours, and which file wins when two instructions disagree.

## What Trazo is mounted on

Trazo is an overlay. You mount it onto your repo. It does not pick your language, runtime
or deploy path.

The only requirement is a build and test environment that one command runs and that an
agent can run from a fresh worktree. Docker, nix, devcontainers and a `Makefile` all
qualify. Trazo does not require one tool over another
([rules.md, "The mount-time contract"](https://github.com/manoochehri/trazo/blob/main/.trazo/rules.md)).

## What Trazo adds

| Where | What it is | Who owns it |
|---|---|---|
| `.trazo/`, except `project/` | Rules, roles, skills, hooks, architecture guide | Trazo. Replaced on upgrade. |
| `.trazo/project/` | Your charter, decision records, workstreams, status, plan, runbook, reports | You. Never overwritten on upgrade. |
| `AGENTS.md`, `CLAUDE.md`, `.claude/`, `.codex/`, `.agents/` | Adapters that point each tool at `.trazo/` | Shared. The installer changes only the parts listed below. |
| CI workflows, PR template, scan and evidence scripts, `.env.example` | Harness files | Shared. A file you already have is never overwritten. |

## What `.trazo/` contains

```
.trazo/
  rules.md          the rules, stated once, tool-neutral
  ARCHITECTURE.md   how Trazo is built (pinned copy)
  ADVISOR.md        the advisor role
  roles/            canonical role definitions
  skills/           workflow skills
  hooks/            guard scripts; known gaps are listed in the hooks README
  templates/        blank charter, ADR, workstream and docs files
  project/          yours (see below)
  VERSION           the release installed
  INSTALLED         manifest of the adapter files placed, with a hash for each
```

The installer replaces everything in `.trazo/` except `project/` when you upgrade. Read the
diff before you accept it. Source for these files:
[`src/overlay/`](https://github.com/manoochehri/trazo/tree/main/src/overlay).

`.trazo/project/` holds your own state:

- `charter/`, `adr/`, `workstreams/`
- `STATUS.md`, `PLAN.md`, `RUNBOOK.md`, `SKEPTIC_BAR.md`, `reports/`

The installer fills it from blank templates only when it is missing
([ADR 0011](https://github.com/manoochehri/trazo/blob/main/.trazo/project/adr/0011-ours-in-project-hosts-get-templates.md)).

## What stays yours

- **Your code, build, tests, runtime and deploy.** Trazo does not take them over. The
  architecture says the installer works "without taking ownership of the host's code,
  runtime, or project state"
  ([ARCHITECTURE.md](https://github.com/manoochehri/trazo/blob/main/src/overlay/ARCHITECTURE.md)).
- **`.trazo/project/`.** Upgrades never change it. Only `uninstall --purge` removes it.
- **Text outside the `trazo:begin` and `trazo:end` markers** in `AGENTS.md` and `CLAUDE.md`.
  The installer does not read or rewrite it.
- **Files you already have.** If `.claude/` or `.codex/` already has a file with the same
  name, Trazo installs its copy as `trazo-<name>`. `.claude/settings.json` is placed only if
  it is missing.
- **`.github/CODEOWNERS`.** Trazo writes it only when it is missing. An existing file is
  never edited; suggested lines are printed for you to review.

## `AGENTS.md` is how; Trazo is whether

`AGENTS.md` says how to work in your codebase: the command that builds it, the command that
tests it, your conventions. You write it and keep it current.

Trazo says whether the work may be done. Who may act, which limits are human-only, what
evidence a claim needs, and which roles must stay separate.

Take a release. Your `AGENTS.md` can say "run `make release`". That answers how. Trazo adds
the limits: the release tags only when CI is green, and an existing tag is never moved.
A command existing is not permission to run it.

**When they disagree, Trazo wins.** `.trazo/rules.md` says so directly: where a repository
instruction and a rule there disagree, the rule wins. A nested file, or one an agent reads
later, does not override a rule because it was read later.

You can edit your `AGENTS.md` freely. Changing what it says about permission, safety or
acceptance is a governance change, and Trazo's rules decide it.

## Tool adapters

- **Claude Code.** `CLAUDE.md` loads the rules with `@.trazo/rules.md`. The import is read
  when the session starts, and it resolves only when the session starts in the repository
  root. If it does not resolve, nothing warns you and the session runs without the rules
  ([adapter source](https://github.com/manoochehri/trazo/blob/main/src/adapters/CLAUDE.md)).
- **Codex and other `AGENTS.md` readers.** The adapter is
  [`src/adapters/AGENTS.md`](https://github.com/manoochehri/trazo/blob/main/src/adapters/AGENTS.md).
  Codex support was tested once with `codex-cli 0.162.0-alpha.2`. UNVERIFIED on other Codex
  versions.

## Where to go next

- [Install and upgrade](install.md)
- [How it works](how-it-works.md): the loop, the roles and the merge gate
- [Guardrails and limits](guardrails.md): what agents may do and what stays yours
- [Day to day](day-to-day.md): running the repository
- [Decision records](https://github.com/manoochehri/trazo/blob/main/.trazo/project/adr/README.md)
  (ADR index)
