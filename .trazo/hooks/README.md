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
| `Bash(gh workflow run ...)` | Not a prefix rule: `engineer_bash_guard.py` allows only exactly `gh workflow run owner-merge.yml -f pr=<digits>` (or `--field`), no `--ref` or other flag, no other workflow; it also denies `gh api` to `dispatches` and `actions/workflows` endpoints (#333) |
| `Bash(gh pr merge *)` | Merging goes through the gated workflows (`drive.yml`, `owner-merge.yml`), not a direct session merge |
| `Bash(fly *)`, `Bash(flyctl *)` | Production hosting |
| `Bash(clasp push *)`, `Bash(clasp deploy *)` | Apps Script deploys |
| `Bash(scripts/deploy*)`, `Bash(./scripts/deploy*)` | A host's deploy scripts |
| `Bash(scripts/put_secret.sh *)` | Secrets are entered by the human |
| `Bash(gh secret *)`, `Bash(gh variable set *)` | Repository secrets and variables |

A deny rule matches the command text as written. It is not a security boundary: `git -C . push`,
`bash scripts/deploy.sh` or a wrapper such as `env` can slip past a prefix rule (Claude Code
permissions docs, "What Bash rules don't match"). That is why the PM's Bash goes through the
allowlist above and why deploy credentials should live only in CI.

## Extending the list for a host

Deploy commands are host-specific. Add your own rules to the host's `.claude/settings.json`
under `permissions.deny`, for example `Bash(./bin/ship *)` or `Bash(terraform apply *)`. The
installer writes `settings.json` only when absent; on `upgrade` it merges this release's missing
deny rules and hook entries into your existing file (additive and idempotent, backup at
`.claude/settings.json.bak`), so your additions survive and you do not add the hook entries by
hand.

## 4. The engineer's Bash guard (`engineer_bash_guard.py`, issue #330)

The deny rules above match command text as written, so `gh api -X PUT repos/<o>/<r>/pulls/<n>/merge`,
`gh api -X POST repos/<o>/<r>/statuses/<sha>` and `cat .env` slipped past them. A second `Bash`
hook in `settings.json`, run with `--skip-agent pm`, denies those routes for every caller except
`pm` (which keeps the allowlist in section 2): the main session and the engineer and
senior-engineer subagents.

It is a denylist over the parsed command. It splits on `;` `&&` `||` `|`, `$(...)` and backticks
(also inside double quotes), shell keywords and braces (`if`, `then`, `do`, `{`, `!`), and it
checks the command a shell flag (`bash -c`, `-lc`, `-xc`) or `eval` is handed. It strips the
wrappers `env` (including `-u` and `-S`), `sudo`, `timeout`, `nice`, `command`, `exec`, `time`,
`nohup`, `xargs` and `stdbuf`, and gh flags such as `--repo` wherever they stand. It denies every
`gh api` call that is not a GET or HEAD (`-X`, `--method`, `-f`, `-F`, `--input` and method
override headers), `gh api graphql` in any case, `gh alias`, `gh auth token`, `gh release`
writes, `git push` to `main` or `master` (or `--all`, `--mirror`), git `alias.*` settings, a bare
shell that reads a script from a pipe, here-string or heredoc, and any word naming a protected path
or command. It allows what an engineer needs: `git` (pushes to feature branches), `gh pr
create|view|comment|diff|checks`, `gh issue *`, read-only `gh api`, tests, `uv`, `make`, and
`.env.example`-style placeholders.

One source: it reads the protected commands (`Bash(<prefix> *)`) and paths (`Read(<glob>)`) from
`permissions.deny` in `.claude/settings.json`, so adding a rule there extends the guard. If that
file is missing or has no such rules the hook blocks. Exit 2 blocks, and the declared command ends
`|| exit 2`, so a missing script or `python3` blocks too.

### What still gets through

This hook is a speed bump, not a security boundary. It parses text, and the shell can build a
command the parser never sees. These are known to get through:

- `curl` with `$GH_TOKEN` (or any HTTP client): an agent that holds the token can merge, set a
  commit status or read a secret with no `gh` and no `.env` word in the command.
- Git aliases that already exist, `git -c alias` forms the parser does not read, and `gh` aliases
  that were set earlier (`gh m`): the hook only sees the alias name.
- Shell variables and globs: `f=.env; cat $f`, `cat .e*`, `cat .en?`, `cat "$HOME"/.ssh/id_rsa`.
- Constructs that compute the command: `eval $(...)`, `$(echo gh) pr merge`, `printf ... | sh -s`
  built from a variable, process substitution, aliases and shell functions.
- `python -c`, `node -e`, and any script the agent writes and then runs.
- A shell that is handed its script some other way than the forms listed above.
- Wrappers and flags not listed above. A flag with a value that the parser does not know is read as
  a bare flag, so the value is mistaken for the command.
- Anything the Read, Edit and Write tools do: this hook binds Bash only.

The real fix is an agent token that cannot merge or set statuses (#320), plus branch protection.
Until then, treat a green result from this guard as "the obvious routes are closed", never as
"the engineer cannot merge".

## Not covered

Engineers and the main session are bound by the deny rules in section 3 and the guard in section
4, neither of which is a security boundary (see "What still gets through"). Symlinks inside the repository that point outside it
are not resolved by the guard (UNVERIFIED).

# Only the pinned roles start as subagents: `agent_role_guard.py` (issue #326)

The front door once started generic subagents (`general-purpose`, `Explore`, `Plan`) and gave them
a role in the prompt, instead of the pinned agents or the role commands. A prompt did not stop it.
`settings.json` registers a `PreToolUse` hook on the `Agent` tool (`Agent|Task`) that allows only
`pm`, `engineer`, `senior-engineer`, `reviewer`, `security` and `skeptic` (and the installer's `trazo-` prefixed copies) and
blocks everything else with exit 2. Engineering is `/eng`, `/senior-eng` or `/work`; architecture
is `/architect`.

- **Fails closed.** A missing, empty or non-string `subagent_type`, unparseable input, or a missing
  script all block (the declared command ends `|| exit 2`).
- **UNVERIFIED live.** The input shape (`tool_name`, `tool_input.subagent_type`) comes from the
  Claude Code hooks documentation, not from a recorded payload; the live check was not run. A payload
  of another shape is blocked, so the failure mode is "too strict", never "open". If Claude Code
  starts a pinned agent under a name this list does not know, the hook blocks it.
- **Existing hosts add it by hand.** The installer writes `settings.json` only when absent and never
  overwrites an existing one, so a host with its own `settings.json` must add this hook entry itself
  after upgrading, together with the hook script the upgrade places in `.trazo/hooks/`. Do not add
  the entry before the script is installed: the declared command blocks every Agent call when the
  script is missing.
- **Not covered.** There is no pinned architect agent (ADR 0021 says none), so `/architect` stays a
  main-session role switch. `/eng` and `/senior-eng` start the pinned `engineer` and `senior-engineer`
  subagents, so the main session no longer needs to write; a lock on main-session writes is the next
  step and is not part of this change. A hook binds the session it is registered in, not the agents
  that session starts.
