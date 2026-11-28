# 0032: Agents are permissive by default; GitHub holds the irreversible limits

**Date:** 2026-11-27  **Status:** proposed (becomes accepted when the owner dispatches the merge; it changes `rules.md`, role files and `settings.json`)

Owner direction on [#377](https://github.com/manoochehri/trazo/issues/377), architect design in the
same thread, tracked in [#379](https://github.com/manoochehri/trazo/issues/379).
Supersedes the shell-construct and role-restriction parts of [0029](0029-the-front-door.md) and of
issue #330 (the engineer Bash denylist). It loosens permissions deliberately; it does not loosen
any limit on the irreversible list below.

## Context

Policy was enforced by regex over shell text. It blocked legitimate calls (`$(`, heredocs,
redirects, any text naming `.claude`, every `gh api` write) and still leaked (`python -c`). The
owner asked for agents to be very permissive and for the owner to be out of the routine loop.
GitHub already holds the real limits: the main ruleset, CODEOWNERS and `owner-merge.yml`.

## Decision

- Agents may use ordinary shell constructs; a command is judged by the verbs it resolves to.
  Role and skill text that told agents to avoid `$(...)`, heredocs or backticks is removed.
- The PM may close issues and edit labels (no longer limited to create, comment, edit), except
  that it never removes `needs-decision` or `drive-halt`: clearing `needs-decision` is the owner's
  decision signal, so a PM that could clear it could approve an owner gate itself.
  `pm_bash_guard.py` `STOP_LABELS` already enforces this and is unchanged.
- The reviewer and security post their own commit status (`trazo/verdict`, `trazo/security`) with
  one `gh api` call each, and no other context.
- The main session (front door) may write its memory directory
  (`~/.claude/projects/<project>/memory/`) and issue text, through `front_door_guard.py` only. The
  `Read(~/.claude/**)` deny stays and the edit lock on repository files stays. No `allow` entry
  ships in `settings.json`: shipped settings only deny, so they never grant a host permissions
  (pinned by `test_shipped_settings_keep_deny_rules_and_engineer_default` in
  `tests/test_install.py` and by `tests/test_front_door_guard.py`). Claude Code's own permission prompt for `~/.claude` memory
  writes is therefore configured in the user's own settings, not shipped. The hook also cannot
  name only the current project's directory, since the project slug is not in the payload; it
  allows `~/.claude/projects/*/memory/`.
- `rules.md` states the principle in "Permissive by default".

The stop list in `rules.md` and every owner-only limit win over this record.

Unchanged and still human-only: secrets and credentials, production and spend, force-push or
deletion on the default branch, repository, ruleset and release settings, `gh pr merge` (merging
is `owner-merge.yml`), and governance paths (CODEOWNERS, rules, roles, hooks, settings, workflows,
charter).

## Alternatives considered

- Keep the denylist and patch each false positive: it is the wrong layer and grows forever.
- Remove all guards: the secret-read and merge limits are cheap and irreversible if wrong.

## Consequences

Easier: agents stop hitting blocks on harmless commands. Harder: a looser shell guard is easier
to bypass; accepted, it was already bypassable and was never the security boundary. Dependent
work: the guard rewrite (#378) and `pm_bash_guard.py` must match this text before the PM can
actually close issues; the ruleset change is a separate owner-run script. Revisit if a merge of a
risky change happens with a status not set by its own role context.
