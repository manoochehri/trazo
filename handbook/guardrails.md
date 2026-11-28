# Guardrails and limits

Agents in a Trazo repo work freely on branches. A few actions stay with the owner. This page says
which actions those are, why, how GitHub and the hooks enforce the limits, and where that
enforcement can fail.

In short: agents may change anything a pull request can undo. GitHub holds the limits that a pull
request cannot undo.

## What agents do freely

Agents do reversible repository work without asking:

- Make a branch in their own worktree, commit, push that branch, and open a pull request.
- Edit source, tests and documentation. These files are not on the stop list.
- Run the tests and the repository checks.
- Close and reopen issues, and edit labels. The PM may do this, but it may not remove
  `needs-decision` or `drive-halt` ([`pm_bash_guard.py`](https://github.com/manoochehri/trazo/blob/main/src/overlay/hooks/pm_bash_guard.py)).
- Use ordinary shell constructs. The engineer guard judges the verbs a command runs, not its shape
  ([ADR 0032](https://github.com/manoochehri/trazo/blob/main/.trazo/project/adr/0032-permissive-by-default.md)).

A bad change is undone with a new pull request that reverts it. The rules say that anything not
done through a pull request is never reversible ([`rules.md`](https://github.com/manoochehri/trazo/blob/main/.trazo/rules.md#ask-before-guessing)).

## What stays human-only, and why

The stop list in [`.trazo/rules.md`](https://github.com/manoochehri/trazo/blob/main/.trazo/rules.md#ask-before-guessing)
names what an agent must not decide. The main items:

- **Secrets.** Agents never read, print, log or commit a secret. The owner enters secrets with
  `scripts/put_secret.sh`, which the settings deny to agents.
- **Production and deploys.** Agents have no production access unless the owner asks for it.
  Deploy commands are denied to every role ([hooks README, section 3](https://github.com/manoochehri/trazo/blob/main/src/overlay/hooks/README.md#3-shipped-deny-rules-every-role-including-every-subagent)).
- **Spend.** The unattended drive has caps. By default it runs 4 agent runs and 5 merges per UTC
  day, and each run is capped at $2 ([`drive.yml`](https://github.com/manoochehri/trazo/blob/main/.github/workflows/drive.yml)).
- **Merges.** No agent runs `gh pr merge`. The owner dispatches
  [`owner-merge.yml`](https://github.com/manoochehri/trazo/blob/main/.github/workflows/owner-merge.yml),
  or the front door does it for the owner ([ADR 0029](https://github.com/manoochehri/trazo/blob/main/.trazo/project/adr/0029-the-front-door.md)).
- **Governance and safety paths.** Changes to CODEOWNERS paths, workflows, the charter, agent rules,
  role files, `CLAUDE.md`, `AGENTS.md`, `.claude/`, and `.trazo/` outside `.trazo/project/` need the
  owner's review. So do `ARCHITECTURE_CONTRACT.md` and `SKEPTIC_BAR.md`, the build and CI
  configuration, permissions, dependencies, repository settings, and external systems.
- **Scope.** The PM decides scope, priority, sequencing and acceptance criteria.
- **Tags.** A release is a git tag. A tag is never moved or deleted ([`rules.md`](https://github.com/manoochehri/trazo/blob/main/.trazo/rules.md#releases-are-immutable-tags)).

Why these stay human-only: a pull request cannot take back a leaked secret, a spent budget, a
deploy, a changed ruleset, or a moved tag. The rules keep these with the owner. Changing a limit is also a human-only act: "automation may tighten a limit, never loosen
one" ([`rules.md`](https://github.com/manoochehri/trazo/blob/main/.trazo/rules.md#safety-limits-are-human-only)).

## How it is enforced

The rules say to put each gate at the strongest layer that can enforce it. There are four layers,
strongest first.

1. **GitHub rulesets.** The saved copy is
   [`scripts/rulesets/main-ruleset.saved.json`](https://github.com/manoochehri/trazo/blob/main/scripts/rulesets/main-ruleset.saved.json).
   - `protect main` covers the default branch. It blocks deletion and non-fast-forward pushes and
     requires a pull request. It requires four checks: `secrets-scan`, `docker`, `test` and
     `docs-updated`. It has no bypass actors. It requires zero approving reviews and does not
     require code owner review.
   - The tag ruleset `v` blocks deletion, force-move and update of tags, with no bypass.
   - The tag ruleset `v-create` controls who may create tags. Its bypass is the repository Admin
     role ([`protect_release_tags.py`](https://github.com/manoochehri/trazo/blob/main/scripts/protect_release_tags.py)).
2. **CODEOWNERS.** [`.github/CODEOWNERS`](https://github.com/manoochehri/trazo/blob/main/.github/CODEOWNERS)
   names the paths that need the owner's review. The ruleset does not enforce it, because
   `require_code_owner_review` is false. The owner-merge gate and the classifier use the same list
   instead ([`report_verdict.py`](https://github.com/manoochehri/trazo/blob/main/scripts/report_verdict.py)).
3. **The owner-merge gate.** [`owner-merge.yml`](https://github.com/manoochehri/trazo/blob/main/.github/workflows/owner-merge.yml)
   runs only when the owner dispatches it from the default branch. It refuses unless the pull
   request is open, not a draft, not from a fork, and targets the default branch, and every check is
   green on the head commit. A pull request that changes a risky path also needs `trazo/verdict`
   and `trazo/security` to be `success` on that head ([ADR 0031](https://github.com/manoochehri/trazo/blob/main/.trazo/project/adr/0031-review-by-path-not-every-pr.md)).
   It merges with `--match-head-commit`, so a push after the check cannot slip in.
   A scheduled job, [`merge-audit.yml`](https://github.com/manoochehri/trazo/blob/main/.github/workflows/merge-audit.yml),
   re-applies the same gate to recent merges and opens an issue for any that failed it. It detects
   only and reverts nothing.
4. **Four hooks.** They run before tool calls in the session they are registered in. Each one
   binds a different set of tools.
   Their source is in [`src/overlay/hooks/`](https://github.com/manoochehri/trazo/blob/main/src/overlay/hooks/).
   - `agent_role_guard.py` lets the Agent tool start only the pinned roles.
   - `front_door_guard.py` stops the main session from editing files outside `.trazo/project/` and
     from writing pull request bodies or empty commits ([ADR 0029](https://github.com/manoochehri/trazo/blob/main/.trazo/project/adr/0029-the-front-door.md)).
   - `pm_bash_guard.py` is an allowlist of exact command shapes for the PM.
   - `engineer_bash_guard.py` is a blocklist for the main session and the engineer subagents. It
     denies merges, status writes to other roles, secrets and protected paths.

   The hooks fail closed: unreadable input or a missing script blocks the call. They are speed bumps,
   not boundaries (see the next section).

The unattended drive adds its own limits: a kill switch (`DRIVE_ENABLED`), a `drive-halt` label that
stops work, one open drive pull request at a time, and the daily caps above. A halt clears itself
once after a fix merges and CI is green ([ADR 0030](https://github.com/manoochehri/trazo/blob/main/.trazo/project/adr/0030-drive-halt-clears-itself-once.md)).
That is a loosening of a limit, so the owner reviews it.

## Where each layer can fail

**Rulesets.**
- The live `protect main` ruleset, read with `gh api` on 2026-11-28, lists four required checks.
  It does not list `trazo/verdict`, but the saved copy does. The two differ. Which one is intended is
  UNVERIFIED. Drift is tracked in [#282](https://github.com/manoochehri/trazo/issues/282).
- CODEOWNERS is not enforced by the ruleset (see above).
- The reviewer's commit status is not pinned to a GitHub App. [#366](https://github.com/manoochehri/trazo/issues/366) tracks this.

**Owner-merge gate.**
- The reviewer and security statuses are set by the same account that dispatches the run. The gate
  cannot tell the two apart ([#366](https://github.com/manoochehri/trazo/issues/366)).
- The gate's token may or may not squash-merge a pull request that edits `.github/workflows/`.
  GitHub restricts that write. UNVERIFIED on a live run. If the merge is refused, the owner merges
  that one pull request by hand.

**Hooks.** The hook README lists what still gets through ([hooks README, "What still gets through"](https://github.com/manoochehri/trazo/blob/main/src/overlay/hooks/README.md#what-still-gets-through)):

- Any HTTP client that holds `GH_TOKEN`, such as `curl`. It needs no `gh` call and no `.env` word.
- A refspec or endpoint built from a shell variable. The ruleset rejects a push to the default branch,
  but a variable-built endpoint is not judged.
- The working directory is not tracked. `cd .claude && echo x > y` writes into `.claude/`.
- Interpreters and scripts: `python -c`, `node -e`, and a script the agent writes and then runs.
- Shell variables, globs, `eval $(...)`, aliases and functions.
- `gh api -X DELETE` on an object outside the blocklist passes.
- The Read, Edit and Write tools are not bound by the Bash hooks.
- Symlinks inside the repository that point outside it are not resolved. UNVERIFIED.

**Drive.** The first live run did not produce a change. The stuck job could not label the issue
`needs-pm` because it ran `git` outside a repository ([#399](https://github.com/manoochehri/trazo/issues/399)).

## Shipped and UNVERIFIED

Each row names its source. A row marked UNVERIFIED has not been run live.

| Item | Status | Source |
|---|---|---|
| Owner-merge gate logic | Shipped on `main`. Covered by its test file; not a live run. | [`owner-merge.yml`](https://github.com/manoochehri/trazo/blob/main/.github/workflows/owner-merge.yml), [`test_owner_merge_workflow.py`](https://github.com/manoochehri/trazo/blob/main/tests/test_owner_merge_workflow.py) |
| Drive, end to end | UNVERIFIED. The first live run on 2026-11-28 did not produce a change. The open defect is [#399](https://github.com/manoochehri/trazo/issues/399), and its fix is in progress. No full unattended run has merged. | [`drive.yml`](https://github.com/manoochehri/trazo/blob/main/.github/workflows/drive.yml), [#247](https://github.com/manoochehri/trazo/issues/247) |
| `release.yml` | UNVERIFIED. Never run live. | [`release.yml`](https://github.com/manoochehri/trazo/blob/main/.github/workflows/release.yml) |
| `merge-audit.yml` | UNVERIFIED. Never run live. | [`merge-audit.yml`](https://github.com/manoochehri/trazo/blob/main/.github/workflows/merge-audit.yml) |
| Release App bypass on `v-create` | UNVERIFIED. The live `v-create` ruleset, read on 2026-11-28, has one bypass actor (the Admin role) and no App entry. The App bypass shape is not confirmed. | [`allow_release_app.py`](https://github.com/manoochehri/trazo/blob/main/scripts/allow_release_app.py) |
| Front-door hook payload shape: the main session has neither `agent_id` nor `agent_type` | UNVERIFIED live. Taken from the hooks documentation, not a recorded payload. | [hooks README, front door section](https://github.com/manoochehri/trazo/blob/main/src/overlay/hooks/README.md) |
| Agent-role hook input shape (`subagent_type`) | UNVERIFIED live. | [hooks README, agent role section](https://github.com/manoochehri/trazo/blob/main/src/overlay/hooks/README.md) |
| Reviewer App pin on `trazo/verdict` | Not shipped. | [#366](https://github.com/manoochehri/trazo/issues/366) |
| Live `protect main` requires `trazo/verdict` | UNVERIFIED which is intended. Live and saved copies differ. | [`main-ruleset.saved.json`](https://github.com/manoochehri/trazo/blob/main/scripts/rulesets/main-ruleset.saved.json), [#282](https://github.com/manoochehri/trazo/issues/282) |

## Decisions

- [ADR 0029](https://github.com/manoochehri/trazo/blob/main/.trazo/project/adr/0029-the-front-door.md): the front door is the main session, and it acts.
- [ADR 0030](https://github.com/manoochehri/trazo/blob/main/.trazo/project/adr/0030-drive-halt-clears-itself-once.md): a drive halt clears itself once.
- [ADR 0031](https://github.com/manoochehri/trazo/blob/main/.trazo/project/adr/0031-review-by-path-not-every-pr.md): review by path, not every pull request.
- [ADR 0032](https://github.com/manoochehri/trazo/blob/main/.trazo/project/adr/0032-permissive-by-default.md): agents are permissive by default; GitHub holds the irreversible limits.

The status lines of these four ADR files still read "proposed" on `main`, although `rules.md` already applies the rules they describe. This page does not change their status. Other pages cite these ADRs the same way.

## Why these rules exist

Each rule above answers something that went wrong in this project.

- **An agent did the wrong role's job.** In a host repository, the main chat session edited pull requests and pushed empty commits itself, and said nothing stopped it ([#319](https://github.com/manoochehri/trazo/issues/319)). A hook that blocks those edits now ships; its behavior on every live input is UNVERIFIED.
- **One account could set the approval.** Every interactive agent acts through one GitHub account, so any of them can set the status that says a review passed. Of the 22 merged pull requests #316 to #358, the reviewer's own GitHub App wrote a status on 14, and every one was a failure (a placeholder asking a person to set the status). Every success on all 22 came from the shared account ([#366](https://github.com/manoochehri/trazo/issues/366), [#44](https://github.com/manoochehri/trazo/issues/44), both open).
- **Guards missed a route, then blocked the wrong agent.** An engineer agent could still merge and read `.env` through `gh api` and `cat` ([#330](https://github.com/manoochehri/trazo/issues/330)). The guard added for that then blocked the reviewer and security agents from posting their own status ([#347](https://github.com/manoochehri/trazo/issues/347), [#364](https://github.com/manoochehri/trazo/issues/364)).

## Related pages

- [How it works](how-it-works.md): the loop, the roles, the merge gate and the drive workflow these limits apply to.
- [Use it](use-it.md): what to do when a limit stops you.
- [Install and upgrade](install.md): the owner-only setup that creates the GitHub-side limits.
