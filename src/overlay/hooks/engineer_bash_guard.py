#!/usr/bin/env python3
"""PreToolUse hook for the Bash tool of every caller except `pm` (issue #330).

The `settings.json` deny rules match command text as written, so the engineer's Bash still
reached a merge (`gh api -X PUT .../pulls/N/merge`), a commit status (`gh api -X POST
.../statuses/<sha>`) and secrets (`cat .env`). This hook is a denylist over the parsed command
that closes those routes. The PM is not its business: the PM runs an allowlist
(pm_bash_guard.py).

One source: the protected commands and paths are read from `permissions.deny` in the project's
`.claude/settings.json` (`Bash(<prefix> *)` rules and `Read(<glob>)` rules). The only rule
that file cannot express is "no `gh api` write", which is code here. If settings.json is missing,
unreadable or carries no Bash and Read rules, the hook denies: it fails closed, like the rest.

Contract (Claude Code hooks): the call arrives as JSON on stdin with `tool_input.command` and,
inside a subagent, `agent_type`. Exit 0 allows (permission deny rules still win), exit 2 blocks
and stderr is the reason. Any error blocks.

    engineer_bash_guard.py                  enforce for every caller
    engineer_bash_guard.py --skip-agent pm  step aside when agent_type == "pm"

This is a backstop, not a security boundary: a shell can still build a command this parser does
not see (`python -c`, a script it wrote, an obfuscated word). The real fix is an agent token
that cannot merge or set statuses (#320).
"""

import json
import os
import re
import shlex
import sys
from pathlib import Path

REASON = (
    "engineer guard: {why}. Merging, setting commit statuses, writing through `gh api` and "
    "reading secrets are not the engineer's to do (issue #330). Use `gh pr`, `gh issue` or a "
    "read-only `gh api` call, and edit config through the Edit tool; the owner merges."
)

WRAPPERS = {"env", "command", "sudo", "nohup", "time", "exec", "builtin", "nice", "xargs", "stdbuf"}
SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
GH_VALUE_FLAGS = {"-R", "--repo", "--hostname"}  # gh global flags that take a value
GH_METHOD_FLAGS = {"-X", "--method"}
GH_FIELD_FLAGS = {"-f", "-F", "--field", "--raw-field", "--input"}  # imply POST without -X
# Always denied under `gh`, whatever the arguments: not expressible as a settings.json rule.
GH_ALWAYS = {("alias",), ("auth", "token"), ("api", "graphql")}
# Flag values that are free text, not paths or commands.
TEXT_FLAGS = {
    "-m", "--message", "--body", "-b", "--title", "-t", "--jq", "-q", "--search", "-S", "--notes",
    "--subject", "--comment",
}  # fmt: skip
# Placeholder config files are meant to be read and edited (".trazo/rules.md": new config goes
# in the env example).
PLACEHOLDER = re.compile(r"\.env\.(example|sample|template|dist)$", re.IGNORECASE)
OPERATORS = {";", "&", "&&", "|", "||", "|&", "(", ")", "\n", ";;", ";&", ";;&", "&>", "<(", ">("}
REDIRECTS = {"<", ">", ">>", "<<", "<<<", "<&", ">&", ">|"}


class Deny(Exception):
    pass


def settings_path() -> Path:
    return Path(__file__).resolve().parents[2] / ".claude" / "settings.json"


def glob_to_regex(glob: str) -> re.Pattern[str]:
    """`./**/.env.*` -> a pattern matching a word that names such a file; `secrets/**` -> the
    directory anywhere in a path; `~/.ssh/**` -> that directory."""
    body = glob.removeprefix("./").removeprefix("~/")
    tail = ""
    if body.endswith("/**"):
        body, tail = body[:-3], r"(/|$)"
    else:
        tail = "$"
    out = ""
    i = 0
    while i < len(body):
        if body.startswith("**/", i):
            out += r"(.*/)?"
            i += 3
        elif body[i] == "*":
            out += r"[^/]*"
            i += 1
        else:
            out += re.escape(body[i])
            i += 1
    return re.compile(r"(^|[/=:])" + out + tail, re.IGNORECASE)


def load_rules() -> tuple[list[list[str]], list[re.Pattern[str]]]:
    """(command prefixes, secret path patterns) derived from permissions.deny."""
    try:
        deny = json.loads(settings_path().read_text(encoding="utf-8"))["permissions"]["deny"]
    except (OSError, ValueError, KeyError, TypeError) as err:
        raise Deny(f"cannot read the deny rules from settings.json ({type(err).__name__})") from err
    prefixes: list[list[str]] = []
    paths: list[re.Pattern[str]] = []
    for rule in deny if isinstance(deny, list) else []:
        match = re.fullmatch(r"(Bash|Read)\((.+)\)", rule) if isinstance(rule, str) else None
        if not match:
            continue
        kind, spec = match.groups()
        if kind == "Bash":
            words = spec.removesuffix("*").split()
            if words:
                prefixes.append(words)
        else:
            paths.append(glob_to_regex(spec))
    if not prefixes or not paths:
        raise Deny("settings.json carries no Bash and Read deny rules to enforce")
    return prefixes, paths


def segments(command: str) -> list[list[str]]:
    """Split into simple commands on operators, substitutions and backticks. Redirect operators
    stay as words so the file they name is scanned."""
    try:
        lexer = shlex.shlex(command.replace("`", " ; "), posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError as err:
        raise Deny(f"unparseable command ({err})") from err
    out: list[list[str]] = [[]]
    for tok in tokens:
        if tok in OPERATORS:
            out.append([])
        elif tok == "$" or set(tok) <= set("&|;<>()$"):
            if tok in REDIRECTS:
                out[-1].append(tok)
        else:
            out[-1].append(tok)
    return [s for s in out if s]


def strip_wrappers(argv: list[str]) -> list[str]:
    while argv:
        word = argv[0]
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", word):
            argv = argv[1:]
        elif os.path.basename(word) in WRAPPERS:
            argv = argv[1:]
            while argv and (argv[0].startswith("-") or re.fullmatch(r"[A-Za-z_]\w*=.*", argv[0])):
                argv = argv[1:]
        else:
            break
    return argv


def gh_args(argv: list[str]) -> list[str]:
    """argv after `gh` with global flags removed."""
    rest = argv[1:]
    while rest and rest[0].startswith("-"):
        name = rest[0].partition("=")[0]
        rest = rest[2:] if name in GH_VALUE_FLAGS and "=" not in rest[0] else rest[1:]
    return rest


def check_gh_api(args: list[str]) -> None:
    method = None
    implied = False
    i = 1
    while i < len(args):
        a = args[i]
        name, eq, inline = a.partition("=")
        if a.startswith("-X") and not a.startswith("--") and len(a) > 2:
            method = a[2:].lstrip("=")
        elif name in GH_METHOD_FLAGS:
            method = inline if eq else (args[i + 1] if i + 1 < len(args) else "")
            i += 0 if eq else 1
        elif name in GH_FIELD_FLAGS or (a.startswith(("-f", "-F")) and len(a) > 2 and a[2] != "-"):
            implied = True
            i += 0 if eq or len(a) > 2 and not a.startswith("--") else 1
        if "method-override" in a.lower():
            raise Deny("`gh api` method override headers are not allowed")
        i += 1
    effective = (method or ("POST" if implied else "GET")).upper()
    if effective not in {"GET", "HEAD"}:
        raise Deny(f"`gh api` is read-only for the engineer ({effective} is a write)")


def check_argv(argv: list[str], prefixes: list[list[str]], paths: list[re.Pattern[str]]) -> None:
    argv = strip_wrappers(argv)
    if not argv:
        return
    head = os.path.basename(argv[0])
    if argv[0].startswith("$"):
        raise Deny("a command named by a variable cannot be checked")
    if head in SHELLS or head == "eval":
        # `bash -c "<script>"`, `eval <words>`, `bash script.sh`: check what it will run.
        if head == "eval":
            check(" ".join(argv[1:]), prefixes, paths)
        elif "-c" in argv:
            inner = argv.index("-c") + 1
            if inner < len(argv):
                check(argv[inner], prefixes, paths)
        else:
            rest = [a for a in argv[1:] if not a.startswith("-")]
            if rest:
                check_argv(rest, prefixes, paths)
    candidates = [argv]
    if head == "gh":
        args = gh_args(argv)
        candidates = [["gh", *args]]
        for banned in GH_ALWAYS:
            if tuple(args[: len(banned)]) == banned:
                raise Deny(f"`gh {' '.join(banned)}` is not the engineer's")
        if args[:1] == ["api"]:
            check_gh_api(args)
    for cand in candidates:
        for prefix in prefixes:
            n = len(prefix)
            if len(cand) >= n and [os.path.basename(cand[0]), *cand[1:n]] == [
                os.path.basename(prefix[0]),
                *prefix[1:],
            ]:
                raise Deny(f"`{' '.join(prefix)}` is denied by settings.json")
    previous = ""
    for word in argv[1:]:
        if previous not in TEXT_FLAGS and not PLACEHOLDER.search(word):
            if any(p.search(word) for p in paths):
                raise Deny(f"{word!r} names a secret path")
        previous = word


def check(command: str, prefixes: list[list[str]], paths: list[re.Pattern[str]]) -> None:
    for argv in segments(command):
        check_argv(argv, prefixes, paths)


def main(argv: list[str]) -> int:
    try:
        skip = argv[argv.index("--skip-agent") + 1] if "--skip-agent" in argv else None
        payload = json.load(sys.stdin)
        if skip is not None and payload.get("agent_type") == skip:
            return 0
        if payload.get("tool_name", "Bash") != "Bash":
            return 0
        command = payload["tool_input"]["command"]
        if not isinstance(command, str):
            raise Deny("no command")
        prefixes, paths = load_rules()
        check(command, prefixes, paths)
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
    sys.exit(main(sys.argv[1:]))
