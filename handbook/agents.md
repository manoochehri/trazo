# `AGENTS.md` and Trazo

Two different files answer two different questions, and this page is the short version of
why you want both.

## `AGENTS.md` is *how*

A repository's `AGENTS.md` is plain markdown that tells an agent how to work in **that
codebase**: the one command that builds it, the one that tests it, the conventions, the
gotchas. It is rewritten as the project changes, because it describes the project.

If your repo has no `AGENTS.md`, that is normal and not a problem. Writing one is ordinary
work — you already know the commands.

## Trazo is *whether*

Trazo answers a different question: not how to run the tests, but **whether the work may be
done at all.** Who is authorised to act, which limits are human-only, what evidence a claim
needs before it counts, and which roles must not collapse into one person. It does not
describe your codebase, and it is not rewritten when your codebase changes — it accumulates.

## What that looks like in practice

Suppose an agent wants to cut a release.

> **`AGENTS.md` says:** run `make release`. It validates, tags, and pushes `vX.Y.Z`.

That is everything needed to *run* the command. Now the questions Trazo answers:

- May I run it? Only once CI is green. **A command existing is not permission to run it.**
- What must never happen? Moving a tag that already exists — someone may hold it.
- What is out of scope entirely? Cutting a release as a branch. A release is a tag.

The same command, governed or not. The `AGENTS.md` line is the *how*; the four rules above
are the *whether*.

## When they disagree, Trazo wins

This is the rule worth stating plainly, because it is the one an agent under pressure will
want to reinterpret:

> An `AGENTS.md` can establish **how** an action is performed. Only Trazo establishes
> **whether** you are permitted to perform it.

And the corollary, which is really the same point:

**Proximity is not authority.** A nested instruction, or one that arrived later in the
context, does not override a project-level safety rule simply because the agent read it
afterwards. A file that describes a codebase is not thereby a statement about who may act.

## They are not alternatives

Neither file replaces the other, and you are not being asked to choose.

| | `AGENTS.md` | Trazo |
|---|---|---|
| Answers | how do I work in this repo | may I do this, and do I believe it |
| Rewritten | as the project changes | accumulates; records are append-only |
| Written by | the project, day to day | decided once, and changed deliberately |
| Scope | your codebase | the work being done on it |

A mounted repo wants both, written by different parties. The host owns its `AGENTS.md` —
Trazo never overwrites one.

!!! note "This repository's own files"
    Trazo is itself a repository, so it has both: [`AGENTS.md`](https://github.com/manoochehri/trazo/blob/main/AGENTS.md)
    for the commands, and `.trazo/` for the governance. They point at each other, and
    neither is a copy of the other.

## If you use more than one tool

The relationship above is tool-neutral — that is the point of it. A repo that runs
Claude Code, Cline and Cursor does not need three sets of rules. It needs one
`.trazo/rules.md`, and whatever each tool reads to reach it: `CLAUDE.md`,
`AGENTS.md`, native skill metadata, or native agent metadata. Same rules, different door.

## What is not claimed here

Being plain about the limits matters more than sounding certain.

An `AGENTS.md` is read *instructed* — it is a file an agent is told to read and then may or
may not follow. A Claude Code `@` import is *mechanical* — the contents are inlined when the
session starts, with no tool call and no choice. That difference is real, and it is why the
`CLAUDE.md` adapter uses an import rather than a link.

Codex support is runtime-tested with `codex-cli 0.162.0-alpha.2`. Codex reads the root
[`AGENTS.md`](https://developers.openai.com/codex/guides/agents-md/), discovers project skills
under [`.agents/skills/`](https://learn.chatgpt.com/docs/build-skills), and supports project
agents in [`.codex/agents/`](https://learn.chatgpt.com/docs/agent-configuration/subagents).
Trazo installs thin Codex wrappers there; canonical roles and workflow
content remain under `.trazo/roles/` and `.trazo/skills/`, alongside `.trazo/rules.md` and
project state. A read-only `codex exec` smoke test explicitly invoked `$trazo-work` and
confirmed skill discovery and rule loading. A second session delegated to the installed
`trazo-reviewer` agent, which loaded its canonical role and rules in a separate context.
Claude's `CLAUDE.md` import remains runtime-tested separately.

## Where to go next

- [What is `.trazo/`](overlay.md) — the layout and the one contract your repo must satisfy
- [The guide](guide.md) — the full setup walkthrough
- [The playbook](playbook.md) — how a normal day runs
