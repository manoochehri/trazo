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

WRAPPERS = {
    "timeout",
    "env",
    "command",
    "sudo",
    "nohup",
    "time",
    "exec",
    "builtin",
    "nice",
    "xargs",
    "stdbuf",
}
SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
GH_VALUE_FLAGS = {"-R", "--repo", "--hostname"}  # gh global flags that take a value
GH_METHOD_FLAGS = {"-X", "--method"}
GH_FIELD_FLAGS = {"-f", "-F", "--field", "--raw-field", "--input"}  # imply POST without -X
# Always denied under `gh`, whatever the arguments: not expressible as a settings.json rule.
GH_ALWAYS = {
    ("alias",), ("auth", "token"), ("release", "create"), ("release", "upload"),
    ("release", "edit"), ("release", "delete"), ("repo", "delete"), ("repo", "edit"),
    ("repo", "archive"), ("repo", "rename"), ("run", "rerun"),
}  # fmt: skip
KEYWORDS = {"{", "}", "!", "if", "then", "else", "elif", "fi", "do", "done", "while", "until"}
DEFAULT_BRANCHES = {"main", "master"}
GIT_VALUE_FLAGS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
# Wrapper flags that take a value (a value left unlisted is read as the command: see the README).
WRAPPER_VALUE_FLAGS = {
    "env": {"-u", "--unset", "-C", "--chdir"},
    "sudo": {"-u", "-g", "-h", "-p", "-C", "-D", "-r", "-t", "-U", "-T", "-R"},
    "nice": {"-n", "--adjustment"},
    "xargs": {"-n", "-I", "-d", "-P", "-L", "-E", "-s", "-a"},
    "stdbuf": {"-i", "-o", "-e"},
    "timeout": {"-s", "--signal", "-k", "--kill-after"},
}  # fmt: skip
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
        name = os.path.basename(word)
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", word) or word in KEYWORDS:
            argv = argv[1:]
        elif name in WRAPPERS:
            argv = argv[1:]
            valued = WRAPPER_VALUE_FLAGS.get(name, set())
            while argv and (argv[0].startswith("-") or re.fullmatch(r"[A-Za-z_]\w*=.*", argv[0])):
                flag = argv[0]
                if name == "env" and (flag == "-S" or flag.startswith("--split-string")):
                    # env -S 'cmd args': the string is the command line
                    rest = flag.partition("=")[2] if "=" in flag else (argv[1] if argv[1:] else "")
                    skip = 1 if "=" in flag else 2
                    return strip_wrappers([*shlex.split(rest), *argv[skip:]])
                argv = argv[2:] if flag in valued else argv[1:]
            if name == "timeout" and argv:
                argv = argv[1:]  # the duration
        else:
            break
    return argv


def gh_args(argv: list[str]) -> list[str]:
    """argv after `gh` with the global value flags (`--repo` ...) removed wherever they stand."""
    rest, out, i = argv[1:], [], 0
    while i < len(rest):
        name = rest[i].partition("=")[0]
        if name in GH_VALUE_FLAGS:
            i += 1 if "=" in rest[i] else 2
        else:
            out.append(rest[i])
            i += 1
    return out


def bare_words(args: list[str]) -> list[str]:
    """Words that are not flags and not the free-text value of a text flag."""
    out, previous = [], ""
    for a in args:
        if not a.startswith("-") and previous not in TEXT_FLAGS:
            out.append(a)
        previous = a
    return out


OWNER_MERGE = re.compile(r"owner-merge\.yml")
PR_FIELD = re.compile(r"pr=[0-9]{1,9}")


def check_gh_workflow(argv: list[str], words: list[str]) -> None:
    """`gh workflow`: an allowlist (#333). The one dispatch an agent may run is exactly
    `gh workflow run owner-merge.yml -f pr=<digits>` (or `--field`): no `--ref`, no other flag,
    no other workflow name, ID, display name or path. The check reads the raw words, so a flag
    placed anywhere (`gh -R x workflow run`, `--ref b owner-merge.yml`) fails the exact match."""
    sub = words[1] if len(words) > 1 else ""
    if sub in {"list", "view"}:
        return
    exact = (
        len(argv) == 6
        and argv[1:3] == ["workflow", "run"]
        and OWNER_MERGE.fullmatch(argv[3])
        and argv[4] in {"-f", "--field"}
        and PR_FIELD.fullmatch(argv[5])
    )
    if not exact:
        raise Deny(
            "`gh workflow` may only run exactly `gh workflow run owner-merge.yml -f pr=<n>` "
            "(or list/view); any other dispatch, flag, `--ref` or workflow is denied"
        )


def check_gh_api(args: list[str]) -> None:
    for word in args[1:]:
        low = word.lower().strip("/")
        if re.search(r"(^|/)dispatches(/|$|\?)|actions/workflows", low):
            raise Deny(
                "`gh api` to a dispatches or actions/workflows endpoint can start a workflow"
            )
    if any(w.lower().strip("/") == "graphql" for w in args[1:]):
        raise Deny("`gh api graphql` can mutate; use `gh pr` or `gh issue`")
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


def check_shell(head: str, argv: list[str], prefixes, paths) -> None:
    """`bash -c "<script>"` (also `-lc`, `-xc`), `eval <words>`, `bash script.sh`. A shell that
    reads its script from stdin, a pipe or a here-string cannot be checked: deny it."""
    if head == "eval":
        check(" ".join(argv[1:]), prefixes, paths)
        return
    if any(a in {"<<<", "<<", "<"} for a in argv[1:]):
        raise Deny("a shell fed from a here-string, heredoc or file cannot be checked")
    flagged = [i for i, a in enumerate(argv[1:], 1) if re.fullmatch(r"-[A-Za-z]*c[A-Za-z]*", a)]
    if flagged:
        inner = flagged[0] + 1
        if inner >= len(argv):
            raise Deny("`-c` without a script")
        check(argv[inner], prefixes, paths)
        return
    rest = [a for a in argv[1:] if not a.startswith("-")]
    if not rest:
        raise Deny("a shell reading its script from stdin cannot be checked")
    check_argv(rest, prefixes, paths)


def check_git(argv: list[str]) -> None:
    """`git push` may not name the default branch (or push everything); no alias settings."""
    args, i, sub = argv[1:], 0, None
    if any(a.lower().startswith("alias.") or ".alias." in a.lower() for a in args):
        raise Deny("git aliases can hide any command")
    while i < len(args):
        if args[i] in GIT_VALUE_FLAGS:
            i += 2
        elif args[i].startswith("-"):
            i += 1
        else:
            sub = args[i]
            break
    if sub != "push":
        return
    rest = args[i + 1 :]
    if any(a in {"--all", "--mirror", "--tags-all"} for a in rest):
        raise Deny("`git push --all/--mirror` would push the default branch")
    words = [a for a in rest if not a.startswith("-")]
    for ref in words[1:]:  # words[0] is the remote
        dest = ref.rpartition(":")[2] if ":" in ref else ref
        dest = dest.removeprefix("refs/heads/").lstrip("+")
        if dest in DEFAULT_BRANCHES:
            raise Deny("the engineer never pushes to the default branch; open a pull request")


def check_argv(argv: list[str], prefixes: list[list[str]], paths: list[re.Pattern[str]]) -> None:
    original = argv
    argv = strip_wrappers(argv)
    if not argv:
        return
    head = os.path.basename(argv[0])
    if argv[0].startswith("$"):
        raise Deny("a command named by a variable cannot be checked")
    if head in SHELLS or head == "eval":
        check_shell(head, argv, prefixes, paths)
    if head == "git":
        check_git(argv)
    candidates = [argv]
    if head == "gh":
        args = gh_args(argv)
        candidates = [["gh", *args]]
        words = bare_words(args)
        for banned in GH_ALWAYS:
            if tuple(words[: len(banned)]) == banned:
                raise Deny(f"`gh {' '.join(banned)}` is not the engineer's")
        if args[:1] == ["api"]:
            check_gh_api(args)
        if words[:1] == ["workflow"]:
            if len(original) != len(argv):  # `GH_REPO=o/r gh ...`, `env GH_HOST=h gh ...`
                raise Deny("`gh workflow` may not run behind env assignments or wrappers")
            check_gh_workflow(argv, words)
        # `gh pr --repo o/r merge`, `gh pr merge --squash 5`: the group first, the verb anywhere
        for prefix in prefixes:
            if prefix[0] == "gh" and len(prefix) > 1 and words[:1] == prefix[1:2]:
                if all(w in words[1:] for w in prefix[2:]):
                    raise Deny(f"`{' '.join(prefix)}` is denied by settings.json")
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


def substitutions(word: str) -> list[str]:
    """The text of each `$(...)` and backtick substitution left inside a (quoted) word."""
    found, i = [], 0
    while (i := word.find("$(", i)) != -1:
        depth, j = 1, i + 2
        while j < len(word) and depth:
            depth += {"(": 1, ")": -1}.get(word[j], 0)
            j += 1
        found.append(word[i + 2 : j - 1])
        i = j
    found += re.findall(r"`([^`]*)`", word)
    return found


def check(command: str, prefixes: list[list[str]], paths: list[re.Pattern[str]]) -> None:
    for inner in re.findall(r"`([^`]*)`", command):  # before segments() splits on backticks
        check(inner, prefixes, paths)
    for argv in segments(command):
        for word in argv:
            for inner in substitutions(word):
                check(inner, prefixes, paths)
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
