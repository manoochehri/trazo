#!/usr/bin/env python3
"""PreToolUse hook for the `pm` subagent's Bash tool (issue #279).

The PM reads and files issues. It never deploys, merges, pushes or sets a secret. Prompt text
does not hold that line, so this hook does: it is an allowlist, and anything it does not
recognise is blocked.

Contract (Claude Code hooks): the call arrives as JSON on stdin with `tool_input.command`;
exit 0 allows (the normal permission rules still apply, and deny rules always win), exit 2
blocks and stderr is the reason. Any error here blocks: the hook fails closed.

Allowed: read-only `git` and `gh`; `gh issue create|comment|edit` with a fixed flag set;
read-only filters after a pipe. Blocked: every shell construct that can smuggle a second
command (`;` `&` `||`, redirection, substitution, backticks, newlines, backslashes) outside
quotes, substitution and backticks inside double quotes, and any word that names a secret path.
"""

import json
import re
import sys

REASON = (
    "pm hook: {why}. The PM may run read-only git and gh, and `gh issue create|comment|edit`. "
    "Deploys, merges, pushes and secrets are not its to run (issue #279)."
)

FIRST = {"git", "gh", "ls", "pwd"}
FILTERS = {"head", "tail", "wc", "cut", "grep", "jq", "tr"}

GIT_READ = {
    "status", "log", "diff", "show", "rev-parse", "rev-list", "ls-files", "ls-tree",
    "blame", "describe", "shortlog", "cat-file", "merge-base", "branch", "tag", "remote",
    "fetch",
}  # fmt: skip
GIT_BAD_FLAGS = ("--output", "--upload-pack", "--receive-pack", "--exec", "--ext-diff")
GIT_BRANCH_FLAGS = {"--show-current", "-a", "-r", "-v", "-vv", "--list", "-l", "--all", "--remotes"}
GIT_BRANCH_TAKES_VALUE = {"--contains", "--merged", "--no-merged", "--list", "-l"}
GIT_FETCH_FLAGS = {"--prune", "-p", "--tags", "-q", "--quiet", "--all"}

GH_READ = {
    "issue": {"view", "list", "status"},
    "pr": {"view", "list", "diff", "checks", "status"},
    "run": {"view", "list"},
    "repo": {"view"},
    "release": {"view", "list"},
    "label": {"list"},
    "workflow": {"list", "view"},
    "auth": {"status"},
    "search": {"issues", "prs", "code", "repos", "commits"},
}
GH_API_BAD = ("-X", "--method", "-f", "-F", "--field", "--raw-field", "--input")
# (command, subcommand) -> (flags that take a value, flags that do not)
GH_WRITE = {
    ("issue", "create"): (
        {"--title", "-t", "--body", "-b", "--body-file", "-F", "--label", "-l",
         "--milestone", "-m", "--assignee", "-a"},
        set(),
    ),
    ("issue", "comment"): ({"--body", "-b", "--body-file", "-F"}, set()),
    ("issue", "edit"): (
        {"--add-label", "--remove-label", "--add-assignee", "--remove-assignee",
         "--milestone", "--title", "-t", "--body", "-b", "--body-file", "-F"},
        {"--remove-milestone"},
    ),
}  # fmt: skip
TEXT_FLAGS = {"--body", "-b", "--title", "-t"}  # free text: not scanned for secret paths
BODY_FILE_FLAGS = {"--body-file", "-F"}
SECRET_PATH = re.compile(r"(^|/|:)(\.env\b|secrets(/|$))|\.(pem|key)$")


class Deny(Exception):
    pass


def split_segments(cmd: str) -> list[list[str]]:
    """Split on unquoted `|` into segments of words. Refuse any other unquoted shell syntax,
    and substitution or backticks even inside double quotes."""
    segments: list[list[str]] = [[]]
    word: list[str] = []
    in_word = False
    quote = ""

    def end_word() -> None:
        nonlocal word, in_word
        if in_word:
            segments[-1].append("".join(word))
        word, in_word = [], False

    i = 0
    while i < len(cmd):
        c = cmd[i]
        if quote == "'":
            if c == "'":
                quote = ""
            else:
                word.append(c)
        elif quote == '"':
            if c == '"':
                quote = ""
            elif c == "\\" and i + 1 < len(cmd):
                i += 1
                word.append(cmd[i])
            elif c == "`" or (c == "$" and cmd[i + 1 : i + 2] in ("(", "{")):
                raise Deny("command substitution is not allowed")
            else:
                word.append(c)
        elif c in "'\"":
            quote, in_word = c, True
        elif c in " \t":
            end_word()
        elif c == "|":
            if cmd[i + 1 : i + 2] == "|":
                raise Deny("`||` is not allowed")
            end_word()
            if not segments[-1]:
                raise Deny("empty pipeline segment")
            segments.append([])
        elif c in "\n\r;&<>(){}`$\\":
            raise Deny(f"unquoted shell syntax {c!r} is not allowed")
        else:
            word.append(c)
            in_word = True
        i += 1
    if quote:
        raise Deny("unterminated quote")
    end_word()
    if not segments[-1]:
        raise Deny("empty command")
    return segments


def check_git(args: list[str]) -> None:
    if not args or args[0] not in GIT_READ:
        raise Deny(f"`git {args[0] if args else ''}` is not a read-only git command")
    sub, rest = args[0], args[1:]
    for a in rest:
        if a.startswith(GIT_BAD_FLAGS):
            raise Deny(f"git flag {a} can write or run code")
    if sub == "tag" and rest and rest[0] not in {"-l", "--list"}:
        raise Deny("`git tag` is read-only here (-l only)")
    if sub == "remote" and any(a != "-v" for a in rest):
        raise Deny("`git remote` allows only -v")
    prev = ""
    for a in rest:
        if sub == "branch" and a not in GIT_BRANCH_FLAGS and prev not in GIT_BRANCH_TAKES_VALUE:
            raise Deny("`git branch` is read-only here (list flags only)")
        if sub == "fetch" and a.startswith("-") and a not in GIT_FETCH_FLAGS:
            raise Deny(f"git fetch flag {a} is not allowed")
        prev = a


def check_gh_write(key: tuple[str, str], args: list[str]) -> None:
    valued, plain = GH_WRITE[key]
    i = 0
    while i < len(args):
        a = args[i]
        i += 1
        if not a.startswith("-"):
            continue  # an issue number or URL
        name, eq, inline = a.partition("=")
        if name in plain and not eq:
            continue
        if name not in valued:
            raise Deny(f"gh flag {a} is not granted to the PM")
        if eq:
            value = inline
        elif i < len(args):
            value = args[i]
            i += 1
        else:
            raise Deny(f"{name} needs a value")
        if name in BODY_FILE_FLAGS and (value.startswith(("/", "~")) or ".." in value.split("/")):
            raise Deny("--body-file must be a relative path inside the repository")


def check_gh(args: list[str]) -> None:
    if len(args) < 2 or args[0].startswith("-"):
        raise Deny("unrecognised gh command")
    cmd, sub, rest = args[0], args[1], args[2:]
    if cmd == "api":
        if any(a.startswith(GH_API_BAD) for a in args[1:]):
            raise Deny("`gh api` is read-only here (no method, field or input flags)")
        if any(a.lstrip("/").startswith("graphql") for a in args[1:]):
            raise Deny("`gh api graphql` can mutate")
        return
    if sub in GH_READ.get(cmd, ()):
        return
    if (cmd, sub) in GH_WRITE:
        check_gh_write((cmd, sub), rest)
        return
    raise Deny(f"`gh {cmd} {sub}` is not granted to the PM")


def check(command: str) -> None:
    for index, argv in enumerate(split_segments(command)):
        head, args = argv[0], argv[1:]
        # Free-text values may mention secret paths; every other word may not name one.
        prev = ""
        for a in args:
            if prev not in TEXT_FLAGS and SECRET_PATH.search(a):
                raise Deny("a secret path is not readable by the PM")
            prev = a
        if index == 0:
            if head not in FIRST:
                raise Deny(f"`{head}` is not an allowed command")
            if head == "git":
                check_git(args)
            elif head == "gh":
                check_gh(args)
        elif head not in FILTERS:
            raise Deny(f"`{head}` is not an allowed pipe filter")


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        if payload.get("tool_name", "Bash") != "Bash":
            return 0
        command = payload["tool_input"]["command"]
        if not isinstance(command, str):
            raise Deny("no command")
        check(command)
    except Deny as why:
        print(REASON.format(why=why), file=sys.stderr)
        return 2
    except Exception as err:  # noqa: BLE001 - fail closed on anything unexpected
        why = f"hook could not parse the call ({type(err).__name__})"
        print(REASON.format(why=why), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
