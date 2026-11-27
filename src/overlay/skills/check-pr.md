Review pull request $ARGUMENTS (if none given, list open PRs and ask which).

First read the diff. If it changes only documentation or `.trazo/project/` state, check it against the diff and CI yourself with no subagent (ADR 0031), and say so on the PR. If it changes a risky path (hooks, workflows, settings or permissions, dependencies, rulesets, secrets, `CODEOWNERS`, rules, role or agent-instruction files), use the **reviewer** subagent and also the **security** subagent. Each posts its verdict on the PR as a real `gh pr review --comment` — that's not optional — with the verdict word as the first line of the body. Not `--approve` / `--request-changes`: GitHub refuses both while the agent and the PR author are the same account, i.e. every PR here (#44). Summarize both in under 15 lines: verdict, must-fix items, and whether CI is green. Ask whether to merge (only if verdict is merge/approve and CI is green).

A PR whose base differs from the repository's default branch is not mergeable; the reviewer must mark it **merge after fixes** until it is retargeted.

The `trazo/verdict` commit status the reviewer sets (or the automatic review's report job, from a bot `merge` on this head, ADR 0020) is what makes a PR mergeable (`trazo/security` likewise for the security subagent). A new push resets it, so after fixes re-run this review on the new head. Never set those contexts yourself.
