#!/usr/bin/env python3
"""PreToolUse hook for the front door: the main session does not do engineer work (issue #319).

In a host on v0.3.1 the front door edited pull request bodies and pushed empty commits to re-run
CI instead of dispatching an engineer, and could give no reason beyond "nothing stopped me". The
split was prose only, so this hook is the mechanical layer: the main session may read, dispatch
and write project state; it may not edit code or rewrite pull requests.

Who is the front door: the main session. A PreToolUse payload from inside a subagent carries a
non-empty `agent_id` and `agent_type`; the main session carries neither. This guard binds only a
call with neither. `/eng` and `/senior-eng` start the pinned engineer subagents (they do not build
in the main session), so no role marker is needed: the subagent's own calls are not the front
door's. The engineer's and PM's Bash limits are `engineer_bash_guard.py` and `pm_bash_guard.py`.

What the front door may not do (everything else passes through):

- `Edit`, `Write`, `MultiEdit`, `NotebookEdit` on any file outside `.trazo/project/` (decision
  records, STATUS, workstreams: the files `/decide`, `/wrapup` and `/kickoff` write from the main
  session) and outside the session's memory directory (`~/.claude/projects/<project>/memory/`,
  ADR 0032). Issue and comment text goes through `gh issue`, which this guard does not touch.
  The path is resolved first, so `..` and symlinks out of those directories are denied.
- `Bash`: `gh pr edit`, `git commit --allow-empty`, `git apply`, `sed -i` / `perl -i`, `tee`, and a
  redirection to a file. Also `bash -c`, `eval` and `$(...)` bodies, which are read the same way.

Contract (Claude Code hooks): JSON on stdin; exit 0 allows (permission deny rules still win), exit
2 blocks and stderr is the reason. Any error blocks: the hook fails closed.

UNVERIFIED live: that the main session's payload carries no `agent_id`/`agent_type`, that a forked
skill (`/work`) carries them, and the NotebookEdit input shape (`notebook_path`). The Claude Code
hooks documentation says subagent calls carry both; it was not probed. The failure mode if a
forked skill carries neither is "too strict" (its edits are blocked with a message naming the
cause), never open. The tests pin the contract this hook assumes.

This is a speed bump, not a security boundary: a shell can still build a write this parser does not
see (`python -c`, a script it wrote, a variable). The CI ratchet and the PR review are the
backstop. See the hooks README.
"""

import json
import os
import re
import shlex
import sys
from pathlib import Path

REASON = (
    "front door guard: {why}. The front door does not edit code, commit or rewrite pull "
    "requests; dispatch an engineer: `/work <issue>` (or `/senior-eng <issue>` for a "
    "tier:senior issue). It may write only under .trazo/project/ and its memory directory "
    "(issues #319, #379)."
)

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
WRAPPERS = {"env", "command", "sudo", "nohup", "time", "exec", "builtin", "nice", "timeout"}
SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
KEYWORDS = {"{", "}", "!", "if", "then", "else", "elif", "fi", "do", "done", "while", "until"}
GIT_VALUE_FLAGS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}
GH_VALUE_FLAGS = {"-R", "--repo", "--hostname"}
SEPARATORS = {";", "&&", "||", "|", "&", "|&", "(", ")", "\n"}
REDIRECTS = {">", ">>", ">|", "&>", "&>>"}
SAFE_TARGETS = {"/dev/null", "/dev/stderr", "/dev/stdout"}
ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")
SUBSTITUTION = re.compile(r"\$\(([^()]*)\)|`([^`]*)`")


class Deny(Exception):
    pass


def _roots(payload: dict) -> list[Path]:
    roots = []
    for raw in (os.environ.get("CLAUDE_PROJECT_DIR"), payload.get("cwd")):
        if isinstance(raw, str) and raw.strip():
            roots.append(Path(raw).resolve())
    return roots


def _in_memory_dir(real: Path) -> bool:
    """The session's memory notes: ~/.claude/projects/<project>/memory/ and below (ADR 0032)."""
    base = Path.home().resolve() / ".claude" / "projects"
    try:
        rel = real.relative_to(base)
    except ValueError:
        return False
    return len(rel.parts) >= 3 and rel.parts[1] == "memory"


def _check_path(payload: dict, tool_input: dict) -> None:
    raw = tool_input.get("file_path", tool_input.get("notebook_path"))
    if not isinstance(raw, str) or not raw.strip():
        raise Deny("the edit names no file_path")
    path = Path(raw)
    if not path.is_absolute():
        raise Deny(f"{raw!r} is not an absolute path")
    real = path.resolve()
    if _in_memory_dir(real):
        return
    for root in _roots(payload):
        allowed = root / ".trazo" / "project"
        if real == allowed or allowed in real.parents:
            return
    raise Deny(f"the main session may not edit {raw!r}")


def _segments(command: str) -> list[list[str]]:
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    segments: list[list[str]] = [[]]
    for token in lexer:
        if token in SEPARATORS or set(token) <= set(";&|()"):
            segments.append([])
        else:
            segments[-1].append(token)
    return [s for s in segments if s]


def _strip(words: list[str]) -> list[str]:
    """Drop leading keywords, env assignments and wrappers (a wrapper's own flags too)."""
    words = list(words)
    while words:
        head = words[0]
        if head in KEYWORDS or ASSIGNMENT.match(head):
            words.pop(0)
        elif head in WRAPPERS:
            words.pop(0)
            while words and (words[0].startswith("-") or ASSIGNMENT.match(words[0])):
                words.pop(0)
            if head == "timeout" and words:
                words.pop(0)  # the duration
        else:
            break
    return words


def _subcommand(words: list[str], value_flags: set[str]) -> tuple[list[str], list[str]]:
    """Words after the program name, global flags removed; returns (subcommand words, flags)."""
    rest = words[1:]
    out: list[str] = []
    skip = False
    for word in rest:
        if skip:
            skip = False
        elif word in value_flags:
            skip = True
        elif word.startswith("-") and not out:
            continue
        else:
            out.append(word)
    return out, rest


def _check_segment(words: list[str]) -> None:
    words = _strip(words)
    if not words:
        return
    prog = words[0].rsplit("/", 1)[-1]
    if prog in SHELLS:
        for i, word in enumerate(words[1:], 1):
            if word.startswith("-") and not word.startswith("--") and "c" in word:
                if i + 1 < len(words):
                    _check_command(words[i + 1])
                return
        return
    if prog == "eval":
        _check_command(" ".join(words[1:]))
        return
    if prog == "tee":
        raise Deny("`tee` writes a file")
    in_place = re.compile(r"-[A-Za-z]*i.*|--in-place(=.*)?")
    if prog in {"sed", "perl"} and any(in_place.fullmatch(w) for w in words[1:]):
        raise Deny(f"`{prog} -i` edits a file in place")
    if prog == "git":
        sub, rest = _subcommand(words, GIT_VALUE_FLAGS)
        if sub[:1] == ["apply"]:
            raise Deny("`git apply` edits files")
        if sub[:1] == ["commit"] and "--allow-empty" in rest:
            raise Deny("an empty commit to re-run CI is engineer work")
    if prog == "gh":
        sub, _ = _subcommand(words, GH_VALUE_FLAGS)
        if sub[:2] == ["pr", "edit"]:
            raise Deny("`gh pr edit` rewrites a pull request")


def _check_command(command: str) -> None:
    try:
        segments = _segments(command)
    except ValueError as err:
        raise Deny(f"the command could not be parsed ({err})") from err
    for match in SUBSTITUTION.finditer(command):
        _check_command(match.group(1) or match.group(2) or "")
    for words in segments:
        for i, word in enumerate(words):
            target = None
            if word in REDIRECTS:
                target = words[i + 1] if i + 1 < len(words) else ""
            elif re.fullmatch(r"[0-9]*>>?", word) and word.strip("0123456789") in {">", ">>"}:
                target = words[i + 1] if i + 1 < len(words) else ""
            if target is not None and target not in SAFE_TARGETS and not target.startswith("&"):
                if target and _in_memory_dir(Path(os.path.expanduser(target)).resolve()):
                    continue
                raise Deny(f"a redirection writes {target!r}")
        _check_segment(words)


def check(payload: object) -> None:
    if not isinstance(payload, dict):
        raise Deny("the hook input is not a JSON object")
    for key in ("agent_id", "agent_type"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return  # a subagent: its own guards bind it, not this one
    tool = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    if tool in EDIT_TOOLS:
        if not isinstance(tool_input, dict):
            raise Deny("the edit carries no tool_input")
        _check_path(payload, tool_input)
    elif tool == "Bash":
        command = tool_input.get("command") if isinstance(tool_input, dict) else None
        if not isinstance(command, str):
            raise Deny("the Bash call carries no command")
        _check_command(command)


def main() -> int:
    try:
        check(json.load(sys.stdin))
    except Deny as why:
        print(REASON.format(why=why), file=sys.stderr)
        return 2
    except Exception as err:  # noqa: BLE001 - fail closed on anything unexpected
        print(
            REASON.format(why=f"hook could not parse the call ({type(err).__name__})"),
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
