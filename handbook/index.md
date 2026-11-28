# Trazo

**AI agents write the code. A second agent reviews it. You decide what merges.**

Trazo is a set of rules you add to a git repository so AI coding agents work like a small team: one agent writes the code, a separate agent reviews it, and you keep the decisions that cannot be undone. It is not an editor extension and not a build service.

```sh
curl -fsSL https://raw.githubusercontent.com/manoochehri/trazo/main/scripts/install.sh -o install.sh
bash install.sh install latest
```

The [install page](install.md) has the details. Works with Claude Code, Codex and any agent that reads `AGENTS.md`, in VS Code or a terminal, with your GitHub repository. Antigravity is UNVERIFIED ([#433](https://github.com/manoochehri/trazo/issues/433)).

## Why teams add it

**A different agent reviews the work.** The reviewer, security and skeptic agents run in their own sessions, so none of them grades work it wrote. The skeptic checks every number against a written bar, and each number carries its sample size.

**You decide what cannot be undone.** Merging, spending money, secrets, settings and releases stay with you. Agents handle everything a pull request can undo, and a stop rule written before any results exist says when to quit.

**Nothing is lost between sessions.** Plans and decisions are files and issues in your repository, not chat history. The next session reads them first ([`rules.md`](https://github.com/manoochehri/trazo/blob/main/src/overlay/rules.md), "The repo is the memory").

## See one pull request go through

This is [#329](https://github.com/manoochehri/trazo/pull/329), which limited the agents the main chat session may start to six named ones.

1. The body carries test evidence on lines that CI reads literally:

    ```text
    Review rounds: 0
    Fail-first output: 38 errors, the guard script does not exist on main
    ```

2. The security agent read the first commit in its own session and passed it. One suggestion became a follow-up issue.
3. The reviewer returned `merge after fixes` with `Reviewed-Head: 6126ffb`, because the block message named four of the six allowed agents.
4. The engineer pushed `0dd084a` with a test that fails on the old message, and the reviewer wrote `merge`.
5. On `0dd084a` the statuses `trazo/verdict` and `trazo/security` were `success`, CI was green, and it merged on 2026-11-25.

The merge workflow merges with `--match-head-commit`, so a later push cannot slip in. When a check is missing it stops with `it changes risky paths and trazo/verdict is missing on this head; not merging.` (the workflow's wording, not output from #329).

## What you get

| What | Where it lives | Why |
|---|---|---|
| Seven agent job descriptions | `.trazo/roles/` | Architect, engineer, senior engineer, project manager, reviewer, security and skeptic each have a defined job. |
| Rules in one file | `.trazo/rules.md` | Claude Code and Codex read the same rules. |
| Merge rules | `owner-merge.yml`, a GitHub workflow | Documentation changes need green CI; sensitive files also need reviewer and security passes ([ADR 0031](https://github.com/manoochehri/trazo/blob/main/.trazo/project/adr/0031-review-by-path-not-every-pr.md)). |
| Decision records | `.trazo/project/adr/` | This project has 32, ADR 0001 to 0032. |
| A charter | `.trazo/project/charter/` | Goal, budget and stop rule, written first. |
| Hooks for Claude Code | `.claude/settings.json` | They block risky commands. See [what changes in your files](in-your-repo.md), where the folder is called the overlay. |

As of 2026-11-28 the project has 9 tagged releases, 178 merged pull requests since 2026-09-27, and 65 test files in `tests/`.

## Install with one command

Run the two commands above at the root of a git repository (you need `git`, `curl` and the [GitHub CLI](https://cli.github.com/)), then run `/kickoff` in your agent. Or paste this into your agent: "Install Trazo into this repo. Download `https://raw.githubusercontent.com/manoochehri/trazo/main/scripts/install.sh`, run `bash install.sh install latest`, then delete `install.sh`. Tell me what it placed. Do not set secrets or variables."

## Honest status

- Trazo is early: about two months old, built from one project, this one.
- Every agent acts through one GitHub account, so review status is only as trustworthy as that account ([#366](https://github.com/manoochehri/trazo/issues/366)).
- The unattended drive is on in this repository and off by default in yours. Its first live run on 2026-11-28 made no change ([#399](https://github.com/manoochehri/trazo/issues/399), [#247](https://github.com/manoochehri/trazo/issues/247)).
- The hooks are a backstop, not a guarantee ([known gaps](https://github.com/manoochehri/trazo/blob/main/src/overlay/hooks/README.md)).

## Common questions about Trazo

**How does Trazo work with AGENTS.md?** `AGENTS.md` says how to work in your repository: build, test and conventions. Trazo decides whether an action is allowed, such as merging, spending money or reading a secret. The installer adds one marked block and leaves the rest of the file alone; [the rule for a disagreement](in-your-repo.md) is on its own page.

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

Next: [install it](install.md), then see [how it works](how-it-works.md), [day to day](day-to-day.md) and [guardrails and limits](guardrails.md).
