# Trazo

**Trazo is a set of rules you add to a git repository so AI coding agents work like a small team: one agent writes the code, a separate agent reviews it, and you keep the decisions that cannot be undone, such as merging, spending money and changing settings.**

Trazo is for developers who already use Claude Code (in a terminal or in VS Code) or OpenAI Codex on a real repository and want to stay in charge of what it does. It is not an editor extension and not a build service. The rules are a folder named `.trazo/` and a few instruction files that you copy into the repository, and your agent reads them at the start of every session. An optional GitHub workflow merges a pull request only after the required checks have passed. Trazo calls this folder, with its adapter files, the overlay; [what it contains](in-your-repo.md) is on its own page.

It works with any language or framework, because it governs how the agent behaves and not what the code is built with. It asks one thing of your repository: a single command that builds and tests it from a fresh checkout. Docker, nix, a devcontainer or a `Makefile` all satisfy that. Your code, build and deploy setup stay as they are.

## What goes wrong when AI agents work in a real codebase

Each of these happened in the project Trazo was built from. The issue numbers are public, so you can read the original reports.

**The agent that builds the change also declares it done.** In a repository running an early release, the main chat session edited pull request bodies and pushed empty commits to restart CI instead of handing the work to an engineer agent. Asked why, it said it had put speed ahead of the rule and that nothing stopped it ([#319](https://github.com/manoochehri/trazo/issues/319)). A hook that blocks these edits now ships. Whether it behaves on every live input is UNVERIFIED, as the [changelog](changelog.md) says.

**Approval that can be forged or goes stale.** Every agent in this project acts through one GitHub account, so any of them can set the status that says a review passed ([#44](https://github.com/manoochehri/trazo/issues/44) and [#366](https://github.com/manoochehri/trazo/issues/366), both open). On 14 merged pull requests, #316 to #358, the reviewer's own GitHub App wrote only failures, and every success came from the shared account. The opposite failure also occurred: an old failed verdict kept blocking pull request #358 after its evidence had changed ([#359](https://github.com/manoochehri/trazo/issues/359)). A verdict now counts only for the latest commit and the current evidence.

**Guardrails that miss a route, or block the wrong person.** The security review of pull request #329 found that an engineer agent could still merge, set a status and read `.env` through `gh api` and `cat`, routes the deny rules did not cover ([#330](https://github.com/manoochehri/trazo/issues/330)). The guard added in response then blocked the reviewer and security agents from posting their own status, on pull requests #343, #360 and #361 ([#347](https://github.com/manoochehri/trazo/issues/347), [#364](https://github.com/manoochehri/trazo/issues/364)). The changelog calls that guard a speed bump, not a security boundary.

**Decisions made in chat disappear.** A plan or a decision reached in a chat window is gone when the session ends, so the next session repeats it or contradicts it. Trazo keeps plans and decisions as files and issues in the repository, where every new session reads them first ([`rules.md`](https://github.com/manoochehri/trazo/blob/main/src/overlay/rules.md), "The repo is the memory").

## One pull request, start to finish

The pull request is #329, which limited the agents that the main chat session may start to six named ones. The excerpts are real and shortened.

1. The pull request body carries its evidence on lines that CI reads literally:

    ```text
    Review rounds: 0
    Defects found and fixed: none
    Fail-first output:
    New tests/test_agent_role_guard.py run against unchanged origin/main (38 errors, the guard script does not exist there):
    ERROR tests/test_agent_role_guard.py::test_generic_agents_are_blocked[general-purpose]
    ```

2. The security agent read the first commit in its own context and passed it with suggestions. One became #330, the issue above.

3. The reviewer, also in its own context, returned this:

    ```text
    merge after fixes
    Reviewed-Head: 6126ffb5bc46e5ecec3a1517e6996dcf88c4c56c
    Must-fix: src/overlay/hooks/agent_role_guard.py:25 (REASON) ... list only pm, reviewer, security, skeptic, but engineer and senior-engineer are allowed too.
    ```

4. The engineer pushed a second commit with a test that fails on the old message. The reviewer wrote `merge` for `0dd084a`, and security passed it.
5. On `0dd084a` the commit statuses `trazo/verdict` and `trazo/security` were both `success`, and the CI checks (build, test, docker, secrets-scan and the others) were green. The pull request merged on 2026-11-25.

The merge workflow, `owner-merge.yml`, merges with `--match-head-commit`, so a push after the check cannot slip in. When a check is missing it stops with a line of this form (the workflow's own wording, not output from #329):

```text
PR #329: it changes risky paths and trazo/verdict is missing on this head; not merging.
```

## What you get when you add it

- Seven agent job descriptions in `.trazo/roles/`: architect, engineer, senior engineer, project manager, reviewer, security and skeptic. The reviewer, security and skeptic agents run in their own sessions, so none of them grades work it produced.
- Merge rules, enforced by a GitHub workflow. Documentation-only changes need green CI. Changes to sensitive files also need a reviewer pass and a security pass on the latest commit ([ADR 0031](https://github.com/manoochehri/trazo/blob/main/.trazo/project/adr/0031-review-by-path-not-every-pr.md)).
- Numbered decision records. This project has 32, ADR 0001 to 0032, in `.trazo/project/adr/`.
- A charter with a stop rule written before any results exist, and a skeptic that checks every number against a written bar before it is acted on. Each number carries its sample size.
- One rules file, `.trazo/rules.md`, that the Claude Code and Codex adapters both point at.

As of 2026-11-28 the project has 9 tagged releases, the first on 2026-10-08, and 178 merged pull requests since 2026-09-27. Its `tests/` directory holds 65 test files. The share that passes has not been measured for this page, so none is quoted.

## Try it on your repository

Run this in a terminal at the root of a git repository (you need `git`, `curl` and the [GitHub CLI](https://cli.github.com/)):

```sh
curl -fsSL https://raw.githubusercontent.com/manoochehri/trazo/main/scripts/install.sh -o install.sh
bash install.sh install latest
```

Or paste this into your agent: "Install Trazo into this repo. Download `https://raw.githubusercontent.com/manoochehri/trazo/main/scripts/install.sh`, run `bash install.sh install latest`, then delete `install.sh`. Tell me what it placed. Do not set secrets or variables."

Then run `/kickoff` in your agent. It interviews you and writes the charter and first issues. To remove Trazo, run `bash install.sh uninstall`. The [install page](install.md) has the details.

Trazo is free under the MIT license. Your agent provider and GitHub Actions bill you as they always do. The installer only downloads files from the Trazo repository, and nothing from your repository is sent to Trazo.

## Where Trazo stands today

- Trazo is early. The first commit is from 2026-09-27, about two months ago, and it was distilled from one project, this one. The repository records no use by anyone other than its author.
- Every agent acts through one GitHub account, so the review status is only as trustworthy as that account. This is the open issue [#366](https://github.com/manoochehri/trazo/issues/366). It closes when the reviewer's own GitHub App writes the verdicts and the status is pinned to it.
- The unattended drive, `drive.yml`, picks the next ready issue and builds it with nobody watching. It is on in this repository and off by default in yours. Its first live run on 2026-11-28 produced no change and exposed a bug ([#399](https://github.com/manoochehri/trazo/issues/399)). Issue [#247](https://github.com/manoochehri/trazo/issues/247) stays open until a run merges a pull request.
- The hooks that block agent commands are a backstop, not a guarantee. Their known gaps are in the [hooks README](https://github.com/manoochehri/trazo/blob/main/src/overlay/hooks/README.md).
- The charter's goal, that a new VS Code user ships a feature with no manual coding, has not been tried. Token cost has not been measured.

Next: [install it](install.md). After that, [how it works](how-it-works.md) explains the loop from issue to merge, [day to day](day-to-day.md) shows what you type, [in your repo](in-your-repo.md) lists what changes in your files, and [guardrails and limits](guardrails.md) lists what agents may and may not do.
