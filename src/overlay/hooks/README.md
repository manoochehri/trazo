# PM limits: enforced by the harness, not by prompt (issue #279)

The `pm` agent cannot deploy, merge, push, dispatch a workflow, change a secret, start another
agent, or lift the `needs-decision` and `drive-halt` labels. Three mechanical layers hold that,
and the prompts only explain it.

## 1. The PM has no `Agent` tool (ADR 0025)

A subagent the PM started would not carry the PM's Bash allowlist, so the tool is removed from
`tools:` in `agents/pm.md`. The front door (the main session) dispatches work the PM records on
an issue. A test fails if `Agent` returns.

## 2. The PM's Bash allowlist (`pm_bash_guard.py`)

An allowlist of exact argument shapes, registered twice so a skipped layer does not fail open:

- in `agents/pm.md` frontmatter (runs only while the PM runs, and only in a trusted workspace:
  Claude Code skips project subagent frontmatter hooks in `-p` sessions and when only a parent
  folder is trusted);
- in `settings.json` as a `PreToolUse` hook on `Bash` run with `--agent pm`: it enforces only
  when the hook input's `agent_type` is `pm`, and it runs in `-p` sessions too.

It permits read-only `git` and `gh` with known flags, `gh api repos/<owner>/<repo>/...` with
`--jq`/`--paginate` only, `gh issue create|comment|edit` with a fixed flag set (`--body`, not
`--body-file`), and stdin-only filters after a pipe (`head tail wc cut tr grep jq`, no file
operands). It blocks everything else: `gh auth`, any glob, `;` `&` `||` redirection, substitution,
absolute, `~` or `..` paths for git, `git diff --no-index` (and its abbreviations), and any word
naming `.env`, `secrets/`, `*.pem`, `*.key` or similar. `gh issue edit --remove-label` may not
name `needs-decision` or `drive-halt`. Exit 2 blocks and the reason is on stderr; any error also
blocks, and the declared command ends `|| exit 2`, so a missing script or missing `python3`
blocks too. For the settings hook that means every Bash call in a host fails if `python3` is
missing; install `python3` or remove the hook knowingly.

The allowlist is not host-extendable: a PM that needs more should file an issue for the engineer.

## 3. Shipped deny rules (every role, including every subagent)

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
additions survive an upgrade, and a host with an existing file must add this release's `hooks`
block and deny rules by hand.

## Not covered

Engineers and the main session keep Bash; they are bound only by the deny rules in section 3.
Symlinks inside the repository that point outside it are not resolved by the guard (UNVERIFIED).
