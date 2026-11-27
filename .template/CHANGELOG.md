# Trazo changelog

## 0.5.0 (2026-11-27)
Reviewer and security can post their own status again, review runs only for risky paths, and the owner-merge gate depends on what a pull request changes.
- #319 A front-door guard hook stops the main session from editing files outside `.trazo/project/` or from pushing and merging; engineering goes through `/work` (live behavior UNVERIFIED, see below)
- #359 The review gate counts a verdict or security status only for the current head and the current PR-body evidence; editing the evidence starts a fresh review
- #364 The engineer Bash guard no longer blocks reviewer and security from posting their own commit status; it allows the two read-only lookups the role files use
- #371 Reviewer and security role files read the head SHA and evidence digest first, then post their status with one plain call using literal values
- #367 Reviewer and security run only for risky paths (hooks, workflows, settings and permissions, dependencies, rulesets, secrets, CODEOWNERS, rules and role files). Docs-only and `.trazo/project/` pull requests get a Coordinator check of diff and CI instead (ADR 0031, which supersedes the "every pull request" routing in ADR 0029)
- #320 (partial) The owner-merge gate depends on path risk. Docs-only pull requests merge on green CI with no reviewer status. Risky pull requests still need reviewer and security success on the current head. Owner-only paths (CODEOWNERS) are unchanged. Only the latest check run per name counts, so a re-run replaces an old failure. Ruleset rollback tooling (`scripts/rollback_ruleset.sh`) restores the saved "protect main" ruleset and refuses when the live copy differs in name.
- #252 The drive workflow ships switched off (`DRIVE_ENABLED` unset) and is UNVERIFIED on a live run. The supervised first run (#247) is not in this release.

Not in 0.5.0
- Pinning `trazo/verdict` to the reviewer App. The scratch pin test (`scripts/scratch_pin_test.sh`) ships as a script only; it has not been run and pins nothing.
- The restricted agent token (#366).

Upgrading from 0.4.2
- Run `install.sh upgrade v0.5.0` (use `--dry-run` first). `.trazo/` is replaced from the tag; `.trazo/project/` is never touched.
- The front-door guard hook is new. UNVERIFIED: its input shape has not been checked on a live run. After upgrading, probe it once: ask the main session to edit a file outside `.trazo/project/`; the edit should be refused. The hook fails closed, so a mismatch blocks the action rather than allowing it.
- Owner merges of docs-only pull requests need no reviewer status; risky pull requests are unchanged.

## 0.4.2 (2026-11-25)
Coordinator action loop and canonical architecture baseline.
- #353 Make the Coordinator action-first and remove routine owner merge handoffs
- #356 Establish the canonical architecture and design index

## 0.4.1 (2026-11-25)
Follow-up fixes for the gated workflow, installer upgrades, and front-door brevity. This patch release hardens the Coordinator's merge guard and makes installer settings-record updates safe against redirected or partial writes.
- #343 Harden workflow-dispatch and rerun guards against shell-segment and substitution bypasses
- #340 Fix the PR evidence template and engineer guidance
- #344 Upgrade this repository's own install to Trazo v0.4.0
- #346 Make installer settings-record upgrades safe, including non-regular-file rejection and atomic writes
- #347 Let reviewer and security roles post their own commit status
- #351 Enforce concise three-line Coordinator replies with mechanical tests

## 0.4.0 (2026-11-25)
Agents are pinned and guarded: engineers run as pinned subagents behind new guard hooks, the front door can merge a reviewed PR through a gated workflow, upgrades merge settings for you, and a halted driver can clear itself.
- #315 Fix the unattended driver's first live PR, which committed empty dependency files and used a wrong `Closes` keyword
- #321 Add an owner-triggered merge workflow (`owner-merge.yml`) for any green PR with verdicts, not only Drive branches
- #322 The evidence check accepts headings and re-runs when the PR body is edited
- #323 Fix the `/trazo` skill: one reply budget, and it reports auto-merge state and a stale STATUS first
- #326 Only pinned Trazo roles may start as subagents: a role guard hook blocks generic subagents, and engineer, senior-engineer and architect agents are pinned; `/eng` and `/senior-eng` now start those agents
- #330 Add an engineer Bash guard hook that denies `gh api` writes, merges, status setting and secret reads through routes the deny rules missed
- #332 A drive halt clears itself once after the fix merges and CI is green
- #333 The front door merges a reviewed PR by dispatching `owner-merge.yml`, which re-checks the review, CI and security at the exact head. `gh pr merge` stays denied and the engineer Bash guard allows only that one dispatch command. This loosens a safety limit on the owner's instruction, and the engineer-facing wording in `rules.md` changes with it. The shared owner login can still forge statuses until the restricted agent token (#320) lands, planned for 0.4.1.
- #328 (first step, #334) Add a read-only STATUS generator (`scripts/gen_status.py`) and a manually dispatched status workflow (`status.yml`) that print the status block from live GitHub data; scheduled updates are not in yet
- #337 `install.sh upgrade` merges the new hooks and deny rules into an existing `.claude/settings.json`

Upgrading from 0.3.1
- Run `install.sh upgrade v0.4.0` (use `--dry-run` first). `.trazo/` is replaced from the tag; `.trazo/project/` is never touched.
- The upgrade now merges the new hooks and deny rules into an existing `.claude/settings.json` itself, with a backup in `.claude/settings.json.bak` (#337).
- New files shipped: the `owner-merge.yml` and `status.yml` workflows, `scripts/gen_status.py`, the agent role guard and engineer Bash guard hooks, and pinned engineer and senior-engineer agents. `/eng` and `/senior-eng` now start those agents.
- Set the repository variable `DRIVE_BUILDER_APP_LOGIN` to the builder App's login (for example `trazo-builder[bot]`). Without it the halt auto-clear (#332) does nothing.
- UNVERIFIED: the new hooks' input shape has not been checked on a live run. They fail closed, so a mismatch blocks the action rather than allowing it.
- The engineer Bash guard is a speed bump, not a security boundary. A restricted agent token (#320) is the real fix, planned for 0.4.1.
- Not in 0.4.0 (moved to 0.4.1): faster tests (#341) and the restricted agent token (#320). The scheduled STATUS PR and its merge path also remain in 0.4.1, under #328.

## 0.3.1 (2026-11-22)
Fixes two v0.3.0 problems: the main session stalling on a menu instead of acting, and agents unable to deploy.
- #304 The main session is the front door: `rules.md` and both adapters define it, `/trazo` reports what it is doing and dispatches the PM instead of printing "You could say" (ADR 0029, extends 0025)
- #306 The shipped `settings.json` no longer denies deploy commands (`fly`, `flyctl`, `clasp push/deploy`, `scripts/deploy*`) for every agent. A deny rule binds every session and cannot be overridden when the owner asks for a deploy; the PM is still kept off deploys by its Bash allowlist. Merge, secret, variable and workflow-dispatch denies stay.

Upgrading from 0.3.0
- Run `install.sh upgrade v0.3.1` (use `--dry-run` first). `.trazo/` is replaced from the tag; `.trazo/project/` is never touched.
- If you merged v0.3.0's `.claude/settings.json` into yours, delete the `fly`, `flyctl`, `clasp push`, `clasp deploy` and `scripts/deploy` lines from `permissions.deny` yourself: the installer never edits that file.
- `rules.md` gains a "Front door" section: agents act on what's next instead of waiting to be told.

## 0.3.0 (2026-11-22)
Agents decide and ship. Read "Before you enable anything", "Known limits for hosts" and
"Upgrading from 0.2.0" first.

**Status of the driver, stated plainly.** The unattended driver (`drive.yml`) ships switched
off (`DRIVE_ENABLED` unset) and has NOT been verified on a live run: #247 (the supervised first
run) moved to v0.4.0. The GitHub App identity (#252) is partly in place: the setup script and the
drive publish job's builder token exist, and the reviewer App path is the report job below; none
of it has run live. Treat all of it as UNVERIFIED.

Driver and guardrails
- #246 Add the unattended drive workflow with gated auto-merge (ADR 0024); off by default
- #249 Cap spend per drive run
- #258 Runaway guardrails: merge cap, one PR in flight, drive-halt circuit breaker
- #262 Liveness sweeper re-runs stalled reviews and flags stalled issues
- #273 Auto-merge sensitive list covers the files the stop list protects
- #252 (partial) Owner-run `scripts/setup_github_apps.zsh` creates the builder and reviewer Apps
  and stores their keys in the `trazo-apps` environment; the drive publish job mints a builder
  token from it
- Refs #291 A `report` job sets `trazo/verdict` as the reviewer App from the default branch
  (ADR 0028, PR #294); `review.yml` holds no key and sets no status

Agent behavior
- #266 Decide, then tell: agents stop waiting on reversible questions (ADR 0026, loosens a gate in `rules.md`)
- #279 The PM cannot deploy, merge, push or set secrets: enforced by a hook and deny rules, not only by prompt

Protections
- #231 CODEOWNERS covers the review-gate role definitions
- #281 CODEOWNERS narrowed per owner decision to what governs agents (rules, roles, skills,
  adapters, agent instruction files, workflows, charter); everything else is agentic
- #263 Release-tag creation is restricted by an owner-run script (`scripts/protect_release_tags.py`);
  release tags are protected against forged `latest`

Installer
- #272 The installer resolves release tags, not a branch with the same name
- #285 The installer ships the full harness to hosts: CI, review, report and drive workflows (Claude
  adapter), PR template, secret scanning, `put_secret.sh`, evidence and verdict scripts,
  `.env.example`, placeholder Dockerfile, and a CODEOWNERS starter

Docs
- The README now has how-tos for installing from scratch, upgrading, and setting up the GitHub Apps

Before you enable anything (owner-only; the installer prints these and sets none of them)
- `ANTHROPIC_API_KEY` secret, for automatic review and drive
- `AUTO_REVIEW_ENABLED=true` variable to turn on automatic review (default off). Automatic review
  also needs the reviewer App and the `trazo-apps` environment: `report.yml` sets `trazo/verdict`
  as the reviewer App
- the `trazo-apps` environment (deployment branches: `main` only) and the builder and reviewer
  Apps, made with `scripts/setup_github_apps.zsh` from this tag (not installed in your repo)
- `DRIVE_ENABLED=true` only when you can watch a run; unset it if anything looks wrong

Known limits for hosts
- The GitHub Apps setup script is not shipped to hosts yet (run it from a checkout of this tag)
  and only supports a default branch named `main` (follow-up: #296).
- The driver and the App identity have not run live (#247, v0.4.0).

Upgrading from 0.2.0
- Run `install.sh upgrade v0.3.0` (use `--dry-run` first). `.trazo/` is replaced from the tag, so
  hand edits inside `.trazo/` (outside `.trazo/project/`) are lost; `.trazo/project/` is never touched.
- Harness files are new to you: a path you already have (your own `ci.yml`, PR template,
  Dockerfile and so on) is kept, not overwritten. Files Trazo placed and you edited are left with a diff.
- `review.yml`, `report.yml` and `drive.yml` are placed with the Claude adapter. `review.yml` and
  `drive.yml` do nothing until you set the variables above; `report.yml` sets `trazo/verdict` as
  the reviewer App and needs that App and the `trazo-apps` environment. If you do not want them,
  delete them.
- An existing `.github/CODEOWNERS` or `.claude/settings.json` is never edited. A host with no
  CODEOWNERS gets a starter on upgrade; otherwise add the suggested lines yourself. Merge the new
  deny rules and the PreToolUse hook entry from `src/adapters/claude/settings.json` in the Trazo
  repo at v0.3.0 yourself; without that merge you do not get the PM guard.
- `rules.md` changes behavior: agents now decide reversible choices and record `Decided:` on the
  issue instead of asking.

## 0.2.0 (2026-10-13)
- #187 Attribute role-authored GitHub comments and issues
- #192 Split the engineer role into eng (junior) and senior eng
- #193 Add a Architect / head-of-eng role: keeper of the big picture
- #194 PM role: dispatch open items instead of reporting them, and post answers on the issue
- #195 Reviewer and skeptic output: bullets, severity discipline, evidence folded
- #203 Ship senior engineer role file, /senior-eng command and Codex agent (ADR 0016)
- #204 trazo/verdict frequently is red in issues
- #209 the PM role has lost all power
- #216 Engineers wait for CI, fix obvious failures, then request review
- #218 more clarity for questions to owner: plain language, less jargon, Include pros and cons
- #222 Ship the 'only /wrapup writes STATUS.md' rule to hosts (src/overlay)
- #224 Automatic review can credit a stale head's merge to a newer head
- #225 CI workflows pin third-party actions by tag, not by commit

## 0.1.0 (2026-10-08)
- #96 Repoint the adapters and fix tests naming the old layout
- #97 Move this repo charter + ADRs into .trazo/project/
- #98 Update the handbook and README for the src/ + .trazo/ layout
- #99 Supersede the stale paths in ADRs 0005-0008
- #107 Retire the gh-repo-create --template path once src/ is the install route
- #111 Move this repo own docs/ state into .trazo/project/ and ship hosts a blank docs/ template
- #113 Agent session doesn't proactively read a project's standing-rules/decision-record directory before acting
- #114 Repo cleanup: remove files left over from the starter-template era
- #116 Make the model behind each role visible and pinned (Sonnet for eng, Opus for the rest)
- #118 Distribution: how a host installs and upgrades Trazo (npx vs alternatives, existing AGENTS.md/CLAUDE.md)
- #121 Remove stale deploy/build references and decide the lessons file's fate
- #122 Fix .claude/ vs src/adapters/claude/ drift and add a test that they match
- #126 Test: every CODEOWNERS path must match a real file or directory
- #127 Let the PM clear needs-decision once the owner has decided, with a quoted record
- #130 make release: build the changelog from the milestone's closed issues
- #133 src/adapters/AGENTS.md ships Trazo-specific lines into host repos
- #134 Owner: protect release tags and the shipped installer before v0.1.0
- #135 Installer hardening: findings from the #132 review and security pass (merged before the fixes)
- #139 Land the review fixes that #136 and #137 merged without
- #141 install.sh uninstall --purge silently deletes gitignored files in .trazo/project/
- #143 README overclaims what a host gets, and points at a version that contradicts v0.1.0
- #147 kickoff.md still carries semilla-era wording ("created from semilla", copying templates/docs/)
- #148 Enforce verify-don't-assume: cited spec before code, fakes built from real sources
- #149 Tests fail on the old code first, with output in the PR; report review rounds
- #150 Hard role boundaries: PM decides with a source and owns dates; no prod access unasked; pressure never drops a gate
- #151 Token budget rule: one session per task, no polling, state in the tracker
- #152 Owner messages: short, decision-first, at most one command, no homework
- #153 ADR 0013: what a version number means (PATCH vs MINOR)
- #154 Stop doc drift: status line on every project doc, link don't restate, make docs-check
- #155 No stacked PRs: every PR targets main, and head branches auto-delete on merge
- #156 Gates must hold without routines: the owner talks to the PM in plain English, never runs /work or /kickoff
- #157 Define the boundary between `AGENTS.md` and Trazo
- #160 Add an OpenAI Codex adapter for shared Trazo roles and workflows

## Pre-release development history

Versions below record development before the first tagged release. They are retained as
historical notes and do not claim that those versions were published.

### 0.6.0 (2026-09-30)
- **A release is now a git tag.** `make release` validates the tree, the version, and
  the changelog, then creates and pushes annotated tag `vX.Y.Z`. `latest` means the
  highest release tag. Until this shipped the repository had **zero tags**, so no host
  could pin a version — see `.trazo/adr/0006-release-process.md`.
- New rule in `.trazo/rules.md`: *releases are immutable tags* — never a branch, never a
  moved tag, always cut from an already-pushed commit.
- `CONTRIBUTING.md` records that the version bump and the changelog entry ship in the
  same commit, and that the release is cut after merge.
- The earlier `0.1.0` through `0.5.0` development snapshots below were never tagged and
  are not backfilled. This release reuses `0.1.0` as the first published version; its
  tag points to this release commit, not to the old development snapshot. `0.6.0` was
  the first version intended to be released as a tag, but that release was withdrawn.

---

## Versions withdrawn on 2026-10-01

At the time this withdrawal was recorded, no version above `0.6.0` was released. This
section records what the file used to claim, and why it no longer does.

Entries `0.7.0`, `0.8.0` and `0.9.0` appeared here as released versions. Two of them
(`v0.7.0`, `v0.9.0`) were cut as tags; `0.8.0` never was. **Both tags were deleted on
2026-10-01** because the product was not finished, and nobody could have been holding
them: no installer resolved tags (#53 is open), and no script in `scripts/` reads a ref.

Leaving the entries above would make the changelog claim releases that a consumer cannot
resolve, which is the exact defect this file exists to prevent. The work described in
those entries was real and is preserved in git history; it simply was not a release.

See `.trazo/adr/0009-tag-immutability-binds-from-first-consumer.md`: a tag is immutable
from the first *external consumer*. The `0.1.0` entry above records the first honest
published version; this section remains as pre-release history.

### 0.5.0 (2026-09-28)
- Role commands: `/pm`, `/security`, `/reviewer`, and `/eng` in `.claude/commands/`.
  Each command switches the session into that role directly for subsequent conversation turns
  until another role command is used.
- One-liner prompt response pattern: when invoked without arguments, roles reply with a brief
  one-liner acknowledgment and model switch tip (e.g., `(tip: /model opus)`) rather than
  printing unprompted reports; when invoked with arguments, they answer immediately.
- Non-engineer roles (`pm`, `security`, `reviewer`) enforce read-only instructions (no code or config edits).
- Preserved `.claude/agents/*.md` for one-off subagent delegation from the engineer session.
- Updated documentation across `CLAUDE.md`, `README.md`, handbook (`index.md`, `guide.md`, `playbook.md`, `team.md`),
  and `.claude/commands/semilla.md`.

### 0.4.0 (2026-09-27)
- Docs site: MkDocs + Material, source in `handbook/` (not `docs/`, which stays project
  scaffolding). Moved `GUIDE.md` and `PLAYBOOK.md` into `handbook/`; added a Home page, a
  team page, and pages that include (not copy) `.template/LESSONS.md`, `CHANGELOG.md`, and
  `CONTRIBUTING.md`. Converted the playbook's ASCII game-loop diagram to Mermaid.
- Added an original flat SVG logo (seed/sprout) as the site logo, favicon, and README mark.
- `.github/workflows/docs.yml`: builds on every PR (`mkdocs build --strict`, fails on broken
  links) and deploys to GitHub Pages on merge to `main`, gated to `manoochehri/semilla` so
  projects created from the template don't publish by accident.
- `make docs` to preview locally. Kickoff gained an optional "publish a docs site?" question
  (default no); saying no removes `handbook/`, `mkdocs.yml`, and the docs workflow.

### 0.3.0 (2026-09-27)
- Add `.template/PLAYBOOK.md`: the daily loop (the "game loop" diagram), the team table, and
  an FAQ covering planning, building, reviewing, deploying, money/safety, and troubleshooting.
  Linked from both READMEs and cross-linked with `.template/GUIDE.md`.

### 0.2.1 (2026-09-27)
- Fixed `.github/CODEOWNERS` not protecting itself: the publish-time find/replace had rewritten
  the path to `.github/CODE<user>S`, so the file matched no rule and could be edited without owner
  review (issue #14, present since 0.1.0).
- `scripts/publish_template.sh` now substitutes the `{{OWNER}}` placeholder — never a bare `OWNER`,
  which is a substring of `CODEOWNERS` — and warns when there is nothing to replace.
- `/kickoff` replaces placeholders and `@handles` only, never the paths in CODEOWNERS.
- Tests: CODEOWNERS must cover itself and its paths must not contain the owner's name (issue #14);
  the publish script is exercised against a throwaway fixture with stub `git`/`gh`.

### 0.2.0 (2026-09-27)
- Subagents in `.claude/agents/`: pm, reviewer, security (Opus, read-only).
- Commands streamlined: `/semilla` (menu), `/work`, `/check-pr`, `/pm`, `/brief` (was `/status`, which clashed with a built-in); `/improve-template` and `/sync-template` renamed `/template-improve` and `/template-sync`.
- `CLAUDE.md` gains a team table and a plain-English → routine map, so commands are optional.
- Kickoff: branch-protection ruleset with a solo-owner caveat (no required approvals, since GitHub won't let an owner approve their own PR).
- `.template/GUIDE.md` rewritten: the AI team, subagents, the GitHub Actions engineer/reviewer/PM setup, and an expanded command table.

### 0.1.1 (2026-09-27)
Fixed the first-run CI failure: a job-level `hashFiles()` condition is invalid on GitHub
Actions and was moved inside the step. Switched gitleaks in CI from a Docker container to
a downloaded binary (the container tripped git's "dubious ownership" check on runners).
Fixed the Dockerfile so `uv run` doesn't try to write to the root-owned venv as a non-root
user (venv's `bin` added to `PATH`, entrypoint runs `python` directly). Grouped Dependabot
updates (uv, GitHub Actions). Updated pre-commit hook versions. Added `.template/GUIDE.md`,
linked from both READMEs.

### 0.1.0 (2026-09-27)
Initial version, distilled from a real project: docs-as-code state, decision records,
workstreams, advisor role, secrets-first setup, Python/uv/Docker, CI with gitleaks,
pluggable deploy targets (Fly, AWS; GCP stub), Claude Code session commands.
