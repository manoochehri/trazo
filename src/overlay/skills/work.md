Implement issue $ARGUMENTS.

1. Read the issue (`gh issue view`), AGENTS.md and `.trazo/rules.md`, and any docs it links.
2. Explain your plan in a few lines and list anything unclear. Then wait for my OK — unless the run is unattended, which means it was started by an agent mention on an issue or by a schedule. In that case post the plan to the issue with `gh issue comment` and carry on. Nothing else counts as unattended; if I'm slow to reply, you are still waiting for me.
3. Do not stack work on an unmerged pull request. If this issue depends on an open PR, wait for that PR to merge, then start from fresh `origin/<default-branch>`. Find the repository's default branch with `gh repo view --json defaultBranchRef --jq .defaultBranchRef.name`, fetch it, and create a dedicated worktree from `origin/<default-branch>`:
   `git worktree add .worktrees/issue-<number>-<short-name> -b issue-<number>-<short-name> origin/<default-branch>`
   Work inside that worktree directory. Each worktree has its own environment (run `make setup`). Make the first commit of the change (it doesn't need to be complete).
4. Push and open a pull request against the repository's default branch that closes the issue, right after that first commit — so there's something for the reviewer/security subagents to comment on. Give me the link. Then verify the base: compare `gh pr view <number> --json baseRefName --jq .baseRefName` with the default branch from `gh repo view`. If it differs, change it with `gh pr edit <number> --base <default-branch>` and verify again before continuing; if the correction fails, stop.
   **The first line of the first commit's message must read `Closes #<n>: <subject>` — a standalone line, never a mention inside a sentence.** A PR-body keyword alone does not close anything when the PR is squash-merged (the default for `main` here, and every PR since #26): this repo squashes with the first commit's subject and the accumulated commit messages (measured: `squash_merge_commit_title=COMMIT_OR_PR_TITLE`, `squash_merge_commit_message=COMMIT_MESSAGES`), so the PR body never reaches the landing commit. Both are needed — the PR body so a reader sees the intent, the commit subject so the merge actually closes it. Mirror the same `Closes #<n>:` prefix in the PR title too: the squash subject is editable at merge time, and a keyword-free subject is how five issues survived their own merges (#68).
   Verify with a real grep of the first line, not by reading the message: `git log -1 --format=%B | head -5 | grep -iE '^(close[sd]?|fix(e[sd])?|resolve[sd]?) #[0-9]+'` must exit 0. `head` is the rule: a keyword that appears only later, or inside prose, is discussion of the directive, not the directive — #65's commit message *mentioned* `Closes #N` in a sentence about the bug and closed nothing (#68).
5. For a bug fix or behavior change, write the regression test first and run it against unchanged code; put the failing output in the PR. For external behavior, list each assumption and its source in the plan, or mark it `UNVERIFIED`; an unverified behavior the code depends on blocks the change. Finish with tests, running `make test` and `make lint` as you go and fixing failures. Update docs the PR template asks for (do not update VERSION/CHANGELOG in feature PRs; those are managed separately on release to avoid branch collision). Push additional commits to the same branch/PR.
6. Ask the **reviewer** subagent to review the PR; verify that the PR base branch is `main`. The subagent posts its verdict directly on the PR as a `gh pr review --comment` with the verdict word as the first line of the body (not just a chat summary) — not `--approve` / `--request-changes`, which GitHub refuses while the agent and the PR author are the same account, i.e. every PR here (#44); switch back when #44 gives agent work its own identity. Fix must-fix items and push. If the change touches secrets, permissions, workflows, dependencies, or infra, also ask the **security** subagent — it posts findings tied to this PR the same way via `gh pr review --comment`; a security finding unrelated to this PR becomes its own GitHub issue instead. If the change makes or relies on a **quantitative, experimental, or empirical claim** — a measured number, a benchmark, a cost or performance figure, an A/B or backtest result — also ask the **skeptic** subagent before the claim ships: it checks the result against `.trazo/project/SKEPTIC_BAR.md` and returns *holds* / *holds with caveats* / *does not hold*, and a `does not hold` is a must-fix item. A claim that is merely *believed* is not evidence, and code that encodes a number nobody checked encodes the bug too.
7. Report the PR link and verdict first, then the test result, number of review rounds, and defects found and fixed. Keep the owner summary decision-first, short, and to at most one command; link the PR for detail.

## When a decision arrives

Whichever way it arrives — the `pm` subagent's answer, the owner answering in chat, or `/decide` — put it on the issue with `gh issue comment` *before* you build on it: the decision, who made it, and what it unblocks. Then work from the issue, not from this transcript. The chat line afterwards is a pointer with the issue link, never the record. A decision that exists only in this conversation dies with the session, and the next one re-asks it.


## When you hit something that blocks progress

The test for "blocked" is whether **progress stops**, not whether you have a question. Choices you can make yourself — library, naming, file layout, test structure — you make yourself, and you note them in the pull request.

When progress does stop:

1. **Post the question to the issue** with `gh issue comment`. Include what you tried, what you verified, the options you see, and which one you would pick. Do not put it only in chat.
2. **Label it:** `gh issue edit <n> --add-label needs-pm`.
3. **Call the `pm` subagent** for an assist, pointing it at the issue number.
4. **If it answers,** comment the answer onto the issue with `gh issue comment` first (see *When a decision arrives*), then continue from it, and remove `needs-pm` if it is still on the issue (`gh issue edit <n> --remove-label needs-pm`).
5. **If it judges the call to be the owner's,** it applies `needs-decision`, removes `needs-pm`, and assigns the owner (the handle is in `.github/CODEOWNERS`). You stop there — no further work on this issue. Say so in chat in one line, with the issue link.
6. **If it comes back with neither** an answer nor an escalation, treat the blocker as still open: leave `needs-pm` on, say so in chat in one line with the issue link, and stop. Do not fill the gap by deciding it yourself.

You never classify whether something is the owner's call yourself: you apply `needs-pm` and let the PM decide. While the PM is looking, keep building anything that doesn't depend on the answer. Once it escalates to `needs-decision`, that issue is stopped until the owner clears it.

## Merge gate
`trazo/verdict` (set by the reviewer subagent; `trazo/security` by the security subagent) is the commit status that makes a PR mergeable once the owner marks it a required check. It is per head SHA, so every push resets it: after pushing fixes, re-request review so the reviewer sets it again on the new head. The engineer never sets these contexts; do not run `gh api .../statuses` for `trazo/verdict` or `trazo/security` yourself.

Use one working session per task. Do not poll another session or its transcript; put
progress in the issue and PR, then start a fresh session for the next task.
