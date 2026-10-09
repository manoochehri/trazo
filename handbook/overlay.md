# What is `.trazo/`

Trazo is an **overlay**, not a starter template. That is the whole difference, and it decides everything else on this page.

A starter template is a repo you copy once, at the start, and then diverge from forever. An overlay is a directory you mount onto a repo that already exists — with its own runtime, its own toolchain, its own pipeline, and its own history — and it governs **how agents work** without touching **what your code does**.

So the question "which stack do you use?" has no answer here, and that is deliberate.

## The mount-time contract

There is exactly one thing a mounted repo has to provide:

> **A one-command, reproducible build/test environment that an agent can run hermetically from a fresh worktree.**

Docker, nix, devcontainers or a `Makefile` all satisfy it. **Trazo does not mandate a particular tool** — that mistake was already made once, with a cloud provider, and it is why the contract is phrased as a capability rather than a product. A mounted repo declares what it has; Trazo keeps its own tooling for its own repository and asks nothing of yours.

Everything else in this overlay is the same shape: a rule stated once, tool-neutrally, that any agent has to follow regardless of what it is running on.

## The layout

```
src/                      the product: what a host receives, edited here
  overlay/                tool-neutral core: rules.md, ADVISOR.md, ARCHITECTURE.md
    templates/            blank charter, adr, workstream and docs/ for a host
  adapters/               AGENTS.md, CLAUDE.md, claude/ (commands, agents, settings)

.trazo/                   the pinned install; overwritten on upgrade, never hand-edited
  rules.md                the rules, stated once, tool-neutral
  ARCHITECTURE.md         how the system is built
  ADVISOR.md              the advisor/PM role
  project/                the repository's own state; never overwritten
    charter/              the judgment layer: goal, budget, success criteria, stop rule
    adr/                  numbered decision records — append-only, supersede never edit
    workstreams/          one file per feature or experiment, with status and evidence
    STATUS.md PLAN.md RUNBOOK.md SKEPTIC_BAR.md reports/
```

`src/` is canonical and `.trazo/` is the installed, pinned copy of it. In the Trazo repository the two are separate on purpose: editing a rule in `src/` does not change the rules governing the session that edited it, because that session is governed by the frozen copy in `.trazo/` until the next version is cut. In a host there is no `src/`; the host has only `.trazo/`, and `.trazo/project/` is its own.

Three things are worth noticing about that layout.

**`rules.md` is the core, and it is deliberately not in `.claude/`.** `.claude/` adapts those rules to Claude Code; the Codex adapter does the same through `AGENTS.md`, project agents, and skills. Both use the same canonical roles and rules. Other agents that read `AGENTS.md` can use the generic adapter. In this repository, adapter source lives in [`src/adapters/`](https://github.com/manoochehri/trazo/tree/main/src/adapters).

Here the adapter loads the rules with a one-line `@.trazo/rules.md` import, so they are inlined at load rather than left as a link an agent might skip or reword. That form was runtime-verified in [`claude-md-imports.md`](https://github.com/manoochehri/trazo/blob/main/.trazo/project/workstreams/claude-md-imports.md): one hop, no tool call, and it resolves when the session starts in the repository root. Because an import that fails to resolve is **silent** — no error, no warning — the repository asserts every `@` target exists, so a typo cannot quietly leave an agent with no rules.

**The framework and the project are partitioned.** Everything in `.trazo/` outside `project/` belongs to Trazo and is overwritten when you upgrade. Everything inside `project/` belongs to the repository and is never overwritten. That boundary is what makes an upgrade safe.

**The charter is a directory, because it is several documents.** The goal, the budget, the success criteria and the stop rule are separate files that are reviewed separately, and the stop rule is the one that has to be written *before* the results exist.

## Why a judgment layer, and not just specs

A `specs/` and `adr/` folder answers *what to build*. It does not answer *whether to keep going*.

That question has a structural problem once agents are writing the code: **agents remove attrition as a stop mechanism.** Continuing a doomed project costs almost nothing extra and produces plausible, well-reviewed commits the whole way down. There is no natural moment where anything forces the question, so nothing ever asks it.

Trazo answers it with two things that a spec folder does not have:

- a **stop rule** — the evidence, decided in advance, that means stop or rethink. Pre-registration is the point: a stop rule written after results exist is a rationalisation.
- a **skeptic** — a subagent that never edits a file and tries to break every quantitative result *before* anyone acts on it, returning `holds` / `holds with caveats` / `does not hold`. Its verdict is posted on the pull request or issue so the next session can see it. It runs every time, not only when something looks suspicious, because the failure it catches is the result that looks completely fine.

The skeptic works because it is **not** the session that produced the result. An agent that built an analysis knows what it meant to build, so it reads the output as if it meant what it meant. Asking a second question in the same conversation inherits those blind spots — which is why it is a separate subagent, never a mode you switch into.

## What stays out of the overlay

`.trazo/project/` holds a repository's own state: charter, decision records, workstreams, `STATUS.md`, `PLAN.md`, `RUNBOOK.md`, `SKEPTIC_BAR.md` and `reports/`. In the Trazo repository that is state about Trazo, and none of it ships to a host. A host receives blank templates from `src/overlay/templates/` (the charter, ADR and workstream files, and a `docs/` set holding STATUS, PLAN, RUNBOOK, SKEPTIC_BAR and `reports/`), and the installer creates them in the host's own `.trazo/project/` if absent (`/kickoff` fills them in). `docs/` is empty in this repository and belongs to the host.

The rule of thumb: **ours lives in `.trazo/project/`; the host's is a template under `src/overlay/templates/`.** The framework files beside it are overwritten on upgrade; `project/` never is.

## Releases

A release is a GitHub milestone named `vX.Y.Z`: its description is the release goal and its issues are the scope. The git tag is cut when the milestone has 0 open issues and CI is green, and `make release` refuses to tag while any are open. Tags are immutable. A tag that exists is never moved, because someone may have pinned it, and "latest" means the highest release tag.

## Updating a mounted copy

Trazo is mounted, not forked, so there is no upstream to sync from and no automated round trip back. That is a deliberate consequence of the model, not an omission:

- **Taking an improvement in:** run `bash install.sh upgrade <tag>` (`--dry-run` previews it). It replaces the framework files in `.trazo/`, never touches `.trazo/project/`, and skips adapter files you have edited; review the diff like any other change.
- **Your project's own decision records win** on anything the two disagree about. You know your repo; Trazo does not.
- **Lessons flow the other way only by hand.** If a mounted project learns something reusable, it records it in its own `.trazo/project/adr/` and workstreams. Nothing is sent anywhere automatically.

## Where to go next

- [The playbook](playbook.md) — how a normal day runs
- [The guide](guide.md) — the full setup walkthrough
- [The team](team.md) — the roles and who calls on whom
