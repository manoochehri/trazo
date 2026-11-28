# Install, upgrade and uninstall

**How do I get Trazo into my repository?** Run the command below at the root of a git repository, then open your agent and run `/kickoff`. The rest of this page covers the upgrade, removal and the owner-only setup.

## Install

You need a git repository, which should have a clean working tree so the changes are easy to review, plus `git`, `curl`, `bash` and the [GitHub CLI](https://cli.github.com/) signed in with `gh auth login`.

```sh
T=$(mktemp -d)
curl -fsSL https://raw.githubusercontent.com/manoochehri/trazo/main/scripts/install.sh -o "$T/install.sh"
bash "$T/install.sh" install latest
```

The installer goes into a temporary directory, not into your repository, so it does not overwrite a file of yours named `install.sh`. `latest` means the highest release tag. The Trazo files themselves come from that release tag, and never from a moving branch.

Or paste this into Claude Code, Codex or any coding agent, from the root of your repository:

> Install Trazo into this repo. Download `https://raw.githubusercontent.com/manoochehri/trazo/main/scripts/install.sh` into a new temporary directory outside the repository (`mktemp -d`), never into the repository, run `bash` on that file with `install latest`, and leave the repository's own files alone. Tell me what it created or changed, read `.trazo/INSTALLED` for the full list of files it placed, and give me the owner-only steps it printed. Do not set secrets or variables.

### What you get

The script prints what it created or changed, any clash or kept file, and the owner-only steps. `.trazo/INSTALLED` lists every adapter and harness file it placed, with its hash. In your repository you now have a `.trazo/` folder with the rules and agent job descriptions, an adapter for your agent (`CLAUDE.md`, `AGENTS.md`, `.claude/`, and `.codex/` only with `--adapter codex`), GitHub workflows, and a blank `.trazo/project/` that is yours. [In your repo](in-your-repo.md) lists each path.

### What to do first

1. Read what the script printed.
2. Commit the new files on a branch and open a pull request.
3. In your agent, run `/kickoff` and answer its questions. Kickoff writes the charter and plan, and shows them to you before anything is built.
4. Start a new agent session after the install, because Claude Code loads hooks and settings only when a session starts.

Everything else, such as automatic review and the unattended drive, is optional. The [owner setup](#owner-setup) below covers it.

### Options

| Option | Meaning |
|---|---|
| `--adapter claude\|agents\|codex\|both` | Which tool adapter to install. Default `both`: Claude Code and the generic `AGENTS.md` adapter, with no Codex agents or skills. Use `codex` for `AGENTS.md` plus Codex project agents and skills. Use `claude` or `agents` for only that one. |
| `--source <path-or-url>` | Where to fetch the release from. Default is `$TRAZO_SOURCE`, then the public repository. The script prints the source it uses. |
| `--sha <commit>` | A full 40-character commit the tag must point to. The script refuses on a mismatch, so you can detect a moved tag. |
| `--dry-run` | Works with `upgrade` only. Never pass it to `install`: the option is ignored there and the install runs for real. |


## What the installer changes

The script changes only the paths below. It never touches your code, your build or your pipeline.

- **`.trazo/`** is replaced from the tag. `.trazo/VERSION` records the tag and its commit. `.trazo/INSTALLED` lists each adapter and harness file the script placed, with its hash.
- **`.trazo/project/`** is created from blank templates. It is yours. Your files in it are never overwritten or removed, and a missing blank template file, such as `ARCHITECTURE_CONTRACT.md`, is created again.
- **`AGENTS.md` and `CLAUDE.md`** get one block, between `<!-- trazo:begin -->` and `<!-- trazo:end -->`. Everything outside those markers is left as it was. If a file does not exist, the script creates it.
- **`.claude/agents/` and `.claude/commands/`** get the Trazo files. If a file of the same name is already yours, the Trazo file is installed as `trazo-<name>.md`, and the script says so.
- **`.claude/settings.json`** is installed only if you have none. On upgrade, the script adds the shipped deny rules and hook entries to yours. It writes a `.bak` copy first. Your own entries and your `model` setting are kept. The script prints each change, including any rule it removes.
- **`.codex/agents/` and `.agents/skills/`** get the Codex files, for `--adapter codex` only. Names are prefixed with `trazo-`.
- **The harness** (CI and gates): workflow files under `.github/workflows/` (`ci.yml` always, and `review.yml`, `report.yml`, `drive.yml`, `owner-merge.yml` and `status.yml` with the Claude adapter, that is `claude` or `both`), the pull request template, `scripts/` helpers, `.env.example` with placeholders, a `.gitleaks.toml`, and a placeholder `Dockerfile`. A file you already have is never overwritten.
- **`.github/CODEOWNERS`** is written only if you have none. If you have one, the script prints lines to add and leaves yours alone. A safety limit counts only once you have reviewed it.

The script refuses to run if `.trazo/` holds anything besides `project/` and has no `INSTALLED` file (an older layout), or if the markers in `AGENTS.md` or `CLAUDE.md` are unbalanced. Fix those by hand, then run it again.

**Start a new session after install or upgrade.** Claude Code loads hooks and settings when a session starts. A session that was already open keeps the old ones.

## Check which version you have

The file `.trazo/VERSION` in your repository records the release you installed and its commit. It can be older than the newest release. The newest release is the highest tag on the [tags page](https://github.com/manoochehri/trazo/tags), and what changed is in the [changelog](changelog.md).

## Upgrade

Preview first. This prints the diff of `.trazo/` and changes nothing:

```sh
T=$(mktemp -d)
curl -fsSL https://raw.githubusercontent.com/manoochehri/trazo/main/scripts/install.sh -o "$T/install.sh"
bash "$T/install.sh" upgrade latest --dry-run
```

Then apply it, in the same terminal so that `$T` is still set:

```sh
bash "$T/install.sh" upgrade latest
```

Commit the result on a branch and open a pull request. Then start a new session.

- Framework files under `.trazo/` are replaced, and any the new release dropped are removed.
- Your files in `.trazo/project/` are never overwritten or removed. A missing blank template file is created again.
- A file in `.trazo/INSTALLED` that you have edited since it was placed is skipped with a warning. On upgrade the script prints the diff so you can merge it by hand.
- Read the printed `- removed` lines in `.claude/settings.json` changes. The `.bak` file has the old version.

To hand the upgrade to your agent, paste: "Upgrade Trazo in this repo. Download `https://raw.githubusercontent.com/manoochehri/trazo/main/scripts/install.sh` into a new temporary directory outside the repository (`mktemp -d`), never into the repository. Run `bash` on that file with `upgrade latest --dry-run` and show me the diff. Then run it without `--dry-run`. List any deny rule the upgrade removed from `.claude/settings.json`. Do not touch `.trazo/project/`."

### If the upgrade reports a script out of step

Some files Trazo places must move together: a workflow and the scripts it calls, such as `scripts/report_verdict.py`. If the installer says that a script you edited is older than its workflow, compare your copy with the same file at the release tag and update it in a pull request. Issue [#435](https://github.com/manoochehri/trazo/issues/435) is making the installer say this itself.

## Uninstall

```sh
T=$(mktemp -d)
curl -fsSL https://raw.githubusercontent.com/manoochehri/trazo/main/scripts/install.sh -o "$T/install.sh"
bash "$T/install.sh" uninstall
```

This keeps `.trazo/project/`. It removes the framework under `.trazo/`, the adapter and harness files listed in `.trazo/INSTALLED` that you have not edited, and the marked blocks in `AGENTS.md` and `CLAUDE.md`. A file that held only the block is deleted. Your own files stay, including your `.claude/` files, your `.codex/` agents and `.trazo/project/`. The installer does not remove `.github/CODEOWNERS`, even one it created.

To remove `.trazo/project/` as well, add `--purge`. It refuses if `.trazo/project/` has uncommitted, untracked or ignored files, so commit or move them first. Only if you accept losing them, add `--force` too.

To hand the removal to your agent, paste: "Remove Trazo from this repo. Download `https://raw.githubusercontent.com/manoochehri/trazo/main/scripts/install.sh` into a new temporary directory outside the repository (`mktemp -d`), never into the repository, and run `bash` on that file with `uninstall` (this keeps `.trazo/project/`). Do not use `--purge` unless I say so."

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

The script that creates them is not installed in your repository. Run it from a clone of Trazo, checked out at the tag in the first line of your `.trazo/VERSION` (written as `TAG` below). You need admin rights on your repository:

```sh
git clone https://github.com/manoochehri/trazo.git
cd trazo
git checkout TAG
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

**The driver is UNVERIFIED.** It was triggered on a schedule from 2026-10-31 but only ran for real from 2026-11-23, when it was switched on in the Trazo repository, and it opened one pull request, #312, which was closed unmerged. A watched run on 2026-11-28 made no change and exposed a bug ([#399](https://github.com/manoochehri/trazo/issues/399)). Treat the driver as unproven until one full unattended run opens and merges a pull request. Live verification is tracked in [#247](https://github.com/manoochehri/trazo/issues/247).

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

An open issue labeled `drive-halt` stops work and merging. The driver opens one after two failures in a row. It can clear itself once, after the fix merges and CI is green ([ADR 0030](https://github.com/manoochehri/trazo/blob/main/.trazo/project/adr/0030-drive-halt-clears-itself-once.md), which is still proposed). The self-clear also needs the repository variable `DRIVE_BUILDER_APP_LOGIN` set to the builder App's login, for example `name[bot]`. Without it the halt waits for you to close it. The limits are described in [ADR 0027](https://github.com/manoochehri/trazo/blob/main/.trazo/project/adr/0027-drive-spend-cap-and-runaway-guardrails.md).

### 5. Code owners

Open `.github/CODEOWNERS`. The installer guesses your handle from `origin`. Replace it with a person or team that can review. The file lists the paths that only you can change: agent prompts, roles, settings, workflows and the gate. The lines the installer suggests for `.trazo/INSTALLED-settings` belong there too.

## Deploying

Trazo ships no deploy target. Your build and your cloud are yours. Record the deploy, rollback and teardown commands in `.trazo/project/RUNBOOK.md`. If you deploy from CI, gate the deploy on a GitHub environment that needs your approval.

## Related pages

- [In your repo](in-your-repo.md): what the install adds and what stays yours.
- [How it works](how-it-works.md): what the installed rules, roles and checks do.
- [Guardrails and limits](guardrails.md): which limits the owner-only setup creates.
- [Day to day](day-to-day.md): running the repository once it is installed.
