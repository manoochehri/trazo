# Trazo

**Trazo is an overlay of rules, roles and checks that you mount on a git repository so AI coding agents work to written rules.**

Trazo copies a pinned `.trazo/` folder into your repository, plus the adapter files for your agent: Claude Code, Codex, or any agent that reads `AGENTS.md` ([installer](https://github.com/manoochehri/trazo/blob/main/scripts/install.sh)). Your code, build and deploy setup stay yours. Trazo requires only that you can build and test from a fresh checkout with one command ([the mount-time contract](https://github.com/manoochehri/trazo/blob/main/src/overlay/rules.md)).

Agents work as a small team: a Coordinator (the main session) that dispatches work, a PM, engineers, a reviewer, a security reviewer, a skeptic and an architect. They hand work to each other through GitHub issues and pull requests, not through chat. Which roles may do what is set by [`rules.md`](https://github.com/manoochehri/trazo/blob/main/src/overlay/rules.md) and enforced where possible by hooks and GitHub settings.

You make the decisions only you can make: charter, scope, spend, secrets, and anything that changes a safety limit. Agents do reversible work without asking ([ADR 0032](https://github.com/manoochehri/trazo/blob/main/.trazo/project/adr/0032-permissive-by-default.md)).

## The six problems

| Problem | What Trazo does about it |
|---|---|
| Agents forget. Chat context resets. | Decisions go in numbered records ([ADRs](https://github.com/manoochehri/trazo/tree/main/.trazo/project/adr)), work in GitHub issues, state in `.trazo/project/`. [`rules.md`](https://github.com/manoochehri/trazo/blob/main/src/overlay/rules.md): "The repo is the memory". |
| Copy-paste glue between chats. | Agents hand off through issues and pull requests; an agent never asks you to relay a message ([`rules.md`](https://github.com/manoochehri/trazo/blob/main/src/overlay/rules.md), "Hand off through the repo"). The Coordinator starts the agents the PM records on an issue ([ADR 0029](https://github.com/manoochehri/trazo/blob/main/.trazo/project/adr/0029-the-front-door.md), [ADR 0025](https://github.com/manoochehri/trazo/blob/main/.trazo/project/adr/0025-pm-cannot-start-agents.md)). |
| Secrets leak. | Agents never read, print or commit secrets; you enter them with [`put_secret.sh`](https://github.com/manoochehri/trazo/blob/main/scripts/put_secret.sh). The engineer shell guard blocks secret reads ([`engineer_bash_guard.py`](https://github.com/manoochehri/trazo/blob/main/src/overlay/hooks/engineer_bash_guard.py), [tests](https://github.com/manoochehri/trazo/blob/main/tests/test_engineer_bash_guard.py)). The guard has known gaps, listed in the [hooks README](https://github.com/manoochehri/trazo/blob/main/src/overlay/hooks/README.md). |
| No project management. | A charter with a goal, budget and stop rule, written before results exist; a PM role that triages issues and milestones; ADRs for why. See [`rules.md`](https://github.com/manoochehri/trazo/blob/main/src/overlay/rules.md) and the [PM role](https://github.com/manoochehri/trazo/blob/main/src/overlay/roles/pm.md). |
| Results look better than they are. | A quantitative claim goes to a separate skeptic, which checks it against a bar the project writes down ([`SKEPTIC_BAR.md`](https://github.com/manoochehri/trazo/blob/main/.trazo/project/SKEPTIC_BAR.md), [skeptic role](https://github.com/manoochehri/trazo/blob/main/src/overlay/roles/skeptic.md)). Every number carries its sample size. |
| Safety limits drift. | Files in `CODEOWNERS` change only with your review. [`owner-merge.yml`](https://github.com/manoochehri/trazo/blob/main/.github/workflows/owner-merge.yml) merges by path risk: risky paths need reviewer and security success on the current head, docs-only changes need green CI, owner-only paths need your dispatch ([ADR 0031](https://github.com/manoochehri/trazo/blob/main/.trazo/project/adr/0031-review-by-path-not-every-pr.md), [tests](https://github.com/manoochehri/trazo/blob/main/tests/test_owner_merge_workflow.py)). |

## Current release and status

The current release is **v0.6.0** ([`.template/VERSION`](https://github.com/manoochehri/trazo/blob/main/.template/VERSION)). What changed since 0.4.0 is in the [changelog](changelog.md). To move a host to this release, run `install.sh upgrade` with a dry run first; see [Install, upgrade and uninstall](install.md).

Not proven live, and so UNVERIFIED:

- The drive workflow (`drive.yml`), the unattended driver that builds the next ready issue. It ships switched off. Its first live run on 2026-11-28 did not produce a change and exposed a bug. Nothing is marked verified until one full unattended run merges ([#247](https://github.com/manoochehri/trazo/issues/247), [#399](https://github.com/manoochehri/trazo/issues/399)).
- The front-door guard hook: its input shape has not been checked on a live run ([0.5.0 changelog](changelog.md)).
- The gate that treats `src/` and `.trazo/` changes as risky ([0.6.0 changelog](changelog.md)).
- Release automation (`release.yml`, `merge-audit.yml`) is Trazo's own and is not shipped to hosts. The `allow_release_app.py` setup that lets it push tags has not been run live.

Not built yet: pinning `trazo/verdict` to the reviewer App ([#366](https://github.com/manoochehri/trazo/issues/366)), so a shared account can still post a verdict status.

## Read next

- [Install, upgrade and uninstall](install.md): put Trazo in a repository and keep it current.
- How it works (page pending): the loop from issue to merge, the roles and the merge gate.
- Guardrails and limits (page pending): what agents do freely, what is yours alone, known gaps.

What `.trazo/` contains is in [What is `.trazo/`](overlay.md).
