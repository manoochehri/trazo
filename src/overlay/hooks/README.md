# PM limits: enforced by the harness, not by prompt (issue #279)

The `pm` subagent cannot deploy, merge, push, dispatch a workflow or change a secret. Two
mechanical layers hold that, and the prompts only explain it.

## 1. The PM's Bash allowlist (`pm_bash_guard.py`)

`.claude/agents/pm.md` declares a `PreToolUse` hook on `Bash` in its own frontmatter. Claude Code
runs frontmatter hooks only while that subagent is running. The hook is an allowlist: it permits

- read-only `git` (`status`, `log`, `diff`, `show`, `fetch`, list-only `branch` and `tag`, ...);
- read-only `gh` (`issue|pr|run|release|label|workflow` view and list, `search`, `api` without
  method, field or input flags);
- `gh issue create`, `gh issue comment`, `gh issue edit` with a fixed flag set;
- `head tail wc cut grep jq tr` after a pipe.

It blocks everything else, every unquoted `;` `&` `||` redirection or substitution, and any word
that names `.env`, `secrets/`, `*.pem` or `*.key`. It exits 2 with the reason on stderr; any
error in the hook also blocks. The declared command ends in `|| exit 2`, so a missing script or
missing `python3` blocks too.

The allowlist is not host-extendable: a PM that needs more should file an issue for the engineer.

## 2. Shipped deny rules (every role, including subagents the PM spawns)

`settings.json` ships these `permissions.deny` rules. Claude Code applies deny rules to the main
conversation and to subagents, and they win over any hook's `allow`.

| Rule | Why |
|---|---|
| `Bash(gh pr merge *)` | Merging belongs to the gated CI path (`drive.yml`), not a session |
| `Bash(fly *)`, `Bash(flyctl *)` | Production hosting |
| `Bash(clasp push *)`, `Bash(clasp deploy *)` | Apps Script deploys |
| `Bash(scripts/deploy*)`, `Bash(./scripts/deploy*)` | A host's deploy scripts |
| `Bash(scripts/put_secret.sh *)` | Secrets are entered by the human |
| `Bash(gh secret *)`, `Bash(gh variable set *)` | Repository secrets and variables |
| `Bash(gh workflow run *)` | Workflow dispatch can deploy |

A deny rule matches the command text as written. It is not a security boundary: `git -C . push`,
`bash scripts/deploy.sh` or a wrapper such as `env` can slip past a prefix rule (Claude Code
permissions docs, "What Bash rules don't match"). That is why the PM's Bash goes through the
allowlist above and why deploy credentials should live only in CI.

## Extending the list for a host

Deploy commands are host-specific. Add your own rules to the host's `.claude/settings.json`
under `permissions.deny`, for example `Bash(./bin/ship *)` or `Bash(terraform apply *)`. The
installer writes `settings.json` only when absent and never overwrites an existing one, so your
additions survive an upgrade; add any rule this release ships that your file lacks.

## Not covered

Subagents the PM spawns (ADR 0019) do not carry the PM's frontmatter hook; they inherit only the
deny rules in section 2. Whether a frontmatter hook also fires for a nested subagent is
UNVERIFIED.
