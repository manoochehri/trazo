# Install, upgrade and uninstall

Trazo is installed into your repository from a release tag, by one script. Nothing is
copied from a template repository and nothing is fetched from a moving branch.

## Install

From the root of your git repository:

```sh
curl -fsSL https://raw.githubusercontent.com/manoochehri/trazo/v0.3.1/scripts/install.sh -o install.sh
bash install.sh install v0.3.1
```

Pin the script to the same tag you install, as above. The tag is required: with none, the
script refuses. `latest` is accepted and resolves to the highest `vMAJOR.MINOR.PATCH` tag,
never to a branch.

| Option | Meaning |
|---|---|
| `--adapter claude\|agents\|codex\|both` | Which tool adapter to install. Default `both` (Claude and the generic `AGENTS.md` adapter). Use `codex` for Codex's project agents and skills. |
| `--source <path-or-url>` | Where to fetch from. Default `$TRAZO_SOURCE` (announced when used), then the public repository. A value starting with `-` is refused. |
| `--sha <commit>` | Optional full 40-hex commit the tag must resolve to; refuses on a mismatch. Use it to detect a moved tag. |

What it does:

- Copies the framework (`rules.md`, `ADVISOR.md`, `ARCHITECTURE.md`, `templates/`) into
  `.trazo/` and writes the tag and its resolved commit to `.trazo/VERSION`. The source, tag and
  commit are printed. Tags containing symlinks under `src/` are refused.
- Creates `.trazo/project/` from the blank templates **only if it does not exist**. It is
  yours, and no command here overwrites it.
- Inserts the adapter into `AGENTS.md` and/or `CLAUDE.md` between
  `<!-- trazo:begin -->` and `<!-- trazo:end -->`. If the file exists, everything outside
  those markers is left byte for byte as it was; if it does not, it is created. Running
  install again replaces the block and nothing else.
- For the Claude adapter, copies `agents/` and `commands/` into `.claude/`. If a file of
  that name is already yours, the Trazo one is installed as `trazo-<name>.md` and the
  script says so. `.claude/settings.json` is installed only if you have none; on upgrade, an existing one gets
  the shipped deny rules and hook entries merged in (additive, idempotent, `.bak` written first,
  `model` and your own entries untouched; invalid JSON is refused). The merge also removes, and
  prints, a deny rule or hook entry that the installer itself added earlier and the new release
  no longer ships. What it added is recorded in `.trazo/INSTALLED-settings` (installer-owned,
  removed by uninstall); a rule you wrote is never removed. A rule that predates that record is
  kept and reported as `kept (not recorded as installer-added): "<rule>"`, with the line you can
  delete. A recorded rule is removed only while the shipped engineer Bash guard hook is installed
  and registered; otherwise it is kept and reported. Because the record decides what is
  removed, `.trazo/INSTALLED-settings` belongs in `CODEOWNERS` (the installer's starter and its
  printed lines include it). Read the printed `- removed` lines; the `.bak` has the old file.
- For Codex, inserts the `AGENTS.md` adapter block and installs project-scoped role agents
  under `.codex/agents/` and workflow skills under `.agents/skills/`. Both point to the
  canonical roles and rules in `.trazo/`. Existing host files are preserved; on a name
  clash, Trazo prefixes the installed name and reports it.
- Records a sha256 and path for each adapter file it placed in `.trazo/INSTALLED`, so upgrade
  and uninstall touch only those. A listed file you have edited since is never overwritten
  or deleted: the script warns and, on upgrade, prints the diff. Entries outside
  the supported adapter and harness paths make the script refuse.
- Prints the `settings.json` it installs. It only denies reads of secrets.
- Refuses if `.trazo/` exists without `INSTALLED` (an older layout), and on unbalanced
  markers in `AGENTS.md` or `CLAUDE.md`.
- Writes a starter `.github/CODEOWNERS` only if you have none. It never edits an existing one;
  it prints lines for you to add. A safety limit only counts if you review it.

## Upgrade

```sh
bash install.sh upgrade v0.3.1 --dry-run   # show the diff of .trazo/ and stop
bash install.sh upgrade v0.3.1             # show the diff, then apply
```

Upgrade is install at a newer tag, with a unified diff of `.trazo/` printed before anything
changes. Framework files are replaced (files dropped upstream are removed). `.trazo/project/`
is never read or written.

## Uninstall

```sh
bash install.sh uninstall            # keeps .trazo/project/
bash install.sh uninstall --purge    # removes it too; refuses if it has uncommitted, untracked or gitignored files
bash install.sh uninstall --purge --force   # ...unless you pass --force
```

Removes the framework files under `.trazo/`, the adapter and harness files listed in
`.trazo/INSTALLED` (the ones you have not edited), and the marked blocks in `AGENTS.md` and `CLAUDE.md`. A file that held
only the block is deleted; otherwise your content stays. Your own `.claude/` files, your
`.codex/` agents, `.agents/skills/`, `CODEOWNERS`, and `.trazo/project/` (without `--purge`)
are not touched.

## What the installer places

Besides `.trazo/` and the adapter, a release that ships the harness (`src/harness/`; `v0.3.0`
and later) also places CI and helper files. A path you already have is never overwritten.

### The harness

The harness comes from `src/harness/`. The installer never overwrites a path you already have (a file it placed that you then edit is kept too):

- CI: `ci.yml` (secret scan, PR evidence check), and with the Claude adapter `review.yml` (automatic review, off until `AUTO_REVIEW_ENABLED` is `true`), `report.yml` (sets `trazo/verdict` as the reviewer App, in the `trazo-apps` environment) and `drive.yml` (off until `DRIVE_ENABLED` is `true`; unset on a fresh install)
- `.gitleaks.toml`, `.pre-commit-config.yaml`, `scripts/scan.sh`, `scripts/scan-preflight.sh`
- the PR template and `scripts/check_pr_evidence.py`, so a missing review-rounds, defects or fail-first field fails CI; `scripts/report_verdict.py`, `scripts/drive_guard.py` and `scripts/drive_sweep.py`
- `scripts/put_secret.sh` (stores a secret in AWS Secrets Manager) and an `.env.example` of placeholders
- a starter `.github/CODEOWNERS` for agent prompts, roles, settings and the gate, only if you have none; with one, suggested lines are printed instead

The test command in `ci.yml` and the `Dockerfile` depend on your stack, so they are placeholders that fail until `/kickoff` asks and sets them. `docs.yml` is not shipped: it builds this repository's own MkDocs site. At the end the installer prints only the owner-only steps: the `ANTHROPIC_API_KEY` secret, the `AUTO_REVIEW_ENABLED` variable, the `trazo-apps` environment and GitHub App setup (for automatic review and drive), and keeping `DRIVE_ENABLED` unset until one watched run.

### What `/kickoff` sets up, or asks you to add

Run after install. It interviews you, then writes and configures:

- the charter (goal, budget, success criteria, stop rule) and `PLAN.md`, shown to you for approval before anything is built
- a `SKEPTIC_BAR.md` specialised to what counts as a valid result in your domain
- GitHub labels, milestones and first issues; a Project board if `gh` supports it
- a ruleset on `main` (no force pushes or deletion, pull request and passing CI required) and GitHub secret scanning with push protection
- `make setup`, `make test` and `make scan` run once, with failures fixed
- where the project runs, recorded in the runbook and architecture; if it deploys anywhere, a budget alert and the teardown command

## Owner setup

The short version, with commands, is in the [README](https://github.com/manoochehri/trazo#set-it-up).
The installer prints the same steps at the end, with your repo name filled in. Secrets, variables
and settings are yours; the installer never sets them.

| Item | What it does |
|---|---|
| `ANTHROPIC_API_KEY` secret | Lets automatic review and the driver call Claude. One per repo, or one organization secret. |
| `AUTO_REVIEW_ENABLED` variable | Automatic review runs only when it is `true`. Unset means off. |
| `trazo-apps` environment | Holds the GitHub App keys. Limited to deployment branch `main`, so only a job running from `main` can read them. |
| `BUILDER_APP_ID`, `BUILDER_APP_PRIVATE_KEY` | The builder App. The driver uses it to push a branch and open a pull request. |
| `REVIEWER_APP_ID`, `REVIEWER_APP_PRIVATE_KEY` | The reviewer App. The review path's `workflow_run` report job sets the `trazo/verdict` status as the reviewer App (#291, merged to `main`, so in the next release). Still yours to do: pin that status to the reviewer App in the branch ruleset (#212). |
| `DRIVE_ENABLED` variable | Kill switch for `drive.yml`. Anything but `true` and it does nothing. |

**Where the Apps script comes from.** `scripts/setup_github_apps.zsh` is not installed in a host.
Run it from a clone of Trazo with `--repo owner/name`, as someone with admin rights on that repo.
The `v0.3.0` tag contains it; check out the tag you installed.
It creates the environment, then each App through GitHub's manifest flow, stores the id and key as
environment secrets, checks the key works and that GitHub granted exactly the permissions asked
for, and waits until the App is installed on the one repo. No key is printed or written to a file.
Options: `--dry-run`, `--only builder|reviewer`, `--force` (create another App even if the secrets exist).

**Known gap.** The script names the environment's branch rule `main` and refuses anything else, so
it works only for a host whose default branch is `main`. Drive runs only from the default branch.
The installer's step 3 says "your default branch"; the script has no option for it yet.

**The driver.** `drive.yml` runs every 30 minutes. It picks the top ready issue; an agent with a
read-only token edits a copy of the code; a script with no AI opens the pull request; a merge job
squash-merges it only after a passing review verdict for that exact commit, passing checks, and no
change to an owner-protected path. Limits (merges and runs per day, dollars per run) are optional
repository variables; see the header of `drive.yml`. It has not been verified on a live run
(#247, v0.4.0). Turn it on, watch one run, and unset `DRIVE_ENABLED` if anything looks wrong.
