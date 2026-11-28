# Automation

**What do the GitHub workflows add, and why do they need GitHub Apps?** Everything on this page is optional. Trazo works without it: you ask your agent for work, `/check-pr` reviews it, and you start the merge yourself. The workflows add automatic review, a merge that checks its own conditions and an unattended builder, and they need the one-time [owner setup](install.md#owner-setup) first.

## The workflows

| Workflow | What it does | Switch |
|---|---|---|
| `ci.yml` | Runs the secret scan, the tests, a docker build and the documentation check on every pull request and on the default branch. | Always on. |
| `review.yml` and `report.yml` | Review a pull request automatically. `review.yml` runs the reviewer agent and holds no key. `report.yml` then sets the `trazo/verdict` status. | Variable `AUTO_REVIEW_ENABLED` is `true`. |
| `owner-merge.yml` | Merges one pull request when its checks pass, and refuses with a reason otherwise. It runs only when someone starts it. | None. It is started by hand or by the main chat agent. |
| `drive.yml` | The drive: every 30 minutes it picks the top ready issue, an agent edits a copy of the code, a script opens the pull request, and a merge job can merge it. | Variable `DRIVE_ENABLED` is `true`. |

Three more workflows belong to Trazo's own repository and are not for yours: `docs.yml` publishes this site, `release.yml` cuts release tags, and `merge-audit.yml` checks recent merges after the fact. The sources are in [`.github/workflows/`](https://github.com/manoochehri/trazo/tree/main/.github/workflows).

**The drive is unproven.** It is on in this repository and off by default in yours. It was triggered on a schedule from 2026-10-31 but only ran for real from 2026-11-23, when it was switched on here. It opened one pull request, #312, which was closed unmerged. A watched run on 2026-11-28 made no change and exposed a bug ([#399](https://github.com/manoochehri/trazo/issues/399)), and [#247](https://github.com/manoochehri/trazo/issues/247) stays open until a run merges a pull request. Leave it off until you can watch a run.

## Why GitHub Apps

A workflow normally acts with its built-in token, `GITHUB_TOKEN`. GitHub does not let that token start more workflows, to prevent loops. Per [GitHub's documentation](https://docs.github.com/en/actions/concepts/security/github_token), events caused by it create no new workflow run, with two exceptions: dispatch events, and pull request events, which start runs that wait for a person to approve them.

That breaks automation in three ways:

- A pull request that the drive opens with the built-in token would get no CI and no review until someone approved the runs.
- A push or a merge made with the built-in token starts no push workflow. The docs site did not redeploy after merges for this reason ([#419](https://github.com/manoochehri/trazo/issues/419)). `owner-merge.yml` now starts `docs.yml` by dispatch, which is UNVERIFIED on a live run.
- A status written with the built-in token is not tied to a separate reviewer identity.

A GitHub App is a separate identity with its own key, and its events do start workflows. Trazo uses two:

| App | What it does |
|---|---|
| `trazo-builder` | Lets the drive push a branch and open its pull request, so CI and review run on it. It also lets the drive clear its own halt after a fix, and lets `release.yml` push a tag (UNVERIFIED on a live run). |
| `trazo-reviewer` | Lets `report.yml` set the `trazo/verdict` status as the reviewer, not as the repository owner. |

Both keys are secrets of a GitHub environment named `trazo-apps`, which only the `main` branch may read. Pull request code never holds a key. The setup script, and why it asks you to click twice in your browser, are in [owner setup](install.md#2-the-two-github-apps).

## What is not solved yet

Agents you run in your own sessions still act through your GitHub account, so the review status is only as trustworthy as that account. The reviewer App has written only failures so far, which is the open issue [#366](https://github.com/manoochehri/trazo/issues/366). The details are on [guardrails and limits](guardrails.md).

Next: switch on only what you need, in the order the [owner setup](install.md#owner-setup) gives: the key, the Apps, then automatic review.
