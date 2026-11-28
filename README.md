<img src="handbook/assets/logo.svg" width="64" height="64" alt="Trazo logo">

# Trazo

**Your GitHub repo and VS Code, run like a well-managed engineering team.**

Trazo turns your GitHub repository and your VS Code experience into a well-managed engineering team. Your coding agents get jobs (engineer, reviewer, security, project manager and more), work through issues and pull requests, and are checked by separate agents. You keep what only a person should decide: money, secrets, settings and releases. It works with Claude Code (in [VS Code](https://code.claude.com/docs/en/vs-code) or a terminal), Codex, and any agent that reads `AGENTS.md`; Codex in VS Code and Antigravity are UNVERIFIED. It is not an editor extension and not a build service.

## What you get

- Seven agent job descriptions in `.trazo/roles/`. The reviewer, security and skeptic agents are subagent-only and run in their own sessions, so none of them grades work it wrote. `/pm` and `/eng` start the project manager and engineer agents.
- Merge rules enforced by a GitHub workflow that the main chat agent starts once the checks pass: documentation-only changes need green CI, and risky ones also need a reviewer pass and a security pass.
- 32 numbered decision records and a charter with a stop rule. The skeptic checks every number, and each number carries its sample size.

As of 2026-11-28 the project has 9 tagged releases, more than 180 merged pull requests since 2026-09-27, and 65 test files. The [Home page](handbook/index.md) walks one real pull request, #329, through the checks.

## Install

Run this from the root of your repo. It needs `git`, `curl` and the [GitHub CLI](https://cli.github.com/).

```sh
T=$(mktemp -d)
curl -fsSL https://raw.githubusercontent.com/manoochehri/trazo/main/scripts/install.sh -o "$T/install.sh"
bash "$T/install.sh" install latest
```

Then run `/kickoff` in your agent. To remove Trazo, run the same downloaded script with `uninstall`. The details are in [Install, upgrade and uninstall](handbook/install.md).

Or paste one of these prompts into your agent (Claude Code, Codex or any agent that reads `AGENTS.md`):

> **Install:** Install Trazo into this repo. Download `https://raw.githubusercontent.com/manoochehri/trazo/main/scripts/install.sh` into a new temporary directory outside the repository (`mktemp -d`), never into the repository, run `bash` on that file with `install latest`, and leave the repository's own files alone. Tell me what it placed and the owner-only steps it printed. Do not set secrets or variables.

> **Upgrade:** Upgrade Trazo in this repo. Download `https://raw.githubusercontent.com/manoochehri/trazo/main/scripts/install.sh` into a new temporary directory outside the repository (`mktemp -d`), never into the repository. Run `bash` on that file with `upgrade latest --dry-run` and show me the diff. Then run it without `--dry-run`. List any deny rule the upgrade removed from `.claude/settings.json`. Do not touch `.trazo/project/`.

> **Uninstall:** Remove Trazo from this repo. Download `https://raw.githubusercontent.com/manoochehri/trazo/main/scripts/install.sh` into a new temporary directory outside the repository (`mktemp -d`), never into the repository, and run `bash` on that file with `uninstall` (this keeps `.trazo/project/`). Do not use `--purge` unless I say so.

Your repo needs one command that runs its tests hermetically from a fresh checkout. Docker, nix, devcontainers or a `Makefile` all work.

## Where Trazo stands today

Trazo is early: about two months old and built from one project, this one. Each of these is UNVERIFIED or open:

- Every interactive agent acts through one GitHub account, so review status is only as trustworthy as that account until [#366](https://github.com/manoochehri/trazo/issues/366) lands.
- The unattended drive (`drive.yml`) is on in this repository and off by default in yours. It was triggered on a schedule from 2026-10-31 but only ran for real from 2026-11-23, when it was switched on here, and opened one pull request, #312, which was closed unmerged. A watched run on 2026-11-28 made no change and exposed a bug ([#399](https://github.com/manoochehri/trazo/issues/399)); [#247](https://github.com/manoochehri/trazo/issues/247) tracks the verification.
- The front-door hook that blocks the main session from editing files has not been checked on every live input.
- Release automation (`release.yml`) is Trazo's own and has not run live.

See [Guardrails and limits](handbook/guardrails.md). Released versions are on the [tags page](https://github.com/manoochehri/trazo/tags), and what changed is in the [changelog](handbook/changelog.md).

## Read next

[Home](handbook/index.md) · [How it works](handbook/how-it-works.md) · [In your repo](handbook/in-your-repo.md) · [Install](handbook/install.md) · [Guardrails](handbook/guardrails.md) · [Day to day](handbook/day-to-day.md) · site: https://manoochehri.github.io/trazo/

Contributing: [CONTRIBUTING.md](CONTRIBUTING.md). License: [MIT](LICENSE).
