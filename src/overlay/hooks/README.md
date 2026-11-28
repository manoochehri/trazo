# PM limits: enforced by the harness, not by prompt (issue #279)

The `pm` agent cannot deploy, merge, push, dispatch a workflow, change a secret, start another
agent, or lift the `needs-decision` and `drive-halt` labels. Three mechanical layers hold that,
and the prompts only explain it.

## 1. The PM has no `Agent` tool (ADR 0025)

A subagent the PM started would not carry the PM's Bash allowlist, so the tool is removed from
`tools:` in `agents/pm.md`. The Coordinator (the main session) dispatches work the PM records on
an issue. A test fails if `Agent` returns.

## 2. The PM's Bash allowlist (`pm_bash_guard.py`)

An allowlist of exact argument shapes, registered twice so a skipped layer does not fail open:

- in `agents/pm.md` frontmatter (runs only while the PM runs, and only in a trusted workspace:
  Claude Code skips project subagent frontmatter hooks in `-p` sessions and when only a parent
  folder is trusted);
- in `settings.json` as a `PreToolUse` hook on `Bash` run with `--agent pm`: it enforces only
  when the hook input's `agent_type` is `pm`, and it runs in `-p` sessions too.

It permits read-only `git` and `gh` with known flags, `gh api repos/<owner>/<repo>/...` with
`--jq`/`--paginate` only, `gh issue create|comment|edit|close|reopen` and `gh label create|edit` with a fixed flag set (`--body`, not
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
| `Bash(gh workflow run ...)` | Not a prefix rule: `engineer_bash_guard.py` allows only exactly `gh workflow run owner-merge.yml -f pr=<digits>` (or `--field`), plus `gh workflow run drive.yml` and `gh workflow run release.yml` with no flag at all (#397; `release.yml` refuses unless its own owner, branch, changelog and milestone checks pass), no `--ref` or other flag, no other workflow; it also denies `gh api` to `dispatches` and `actions/workflows` endpoints (#333) |
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
hand. It also removes a rule or hook entry the installer added earlier (recorded in
`.trazo/INSTALLED-settings`) that this release no longer ships, and prints it; a rule you
wrote is never removed. An older rule that predates the record is kept and reported as
`kept (not recorded as installer-added): ...` with the exact line to delete. A recorded
deny rule is removed only while the engineer Bash guard hook is installed and registered.
Keep `.trazo/INSTALLED-settings` in `CODEOWNERS`: it decides what upgrade removes.

## 4. The engineer's Bash guard (`engineer_bash_guard.py`, issue #330)

The deny rules above match command text as written, so `gh api -X PUT repos/<o>/<r>/pulls/<n>/merge`,
`gh api -X POST repos/<o>/<r>/statuses/<sha>` and `cat .env` slipped past them. A second `Bash`
hook in `settings.json`, run with `--skip-agent pm`, denies those routes for every caller except
`pm` (which keeps the allowlist in section 2): the main session and the engineer and
senior-engineer subagents.

Since #378 it is a short blocklist over the parsed command, not a ban on shell constructs. It
judges the verbs a command resolves to: each `$(...)` and backtick span (also inside double
quotes, never inside single quotes) is checked as its own command, heredoc bodies are removed
(an unquoted body's substitutions are still checked), `#` comments are ignored, and pipes and
redirects are read for the verbs and files they name. It splits on `;` `&&` `||` `|`, shell
keywords and braces, and checks the command a shell flag (`bash -c`, `-lc`, `-xc`) or `eval` is
handed. It strips the wrappers `env` (including `-u` and `-S`), `sudo`, `timeout`, `nice`,
`command`, `exec`, `time`, `nohup`, `xargs` and `stdbuf`, and gh flags such as `--repo` wherever
they stand.

Allowed, beyond what a read-only engineer did before: `gh issue close|reopen`, any `gh api` call
that is not on the blocklist (milestone close, comments, labels, issue and PR edits, refs of the
agent's own branches), `$(...)`, heredocs, redirects and variables in any command, force-push of a
branch that is not the default, and writes to the auto-memory directory
(`~/.claude/projects/<project>/memory/<note>`). Prose that merely mentions a `.claude` path is not
a read of it.

Denied: `gh api` writes to `repos/<o>/<r>` itself, `rulesets`, `branches/*/protection`,
`actions/*` (secrets, variables, workflows, runs), `hooks`, `keys` / `gpg_keys`, `collaborators`,
`invitations`, `releases`, `environments`, `deployments`, `merges`, the merge endpoint, `contents`
without an explicit non-default `branch`, `git/refs` of tags or the default branch, commit
statuses (except the reviewer's and security's own, below) and `orgs/` and other account-level
endpoints; a write whose endpoint has a computed part unless the computed part is a variable or a
read-only lookup (`gh repo|pr|issue view`, `git rev-parse`) under an issues, pulls, statuses,
milestones or labels collection; `gh api graphql`, dispatches and `actions/workflows`;
`gh repo edit|delete|archive|rename`, `gh alias`, `gh auth token` and `gh auth ... --show-token`,
`gh release` writes, `gh run rerun`, `gh pr merge`, `gh secret`, `gh variable set`,
`put_secret.sh`; a `gh` subcommand named by a variable or substitution; `git push` to `main` or
`master`, `--all`, `--mirror`, `--tags`, `--follow-tags`, tag refs; git `alias.*` settings; a bare
shell fed from a pipe, here-string or heredoc, and `eval "$(...)"`; writes (redirect, `tee`,
`cp|mv|rm|touch|install|ln|sed -i|dd of=|git mv|git rm`) to `.claude/` and `.trazo/`, except
`.trazo/project/` (its `charter/` and `SKEPTIC_BAR.md` stay denied) and `.claude/worktrees/`;
and any word naming a protected path (`.env`, `secrets/`, keys, `~/.ssh`, `~/.claude`, ...).
`.env.example`-style placeholders are readable. After the security review of the first head: a
`gh api` write may not compute any part of its path after the collection (a variable can spell
`5/merge`), `--input` is denied on every write except a status post, `-F body=@file` is scanned
as the named path, `xargs` may not build `gh`, `git` or shell arguments (and nothing may feed
`xargs` from a heredoc or here-string), an unquoted newline separates commands, and writes to
`user`, `rename`, `rules`, `topics`, `pages`, `forks`, `check-runs`, `vulnerability-alerts`,
`interaction-limits` and `reviews` endpoints are denied. The PM may not create or edit a label
named `needs-decision` or `drive-halt`. A force-push must name its branch: `git push -f`
with no refspec and `git push --force origin HEAD` are denied.

Also denied: a `gh api` short-flag cluster is read flag by flag (`-iX PUT` is a PUT), a `#fragment`
on an endpoint is dropped as gh does, a backslash-newline pair joins the words around it, and a
`git` subcommand built by a variable. A write endpoint is percent-decoded to a fixed point first
(GitHub decodes `%252f` twice) and denied if `%`, `#` or `?` is still there. A bare variable as the whole last segment of a `milestones`
or `issues` PATCH (`milestones/$N`) is allowed; any other computed path part is a known false
denial (`issues/$N/comments`).

Known gaps: a `git push` refspec built by a variable (`X=main; git push origin $X`) is not judged
(the ruleset rejects the push); the working directory is not tracked (`cd .claude && echo x > y`); an endpoint or
path built by a variable cannot be judged; a plain `git push` or `git push origin HEAD` (no force)
while `main` is checked out is not judged, because the branch is unknown to the parser (the ruleset
rejects it); and `gh api -X DELETE` on an issue, comment or other non-blocklisted object passes.

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

One carve-out (#347, widened in #378): the `reviewer` subagent may post `trazo/verdict` and the
`security` subagent `trazo/security`, each only as a `gh api [-X POST] repos/<o>/<r>/statuses/<sha>`
call carrying `state` (success, failure, pending, error), `context` (its own), `description` and an
optional `target_url`. The repo and the sha may be literals, shell variables (`$REPO`, `${SHA}`)
or read-only `$(gh repo view ...)`, `$(gh pr view ...)` and `$(git rev-parse ...)` lookups; a
`description` may use `$(...)`. Every other caller, context, endpoint, method or field stays
denied, the skeptic included.

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
  subagents, so the main session no longer needs to write; the lock on main-session writes is
  `front_door_guard.py` below (#319). A hook binds the session it is registered in, not the agents
  that session starts.

# The front door does not do engineer work: `front_door_guard.py` (issue #319)

In a v0.3.1 host the front door edited pull request bodies and pushed empty commits to re-run CI
instead of dispatching an engineer. The role split was prose only. `settings.json` now registers a
`PreToolUse` hook on `Bash`, `Edit`, `Write`, `MultiEdit` and `NotebookEdit` that blocks the main
session from doing that work and says to dispatch an engineer (`/work <issue>`, or `/senior-eng`).

- **Who it binds.** The main session: a payload with no `agent_id` and no `agent_type`. A subagent's
  calls carry both, so the engineer, reviewer and the rest are not bound by it (their own guards
  are). `/eng` and `/senior-eng` start the pinned engineer subagents, so no role marker is needed
  and nothing can go stale or be forged.
- **What it blocks.** Edit, Write, MultiEdit and NotebookEdit on any file outside `.trazo/project/`
  (the path is resolved first, so `..` and symlinks do not escape; `/decide`, `/wrapup` and
  `/kickoff` write there from the main session). In Bash: a pull request body or label edit
  (`gh pr edit`), `git commit --allow-empty`, `git apply`, `sed -i`, `perl -i`, `tee` and a
  redirection to a file, including inside `bash -c`, `eval` and `$(...)`. Reading, `gh pr
  create|comment|view`, `gh issue *`, plain commits and pushes, and dispatching `owner-merge.yml`
  pass through.
- **Memory notes.** The session's memory directory (`~/.claude/projects/*/memory/`) is
  writable too (ADR 0032). `settings.json` ships no `allow` entry: Claude Code's own permission
  prompt for those writes is configured in the user's own settings, not shipped.
- **Fails closed.** Unparseable input, a missing path, a relative path, an unbalanced quote or a
  missing script all block (the declared command ends `|| exit 2`).
- **UNVERIFIED live.** That the main session's payload has neither field, that a forked skill
  (`/work`) carries them, and the NotebookEdit input shape (`notebook_path`) come from the Claude
  Code hooks documentation, not a recorded payload. If a forked skill carries neither field its
  edits are blocked with this message: too strict, never open. Probe the four cases (main
  session, subagent, `/eng`, `-p`) before relying on it.
- **A speed bump, not a boundary.** `python -c`, a script the agent writes then runs, shell
  variables and globs still write files. The CI ratchet and the review gates are the backstop; a
  hook that derives its path list from `settings.json` is a follow-up on #319.
- **Existing hosts.** `upgrade` merges the hook entry and places the script in `.trazo/hooks/`;
  add the entry by hand only if the script is already there.
