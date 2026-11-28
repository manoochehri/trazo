# Install, upgrade and uninstall

This page is the one place for installing, upgrading and removing Trazo, and for the owner-only setup.

The current release is **v0.6.0** (see `.template/VERSION`). The commands below use it. For a newer release, replace `v0.6.0` with the latest tag from the repository's tag list.

Trazo is installed from a release tag, by one script. Nothing is copied from a template repository, and nothing is fetched from a moving branch.

## Or hand it to your coding agent

Paste one of these into Claude Code, Codex or any coding agent, from the root of your repository. The agent works out the rest. Each uses the current release, `v0.6.0`.

**Install:**

> Install Trazo v0.6.0 into this repo. Download `https://raw.githubusercontent.com/manoochehri/trazo/v0.6.0/scripts/install.sh`, run `bash install.sh install v0.6.0`, then delete `install.sh`. Tell me what it placed and the owner-only steps it printed. Do not set secrets or variables.

**Upgrade:**

> Upgrade Trazo to v0.6.0 in this repo. Download `https://raw.githubusercontent.com/manoochehri/trazo/v0.6.0/scripts/install.sh`, run `bash install.sh upgrade v0.6.0 --dry-run`, and show me the diff. Then run it without `--dry-run` and delete `install.sh`. Do not touch `.trazo/project/`. The upgrade merges new deny rules and hook entries into `.claude/settings.json` and keeps a `.bak` copy: tell me about any deny rule it removes so I can review it. Then remind me to open a fresh session so the new hooks load.

**Uninstall:**

> Remove Trazo from this repo. Download `https://raw.githubusercontent.com/manoochehri/trazo/v0.6.0/scripts/install.sh`, run `bash install.sh uninstall` (this keeps `.trazo/project/`), then delete `install.sh`. Do not use `--purge` unless I say so.

## Before you start

- A git repository with a clean working tree. Commit or stash your changes first.
- `git`, `curl` and `bash`.
- The [GitHub CLI](https://cli.github.com/), signed in with `gh auth login`. You need it for the owner-only setup.
- Your default branch should be named `main`. The GitHub Apps script refuses any other name, and the unattended driver runs only from the default branch.

## Install

Run these from the root of your repository:

```sh
curl -fsSL https://raw.githubusercontent.com/manoochehri/trazo/v0.6.0/scripts/install.sh -o install.sh
bash install.sh install v0.6.0
rm install.sh
```

Then:

1. Read what the script printed. It lists every file it placed and the owner-only steps.
2. Commit the new files on a branch and open a pull request.
3. In your agent, run `/kickoff` and answer its questions. Kickoff writes the charter and plan. It shows them to you before anything is built.

The tag is required. With no tag, the script refuses. `latest` is also accepted. It resolves to the highest `vMAJOR.MINOR.PATCH` tag, never to a branch.

### Options

| Option | Meaning |
|---|---|
| `--adapter claude\|agents\|codex\|both` | Which tool adapter to install. Default `both`: Claude Code and the generic `AGENTS.md` adapter. Use `codex` for Codex project agents and skills. Use `claude` or `agents` for only that one. |
| `--source <path-or-url>` | Where to fetch the release from. Default is `$TRAZO_SOURCE`, then the public repository. The script prints the source it uses. |
| `--sha <commit>` | A full 40-character commit the tag must point to. The script refuses on a mismatch, so you can detect a moved tag. |

## What the installer changes

The script changes only the paths below. It never touches your code, your build or your pipeline.

- **`.trazo/`** is replaced from the tag. `.trazo/VERSION` records the tag and its commit. `.trazo/INSTALLED` lists each adapter file the script placed, with its hash.
- **`.trazo/project/`** is created from blank templates, but only if it does not exist. It is yours. No install or upgrade overwrites it.
- **`AGENTS.md` and `CLAUDE.md`** get one block, between `<!-- trazo:begin -->` and `<!-- trazo:end -->`. Everything outside those markers is left as it was. If a file does not exist, the script creates it.
- **`.claude/agents/` and `.claude/commands/`** get the Trazo files. If a file of the same name is already yours, the Trazo file is installed as `trazo-<name>.md`, and the script says so.
- **`.claude/settings.json`** is installed only if you have none. On upgrade, the script adds the shipped deny rules and hook entries to yours. It writes a `.bak` copy first. Your own entries and your `model` setting are kept. The script prints each change, including any rule it removes.
- **`.codex/agents/` and `.agents/skills/`** get the Codex files, for `--adapter codex` or `both`. Names are prefixed with `trazo-`.
- **The harness** (CI and gates): workflow files under `.github/workflows/` (`ci.yml`, `review.yml`, `report.yml`, `drive.yml`, `owner-merge.yml`, `status.yml`), the pull request template, `scripts/` helpers, `.env.example` with placeholders, a `.gitleaks.toml`, and a placeholder `Dockerfile`. A file you already have is never overwritten.
- **`.github/CODEOWNERS`** is written only if you have none. If you have one, the script prints lines to add and leaves yours alone. A safety limit counts only once you have reviewed it.

The script refuses to run if `.trazo/` exists without `INSTALLED` (an older layout), or if the markers in `AGENTS.md` or `CLAUDE.md` are unbalanced. Fix those by hand, then run it again.

**Start a new session after install or upgrade.** Claude Code loads hooks and settings when a session starts. A session that was already open keeps the old ones.

## Upgrade

Preview first. This prints the diff of `.trazo/` and changes nothing:

```sh
curl -fsSL https://raw.githubusercontent.com/manoochehri/trazo/v0.6.0/scripts/install.sh -o install.sh
bash install.sh upgrade v0.6.0 --dry-run
```

Then apply it:

```sh
bash install.sh upgrade v0.6.0
rm install.sh
```

Commit the result on a branch and open a pull request. Then start a new session.

- Framework files are replaced. Files the new release dropped are removed.
- `.trazo/project/` is never read or written.
- A file in `.trazo/INSTALLED` that you have edited since it was placed is skipped with a warning. On upgrade the script prints the diff so you can merge it by hand.
- Read the printed `- removed` lines in `.claude/settings.json` changes. The `.bak` file has the old version.

## Uninstall

```sh
bash install.sh uninstall
```

This keeps `.trazo/project/`. It removes the framework under `.trazo/`, the adapter and harness files listed in `.trazo/INSTALLED` that you have not edited, and the marked blocks in `AGENTS.md` and `CLAUDE.md`. A file that held only the block is deleted. Your own files stay, including your `.claude/` files, your `.codex/` agents, your `CODEOWNERS`, and `.trazo/project/`.

To remove `.trazo/project/` as well:

```sh
bash install.sh uninstall --purge
```

`--purge` refuses if `.trazo/project/` has uncommitted, untracked or ignored files. Commit or move them first. Only if you accept losing them, add `--force`:

```sh
bash install.sh uninstall --purge --force
```

## Owner setup

Agents never do these steps. They are yours. The installer prints the same list, with your repository name filled in, when it finishes. The steps apply to any release that ships the review and drive workflows.

Replace `owner/name` with your repository. Do the steps in this order: the key, then the Apps, then the review switch. Steps 4 and 5 are for the driver and the code owner.

### 1. Secrets

**`ANTHROPIC_API_KEY`** lets automatic review and the driver call Claude. Set it with:

```sh
gh secret set ANTHROPIC_API_KEY -R owner/name
```

`gh` asks you to paste the key in the terminal. Do not paste it into any chat. In a GitHub organization, set it once as an organization secret.

**Secrets your app needs at runtime** go in your cloud provider's secret store, never in git. Trazo's helper stores a value in AWS Secrets Manager and never prints it:

```sh
bash scripts/put_secret.sh <secret-name> [aws-profile] [region]
```

The script reads the value with hidden input. For a file, set `FILE=path` and leave the prompt empty. The defaults are the `AWS_PROFILE` or `default` profile and the `AWS_REGION` or `us-east-2` region.

Keep local secrets in a `.env` file that git ignores. Copy `.env.example` to `.env` and fill it in. New config goes in `.env.example` as a placeholder.

### 2. The two GitHub Apps

Trazo uses two GitHub Apps. Each one has its own ID and private key:

| App | Secrets it holds | What it does |
|---|---|---|
| `trazo-builder` | `BUILDER_APP_ID`, `BUILDER_APP_PRIVATE_KEY` | The driver uses it to push a branch and open a pull request. |
| `trazo-reviewer` | `REVIEWER_APP_ID`, `REVIEWER_APP_PRIVATE_KEY` | The report job sets the `trazo/verdict` status as this App. Automatic review needs it. |

Both keys are stored as secrets of a GitHub environment named `trazo-apps`. That environment allows only the `main` branch, so only a job running from `main` can read the keys.

The script that creates them is not installed in your repository. Run it from a clone of Trazo, checked out at the tag you installed (v0.6.0 today). You need admin rights on your repository:

```sh
git clone https://github.com/manoochehri/trazo.git
cd trazo
git checkout v0.6.0
zsh scripts/setup_github_apps.zsh --dry-run --repo owner/name
zsh scripts/setup_github_apps.zsh --repo owner/name
```

The first command prints what it would do and changes nothing. The second creates the environment and both Apps. It opens your browser twice: click "Create GitHub App", then install the App on this one repository only. It stores each key itself. You never see or paste a key. It needs `zsh`, `gh`, `jq`, `openssl`, `curl` and `python3`.

Other options: `--only builder` or `--only reviewer` creates one App. `--force` creates an App again even if its secrets exist.

The script is a zsh script, so run it with `zsh`, as shown. A permission error on a `scripts/` file means the executable bit is missing from your clone. That is tracked in [#390](https://github.com/manoochehri/trazo/issues/390).

Check that the `main` branch ruleset requires `trazo/verdict` before you rely on automatic review.

### 3. Automatic review switch

Automatic review is off until you turn it on. Do this last, after the key and the Apps exist:

```sh
gh variable set AUTO_REVIEW_ENABLED --body true -R owner/name
```

Anything other than `true` keeps it off. To turn it off again:

```sh
gh variable delete AUTO_REVIEW_ENABLED -R owner/name
```

The review workflow is described in [ADR 0017](https://github.com/manoochehri/trazo/blob/main/.trazo/project/adr/0017-automatic-review-on-push.md) and [ADR 0028](https://github.com/manoochehri/trazo/blob/main/.trazo/project/adr/0028-report-job-sets-verdict-as-reviewer-app.md).

### 4. Driver switch (UNVERIFIED)

The driver runs `drive.yml` every 30 minutes. It picks the top ready issue. An agent edits a copy of the code. A script with no AI opens the pull request. A merge job merges it only after a passing review verdict for that exact commit, passing checks, and no change to an owner-protected path. See [ADR 0024](https://github.com/manoochehri/trazo/blob/main/.trazo/project/adr/0024-unattended-drive-workflow.md).

**The driver is UNVERIFIED.** Its first two live runs failed. One run did not record a `needs-pm` label on its issue ([#399](https://github.com/manoochehri/trazo/issues/399)). Another picked an issue and produced no pull request ([#401](https://github.com/manoochehri/trazo/issues/401)). The fix for #399 is in progress. Treat the driver as unproven until one full unattended run opens and merges a pull request. Live verification is tracked in [#247](https://github.com/manoochehri/trazo/issues/247).

Leave it off until you can watch a run:

```sh
gh variable set DRIVE_ENABLED --body true -R owner/name
```

Anything other than `true` stops the driver. To stop it:

```sh
gh variable delete DRIVE_ENABLED -R owner/name
```

Optional limits are repository variables. Each has a default, and a bad value falls back to the default:

| Variable | Default | Meaning |
|---|---|---|
| `DRIVE_MAX_MERGES_PER_DAY` | 5 | Merges per UTC day. |
| `DRIVE_MAX_RUNS_PER_DAY` | 4 | Agent runs per UTC day. |
| `DRIVE_MAX_USD_PER_RUN` | 2 | Dollar budget for one agent run, in whole dollars. |

An open issue labeled `drive-halt` stops work and merging. The driver opens one after two failures in a row. It clears itself once, after the fix merges and CI is green ([ADR 0030](https://github.com/manoochehri/trazo/blob/main/.trazo/project/adr/0030-drive-halt-clears-itself-once.md)). The limits are described in [ADR 0027](https://github.com/manoochehri/trazo/blob/main/.trazo/project/adr/0027-drive-spend-cap-and-runaway-guardrails.md).

### 5. Code owners

Open `.github/CODEOWNERS`. The installer guesses your handle from `origin`. Replace it with a person or team that can review. The file lists the paths that only you can change: agent prompts, roles, settings, workflows and the gate. The lines the installer suggests for `.trazo/INSTALLED-settings` belong there too.

## Deploying

Trazo ships no deploy target. Your build and your cloud are yours. Record the deploy, rollback and teardown commands in `.trazo/project/RUNBOOK.md`. If you deploy from CI, gate the deploy on a GitHub environment that needs your approval.

## Related pages

- [In your repo](in-your-repo.md): what the install adds and what stays yours.
- [How it works](how-it-works.md): what the installed rules, roles and checks do.
- [Guardrails and limits](guardrails.md): which limits the owner-only setup creates.
- [Use it](use-it.md): running the repository once it is installed.
