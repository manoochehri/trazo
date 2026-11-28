# Trazo

**Your GitHub repo and VS Code, run like a well-managed engineering team.**

Trazo turns your GitHub repository and your VS Code experience into a well-managed engineering team. Your coding agents get jobs (engineer, reviewer, security, project manager and more), work through issues and pull requests, and are checked by separate agents. You keep what only a person should decide: money, secrets, settings and releases.

```sh
curl -fsSL https://raw.githubusercontent.com/manoochehri/trazo/main/scripts/install.sh -o install.sh
bash install.sh install latest
```

The [install page](install.md) has the details. Trazo works with Claude Code (which runs in [VS Code](https://code.claude.com/docs/en/vs-code) or a terminal), with Codex, and with any agent that reads `AGENTS.md`. Codex inside VS Code and Antigravity are UNVERIFIED ([#433](https://github.com/manoochehri/trazo/issues/433)). It is not an editor extension and not a build service.

## Why teams add it

**A different agent reviews the work.** The reviewer, security and skeptic agents run in their own sessions, so none of them grades work it wrote. The skeptic checks every number against a written bar, and each number carries its sample size.

**You keep what cannot be undone.** That means money and production, secrets, repository and release settings, force-push or deletion on the default branch, and changes to the rules, workflows and charter themselves. The main chat agent starts a merge workflow once the checks pass, without asking you; risky changes also need a reviewer pass and a security pass.

**Nothing is lost between sessions.** Plans and decisions are files and issues in your repository, not chat history. The next session reads them first ([`rules.md`](https://github.com/manoochehri/trazo/blob/main/src/overlay/rules.md), "The repo is the memory").

## See one pull request go through

This is [#329](https://github.com/manoochehri/trazo/pull/329), which limited the agents the main chat session may start to six named ones.

1. The body carries test evidence on lines that CI reads (shortened):

    ```text
    Review rounds: 0
    Defects found and fixed: none
    Fail-first output:
    New tests/test_agent_role_guard.py run against unchanged origin/main (38 errors, the guard script does not exist there):
    ```

2. The security agent read the first commit in its own session and passed it. One suggestion became a follow-up issue.
3. The reviewer returned `merge after fixes` with `Reviewed-Head: 6126ffb`, because the block message named four of the six allowed agents.
4. The author pushed `0dd084a` with a test that fails on the old message, and the reviewer wrote `merge`.
5. On `0dd084a` the statuses `trazo/verdict` and `trazo/security` were `success` and CI was green. It was merged through the owner account on 2026-11-25, before the merge workflow existed (added later that day in #331).

Today that workflow, `owner-merge.yml`, merges with `--match-head-commit`, so a later push cannot slip in. When a check is missing it stops with `it changes risky paths and trazo/verdict is missing on this head; not merging.` (the workflow's wording, not output from #329).

## What you get

| What | Where it lives | Why |
|---|---|---|
| Seven agent job descriptions | `.trazo/roles/` | Architect, engineer, senior engineer, project manager, reviewer, security and skeptic each have a defined job. |
| Rules in one file | `.trazo/rules.md` | Claude Code and Codex read the same rules. |
| Merge rules | `owner-merge.yml`, a GitHub workflow | Documentation-only changes need green CI and no failing or pending review status. Anything in `src/` or `.trazo/` outside `project/` is risky and also needs reviewer and security passes ([ADR 0031](https://github.com/manoochehri/trazo/blob/main/.trazo/project/adr/0031-review-by-path-not-every-pr.md)). |
| Decision records | `.trazo/project/adr/` | This project has 32, ADR 0001 to 0032. |
| A charter | `.trazo/project/charter/` | Goal, budget and a stop rule, written first. |
| Hooks for Claude Code | `.claude/settings.json` | They block risky commands. See [what changes in your files](in-your-repo.md), where the folder is called the overlay. |

As of 2026-11-28 the project has 9 tagged releases, more than 180 merged pull requests since 2026-09-27, and 65 test files in `tests/`.

## Install with one command

Run the two commands above at the root of a git repository (you need `git`, `curl` and the [GitHub CLI](https://cli.github.com/)), then run `/kickoff` in your agent. Or paste this into your agent: "Install Trazo into this repo. Download `https://raw.githubusercontent.com/manoochehri/trazo/main/scripts/install.sh`, run `bash install.sh install latest`, then delete `install.sh`. Tell me what it placed. Do not set secrets or variables."

## Honest status

- Trazo is early: about two months old, built from one project, this one.
- Every interactive agent acts through one GitHub account, so review status is only as trustworthy as that account ([#366](https://github.com/manoochehri/trazo/issues/366)).
- The unattended drive is on in this repository and off by default in yours. It was triggered on a schedule from 2026-10-31 but only ran for real from 2026-11-23, when it was switched on here, and opened one pull request, #312, which was closed unmerged. A watched run on 2026-11-28 made no change and exposed a bug ([#399](https://github.com/manoochehri/trazo/issues/399)); [#247](https://github.com/manoochehri/trazo/issues/247) tracks that verification.
- The hooks are a backstop, not a guarantee ([known gaps](https://github.com/manoochehri/trazo/blob/main/src/overlay/hooks/README.md)).

## Common questions about Trazo

**How does Trazo work with AGENTS.md?** `AGENTS.md` says how to work in your repository: build, test and conventions. Trazo decides whether an action is allowed, such as spending money, reading a secret or changing settings. The installer adds one marked block and leaves the rest of the file alone; [the rule for a disagreement](in-your-repo.md) is on its own page.

**Which agents does it work with?** Agents that read `AGENTS.md`, Claude Code and Codex, not every tool that runs in VS Code.

| Agent | What you get |
|---|---|
| Claude Code | The rules, role commands such as `/work` and `/pm`, and the hooks |
| Codex | The rules and agent definitions, no hooks; tested once by the author ([details](in-your-repo.md)) |
| Other `AGENTS.md` readers | The rules only; the hooks are Claude Code settings and do not apply |
| Antigravity | UNVERIFIED |

**Do I need VS Code?** No. The installer is a shell script, and Claude Code and Codex run in a terminal.

**What does it cost?** Trazo is free under the MIT license. Your agent provider and GitHub Actions bill you as they always do.

**Does anything leave my repository?** The installer only downloads files from the Trazo repository. Nothing from your repository is sent to Trazo.

**Can I remove it?** Run `bash install.sh uninstall`. It keeps `.trazo/project/`.

Next: [install it](install.md), then see [how it works](how-it-works.md), [use it](use-it.md) and [guardrails and limits](guardrails.md).
