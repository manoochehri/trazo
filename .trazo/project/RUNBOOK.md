# Runbook

**Status:** current

## Local
```
make setup     # deps + git hooks (gitleaks, ruff)
make test      # pytest
make lint      # ruff
make docs-check # validate project-doc status, links, issues and freshness
make scan      # scan git history for secrets
make docs      # preview the handbook locally
make release   # validate and cut an annotated version tag
```

`make scan` scans the full git history in a container. It works from inside a
`.worktrees/*` worktree (it mounts the shared git dir), and it refuses to report
success when it cannot verify the history: it exits non-zero with the reason instead
of printing "no leaks found" after scanning 0 commits.

## Parallel work (git worktrees)
To run multiple engineer sessions concurrently without branch or directory collision:
```bash
# 1. Create a dedicated worktree off fresh origin/main
git fetch origin
git worktree add .worktrees/issue-<N>-<name> -b issue-<N>-<name> origin/main

# 2. Work inside the worktree
cd .worktrees/issue-<N>-<name>
make setup     # fast due to uv's shared cache

# 3. List active worktrees
git worktree list

# 4. Remove after PR merge and clean up local branch
cd ../..
git worktree remove .worktrees/issue-<N>-<name>
git branch -d issue-<N>-<name>

# 5. Prune stale worktree references
git worktree prune
```
Note: Claude Code can also be launched directly inside an isolated worktree via `claude --worktree <name>` (which creates `.claude/worktrees/<name>`). Both `.worktrees/` and `.claude/worktrees/` are ignored in `.gitignore`, and secret protections in `.claude/settings.json` cover both recursively.

## Merge gate: verdict status (owner step, #115)
The reviewer subagent sets commit status `trazo/verdict` on the PR head SHA (`pending` at start, `success` for merge, `failure` for merge after fixes or worse); the security subagent sets `trazo/security` the same way. A new push resets both, so a fix needs a fresh review.

Owner step, once: GitHub repo Settings -> Rules -> Rulesets -> the `protect main` ruleset -> Require status checks to pass -> Add checks -> add `trazo/verdict` (optionally `trazo/security` too). Until the check has reported once it may not appear in the picker; type the name in.

Caveat (#44): agents post as the owner's account, so an agent could set `success` itself. The rule says only the reviewer or security subagent sets it, and the audit trail is the PR review comment that accompanies each status. This is not enforced until #44 gives agent work its own identity.

## Separate GitHub App identity for agent work (#44)

The owner chose a GitHub App for agent identity. Install it only on `manoochehri/trazo` and grant the minimum repository permissions needed for the operations in #115:

| Permission | Access | Used for |
|---|---|---|
| Metadata | Read (required) | Repository metadata |
| Contents | Read and write | Read source, push agent branches, and merge PRs if #115 phase two is approved |
| Issues | Read and write | Read issues; post comments and update labels |
| Pull requests | Read and write | Create and update PRs; post reviews/comments; enable auto-merge if #115 phase two is approved |
| Commit statuses | Read and write | Set `trazo/verdict` and `trazo/security` on a commit |

Do not grant Actions, administration, secrets, deployments, Checks, or organization-wide access for this design. Leave webhook URL and event subscriptions unset until a cloud consumer is approved. The current verdict mechanism uses commit statuses; a future switch to Checks requires a separate design and permission review. GitHub documents the endpoint permissions in [its permissions table](https://docs.github.com/en/rest/authentication/permissions-required-for-github-apps), including [creating refs](https://docs.github.com/en/rest/git/refs#create-a-reference), [creating pull requests](https://docs.github.com/en/rest/pulls/pulls#create-a-pull-request), [submitting reviews](https://docs.github.com/en/rest/pulls/reviews#create-a-review-for-a-pull-request), [merging pull requests](https://docs.github.com/en/rest/pulls/pulls#merge-a-pull-request), and [creating commit statuses](https://docs.github.com/en/rest/commits/statuses#create-a-commit-status).

**Credential timing:** create and install the App with repository access restricted to this repository, but wait to generate/store its private key until a reviewed token consumer is ready and has documented the exact secret name and rotation/revocation steps. The private key does not expire; GitHub recommends storing it securely and not sharing it broadly ([GitHub App security guidance](https://docs.github.com/en/apps/creating-github-apps/about-creating-github-apps/best-practices-for-creating-a-github-app)). At that point, the owner generates the key and enters it directly into the approved secret store. Agents must never read, receive, or handle the key.

Installation tokens require a JWT signed with the private key, are limited by the App's permissions and repository access, and expire after one hour ([installation token guide](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app)). The consumer must mint short-lived tokens and use the App identity for GitHub operations.

**Current limit:** local sessions still use the owner's `gh` authentication. Do not copy the App private key into a local `.env` file or onto agent-readable disk. GitHub advises native/client apps running on a user's device not to use the App private key. A local-session identity therefore needs a separately reviewed token-broker design. Cloud execution is also not ready: #117 is research-only and forbids production workflow changes until its evidence-backed plan is accepted. Keep #44 open until a supported consumer is implemented and an agent-authored action is verified as the distinct App identity.

## Secrets
- Local: copy `.env.example` to `.env` and fill in. `.env` is git-ignored and blocked from Claude Code.
- AWS: `scripts/put_secret.sh <secret-name>` (you run it; it prompts without echoing).

## Deploy
This repository has no deploy target. The handbook is published by its GitHub Pages workflow.

## Roll back
TODO

## Recurring
- Daily advisor review: TODO (scheduled task / GitHub Action)
- Weekly: dependency PRs from Dependabot

## Teardown
TODO
