<img src="handbook/assets/logo.svg" width="64" height="64" alt="Trazo logo">

# Trazo

**Trazo is a set of rules you add to a git repository so AI coding agents work like a small team: one agent writes the code, a separate agent reviews it, and you keep the decisions that cannot be undone, such as merging, spending money and changing settings.**

It is for developers who already use Claude Code (in a terminal or in VS Code) or OpenAI Codex on a real repository and want to stay in charge of what it does. Trazo is not an editor extension and not a build service. The rules are a folder named `.trazo/` and a few instruction files that you copy into the repository, and your agent reads them at the start of every session. It works with any language or framework, and your code, build and deploy setup stay as they are.

## What goes wrong when AI agents work in a real codebase

Each of these happened in this project, which Trazo was built from. The issue numbers are public.

- **The agent that builds the change also declares it done.** The main chat session edited pull request bodies and pushed empty commits itself instead of handing the work to an engineer agent, and said that nothing stopped it ([#319](https://github.com/manoochehri/trazo/issues/319)). A hook that blocks this now ships; its behavior on every live input is UNVERIFIED.
- **Approval that can be forged or goes stale.** All agents act through one GitHub account, so any of them can set the status that says a review passed. On 14 merged pull requests the reviewer's own GitHub App wrote only failures ([#366](https://github.com/manoochehri/trazo/issues/366), [#44](https://github.com/manoochehri/trazo/issues/44), both open).
- **Guardrails that miss a route, or block the wrong person.** An engineer agent could still merge and read `.env` through `gh api` and `cat` ([#330](https://github.com/manoochehri/trazo/issues/330)), and the guard added for that then blocked the reviewer from posting its own status ([#347](https://github.com/manoochehri/trazo/issues/347)).
- **Decisions made in chat disappear.** Trazo keeps plans and decisions as files and issues in the repository, where the next session reads them.

## One pull request, start to finish

[Pull request #329](https://github.com/manoochehri/trazo/pull/329) limited which agents the main session may start. It carried its test evidence in the body, the security agent and the reviewer each read it in their own context, and the reviewer returned `merge after fixes` for one commit and `merge` for the next. On that latest commit the statuses `trazo/verdict` and `trazo/security` were both `success`, CI was green, and a workflow merged it. The [Home page](handbook/index.md) shows the real excerpts.

## What you get when you add it

Seven agent job descriptions (the reviewer, security and skeptic agents run in their own sessions), merge rules that need a reviewer pass and a security pass on the latest commit for changes to sensitive files, and 32 numbered decision records, a charter with a stop rule, and a skeptic that checks every number, which must carry its sample size. Rules live in `.trazo/rules.md`; `/pm` and `/eng` start the project manager and engineer agents, while the reviewer, security and skeptic are subagent-only.

## Try it on your repository

Run this from the root of your repo. It needs `git`, `curl` and the [GitHub CLI](https://cli.github.com/).

```sh
curl -fsSL https://raw.githubusercontent.com/manoochehri/trazo/main/scripts/install.sh -o install.sh
bash install.sh install latest
```

Then run `/kickoff` in your agent. To remove Trazo, run `bash install.sh uninstall`. The details are in [Install, upgrade and uninstall](handbook/install.md).

Or paste one of these prompts into your agent (Claude Code, Codex or any agent that reads `AGENTS.md`):

> **Install:** Install Trazo into this repo. Download `https://raw.githubusercontent.com/manoochehri/trazo/main/scripts/install.sh`, run `bash install.sh install latest`, then delete `install.sh`. Tell me what it placed and the owner-only steps it printed. Do not set secrets or variables.

> **Upgrade:** Upgrade Trazo in this repo. Download `https://raw.githubusercontent.com/manoochehri/trazo/main/scripts/install.sh` and run `bash install.sh upgrade latest --dry-run`. Show me the diff. Then run it without `--dry-run`, and delete `install.sh`. List any deny rule the upgrade removed from `.claude/settings.json`. Do not touch `.trazo/project/`.

> **Uninstall:** Remove Trazo from this repo. Download `https://raw.githubusercontent.com/manoochehri/trazo/main/scripts/install.sh`, run `bash install.sh uninstall` (this keeps `.trazo/project/`), then delete `install.sh`. Do not use `--purge` unless I say so.

Your repo needs one command that runs its tests hermetically from a fresh checkout. Docker, nix, devcontainers or a `Makefile` all work.

## Where Trazo stands today

Trazo is early: about two months old and distilled from one project, this one. Each of these is UNVERIFIED or open:

- The review status is only as trustworthy as the one shared GitHub account until [#366](https://github.com/manoochehri/trazo/issues/366) lands.
- The unattended drive (`drive.yml`) is on in this repository and off by default in yours. Its first live run on 2026-11-28 produced no change ([#399](https://github.com/manoochehri/trazo/issues/399)).
- The front-door hook that blocks the main session from editing files has not been checked on every live input.
- Release automation (`release.yml`) is Trazo's own and has not run live.

See [Guardrails and limits](handbook/guardrails.md). The current release is on the [changelog](handbook/changelog.md) and the [releases page](https://github.com/manoochehri/trazo/releases).

## Read next

[Home](handbook/index.md) · [How it works](handbook/how-it-works.md) · [In your repo](handbook/in-your-repo.md) · [Install](handbook/install.md) · [Guardrails](handbook/guardrails.md) · [Day to day](handbook/day-to-day.md) · site: https://manoochehri.github.io/trazo/

Contributing: [CONTRIBUTING.md](CONTRIBUTING.md). License: [MIT](LICENSE).
