# Trazo

**A governance overlay for AI coding agents. Mount it on any repo — new or existing — and agents start working to rules instead of improvising.**

Trazo is built specifically for **Claude Code**, and it is opinionated in two places: how agents hand work to each other, and whether a result is real. It is deliberately neutral about everything else — language, framework, and where your code runs.

[:material-source-repository: Use this template](https://github.com/manoochehri/trazo/generate){ .md-button .md-button--primary }
[:material-book-open-page-variant: Read the playbook](playbook.md){ .md-button }
[:material-layers-triple: What is `.trazo/`?](overlay.md){ .md-button }

---

## The problem

Almost every serious repo already exists, with its own runtime, toolchain and pipeline. Point a coding agent at it and the same things happen again and again:

- **Agents forget.** Sessions end, contexts reset, and plans or decisions kept only in chat are lost.
- **Copy-paste glue.** Moving notes between an "advisor" chat and a coding agent by hand loses information.
- **Secrets leak easily.** Keys end up in `.env` files, logs, commits, or chat.
- **No project management.** No charter, no milestones, no record of *why* something was decided.
- **Results look better than they are.** Agents grade work against their own assumptions instead of reality.
- **Safety limits drift.** An agent "helpfully" loosens a threshold nobody approved.

A starter template does not fix these — it fixes them for the empty repo you start from, and you are not starting from one. And the tool it mandates is the tool you were trying to escape.

Trazo's answer: **the repo is the memory, and the rails are mounted rather than imposed.** It adds a pinned `.trazo/` overlay and a thin `.claude/` adapter. Your code, your build, your deploy — unchanged.

## What it adds

Two layers, and the second is the one that matters.

**The mechanical rails** — table stakes, and easy to copy:

- worktree isolation per change, so two agents never fight over a dirty tree
- role separation, so an agent never grades its own work
- GitHub as the state engine — issues, pull requests, labels — not a database
- secrets discipline: nothing secret is ever read, printed or committed by an agent

**The judgment layer** — the reason to keep going:

- a **charter** with a goal, a budget, success criteria, and a **stop rule** written *before* the results exist
- **evidence with sample sizes**, judged against external ground truth, never against the agent's own model
- a **skeptic** that tries to break every quantitative result before it is acted on

That last pair is the differentiator, and it is the part a spec-and-ADR folder leaves out. Agents remove attrition as a stop mechanism: continuing a doomed project is nearly free and produces plausible commits throughout. Without a charter and a stop rule written down in advance, nothing ever decides to quit.

## How it works

A small team, talking to each other through GitHub — never through chat memory that can vanish with a closed window.

```mermaid
flowchart LR
    Owner(["You (owner)<br/>decide, approve, merge"])
    PM["PM role (/pm)<br/>plans, prioritizes, writes issues"]
    Engineer["Engineer role (/eng)<br/>builds, opens pull requests"]
    Reviewer[["Reviewer subagent<br/>checks pull requests"]]
    Security[["Security subagent<br/>checks secrets, permissions, infra"]]
    Skeptic[["Skeptic subagent<br/>breaks results before they count"]]
    GitHub[("GitHub<br/>issues · pull requests")]

    Owner <--> GitHub
    PM <--> GitHub
    Engineer <--> GitHub
    GitHub -.->|assigns work| Engineer
    Engineer -.->|invokes| Reviewer
    Engineer -.->|invokes| Security
    Engineer -.->|quantitative claim| Skeptic
    Reviewer -.->|verdict posts to| GitHub
    Reviewer -.->|flags risk| Security
```

The PM writes issues, the engineer turns issues into pull requests, and you approve and merge. Only `/pm` and `/eng` switch the session's role directly in Claude Code (they do not switch the model: the subagents are pinned to Opus, the main session's model is yours); the reviewer, security and skeptic checks are subagents the engineer calls on — automatically as part of `/work` and `/check-pr`, or ad hoc ("have security check this", "is this number real?"). Everything is visible, and nothing depends on a chat surviving. See [the team](team.md) for the full roster, and the [playbook](playbook.md) for how a normal day actually runs.

## Mounting it

Trazo is an overlay, so there are two ways in, and you do not have to start from an empty repo.

**On a new repo.** Create one from the template, run `/kickoff`, and it sets up the charter, the labels and the workflows:

```bash
gh repo create my-project --private --template manoochehri/trazo --clone
cd my-project && make setup
```

**On a repo you already have.** Copy `.trazo/` in, then add the adapter for the agent you actually use: `.claude/` if that is Claude Code, your own equivalent otherwise — [the same `.trazo/rules.md` drives any of them](overlay.md). If your repo already has a `.claude/` or a `CLAUDE.md`, merge into it rather than replacing it. If it has an `AGENTS.md`, that stays yours too: it describes your codebase, and Trazo governs the work done on it — see [`AGENTS.md` and Trazo](agents.md). Then read [`What is .trazo/`](overlay.md) for the layout and the one contract your repo has to satisfy. Your runtime, your build system and your pipeline stay exactly as they are — Trazo mandates no tool for a mounted repo, on purpose.

Either way, the next step is the same: open it in Claude Code and run `/kickoff`. It interviews you (idea, success criteria, budget, deadline, constraints, stop rule), shows you the charter, and sets up the issue graph.

## A normal day

```
you + PM (/pm)  →  issues  →  engineer (/eng)  →  pull request  →  reviewer + CI  →  you merge
```

Ten to fifteen minutes of your attention: a morning briefing, a decision or two, a merge or two, and a one-line "wrap up" at the end. The [playbook](playbook.md) walks through the whole loop and has an FAQ for everything in between.

## Layout and releases

`src/` is the product and `.trazo/` is the pinned install that governs a repository; `.trazo/project/` is that repository's own state (charter, decision records, workstreams, STATUS, PLAN, RUNBOOK), never overwritten on upgrade. A host starts from blank templates, not from Trazo's own state. A release is a GitHub milestone, and the tag is cut when it has no open issues; tags are never moved. See [What is `.trazo/`](overlay.md).

## Deploying

**Trazo ships no deploy target.** The overlay governs how agents work; your build and your cloud are yours. If you are mounting Trazo onto an existing repo, deployment is somebody else's decision and Trazo stays out of it.

See the [guide](guide.md) for the full setup walkthrough, including the optional GitHub Actions automation.
