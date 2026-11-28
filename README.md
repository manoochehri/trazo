<img src="handbook/assets/logo.svg" width="64" height="64" alt="Trazo logo">

# Trazo

Trazo is an overlay of rules, roles and checks that you mount on any repo. It makes AI coding agents work to written rules instead of improvising.

## The problem

- Agents forget. Chat context resets, and decisions made in chat are lost.
- Copy-paste glue. Moving notes between chats by hand loses information.
- Secrets leak into `.env` files, logs, commits or chat.
- No project record: no charter, no milestones, no reason for a decision.
- Results look better than they are, because agents grade their own work.
- Safety limits drift when an agent loosens a threshold nobody approved.

## Install

Run this from the root of your repo. It needs `git`, `curl` and the [GitHub CLI](https://cli.github.com/). The version is the current release, v0.6.0.

```sh
curl -fsSL https://raw.githubusercontent.com/manoochehri/trazo/v0.6.0/scripts/install.sh -o install.sh
bash install.sh install v0.6.0
```

Then read [Install, upgrade and uninstall](handbook/install.md). It covers the options, the upgrade and the owner-only steps.

Or paste one of these prompts into your agent (Claude Code, Codex or any agent that reads `AGENTS.md`):

> **Install:** Install Trazo v0.6.0 into this repo. Download `https://raw.githubusercontent.com/manoochehri/trazo/v0.6.0/scripts/install.sh`, run `bash install.sh install v0.6.0`, then delete `install.sh`. Tell me what it placed and the owner-only steps it printed. Do not set secrets or variables.

> **Upgrade:** Upgrade Trazo to v0.6.0 in this repo. Download the installer from the v0.6.0 tag and run `bash install.sh upgrade v0.6.0 --dry-run`. Show me the diff. Then run it without `--dry-run`, and delete `install.sh`. List any deny rule the upgrade removed from `.claude/settings.json`. Do not touch `.trazo/project/`.

> **Uninstall:** Remove Trazo from this repo. Download the installer from the v0.6.0 tag, run `bash install.sh uninstall` (this keeps `.trazo/project/`), then delete `install.sh`. Do not use `--purge` unless I say so.

Your repo needs one command that runs its tests hermetically from a fresh checkout. Docker, nix, devcontainers or a `Makefile` all work. Your code, build and deploy setup stay yours.

## Status

Early. Trazo was distilled from one real project, so expect rough edges. Current release: v0.6.0.

UNVERIFIED, not yet proven on a live run:

- The drive workflow. Its first live run failed to produce a change ([#399](https://github.com/manoochehri/trazo/issues/399)). It ships switched off.
- The front-door hook payload shape.
- Release automation (`release.yml`, `merge-audit.yml`).

Details: [Guardrails and limits](handbook/guardrails.md).

## Read next

- [Index](handbook/index.md): what Trazo is and the problems it addresses.
- [How it works](handbook/how-it-works.md): the loop, the roles, the merge gate and the guards.
- [In your repo](handbook/in-your-repo.md): what `.trazo/` contains and what stays yours.
- [Install, upgrade and uninstall](handbook/install.md).
- [Guardrails and limits](handbook/guardrails.md): what agents do freely, and what is yours alone.
- [Day to day](handbook/day-to-day.md): how to ask for work and what needs you.

Published site: https://manoochehri.github.io/trazo/

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
