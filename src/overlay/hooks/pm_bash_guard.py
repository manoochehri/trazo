#!/usr/bin/env python3
"""PreToolUse hook for the `pm` agent's Bash tool (issue #279).

The PM reads and files issues. It never deploys, merges, pushes or sets a secret. Prompt text
does not hold that line, so this hook does: it is an allowlist of exact argument shapes, and
anything it does not recognise is blocked.

Contract (Claude Code hooks): the call arrives as JSON on stdin with `tool_input.command` and,
inside a subagent, `agent_type`. Exit 0 allows (permission deny rules still win), exit 2 blocks
and stderr is the reason. Any error blocks: the hook fails closed.

    pm_bash_guard.py              enforce for every caller (the pm agent's frontmatter hook)
    pm_bash_guard.py --agent pm   enforce only when agent_type == "pm" (the settings.json hook,
                                  which also runs in `-p` sessions and under a trusted parent)

Allowed: read-only `git` and `gh` with known flags, `gh issue create|comment|edit|close|reopen`
and `gh label create|edit` with a fixed flag set (#378), and stdin-only
filters after a pipe. No file arguments to filters, no `--body-file`
(the PM has no file-write tool, so any path is a secret or repo content), no `gh auth`, no
`gh api` beyond `repos/<o>/<r>/...` reads and the milestone create/edit (#396), no glob
characters, no absolute or `..` paths for git.
"""

import json
import re
import sys

REASON = (
    "pm hook: {why}. The PM may run read-only git and gh, `gh issue create|comment|edit|close|"
    "reopen` and `gh label create|edit`. "
    "Deploys, merges, pushes and secrets are not its to run (issue #279)."
)

FILTERS = {  # command -> (flags, flags that take a value, max positionals)
    "head": (set(), {"-n", "-c"}, 0),
    "tail": (set(), {"-n", "-c"}, 0),
    "wc": ({"-l", "-w", "-c", "-m"}, set(), 0),
    "cut": (set(), {"-d", "-f", "-c"}, 0),
    "tr": ({"-d", "-s", "-c"}, set(), 2),
    "grep": (
        {"-i", "-v", "-c", "-n", "-E", "-F", "-w", "-o", "-x", "-q"},
        {"-m", "-A", "-B", "-C"},
        1,  # the pattern; there is no file operand, and -e/-f/-r are not allowed
    ),
    "jq": (
        {"-r", "-c", "-e", "-s", "-j", "-M", "-S", "--tab", "--raw-output", "--compact-output",
         "--slurp", "--exit-status"},
        set(),
        1,  # the program; -f, --rawfile, --slurpfile and file operands are not allowed
    ),
}  # fmt: skip

GIT_READ = {
    "status", "log", "diff", "show", "rev-parse", "rev-list", "ls-files", "ls-tree",
    "blame", "describe", "shortlog", "cat-file", "merge-base", "branch", "tag", "remote",
    "fetch",
}  # fmt: skip
GIT_BAD_FLAGS = (
    "--output", "--upload-pack", "--receive-pack", "--exec", "--ext-diff", "--no-index",
    "--open-files-in-pager",
)  # fmt: skip
GIT_BRANCH_FLAGS = {"--show-current", "-a", "-r", "-v", "-vv", "--list", "-l", "--all", "--remotes"}
GIT_BRANCH_TAKES_VALUE = {"--contains", "--merged", "--no-merged", "--list", "-l"}
GIT_FETCH_FLAGS = {"--prune", "-p", "--tags", "-q", "--quiet", "--all"}
REMOTE_NAME = re.compile(r"^[A-Za-z0-9._-]+$")

GH_READ_FLAGS = {
    "--json", "--jq", "-q", "--limit", "-L", "--state", "-s", "--label", "-l", "--search", "-S",
    "--assignee", "-a", "--author", "-A", "--milestone", "-m", "--base", "-B", "--head", "-H",
    "--app", "--draft", "-d", "--log", "--log-failed", "--job", "-j", "--attempt", "--branch",
    "-b", "--event", "-e", "--workflow", "-w", "--status", "--user", "-u", "--commit", "-c",
    "--name-only", "--patch", "--color", "--exit-status", "--required", "--comments",
    "--mention",
}  # fmt: skip
GH_SEARCH_FLAGS = GH_READ_FLAGS | {
    "--repo", "--owner", "--sort", "--order", "--match", "--language", "--created", "--updated",
    "--visibility", "--include-prs",
}  # fmt: skip
GH_READ = {
    "issue": {"view", "list", "status"},
    "pr": {"view", "list", "diff", "checks", "status"},
    "run": {"view", "list"},
    "repo": {"view"},
    "release": {"view", "list"},
    "label": {"list"},
    "workflow": {"list", "view"},
    "search": {"issues", "prs", "code", "repos", "commits"},
}
GH_API_FLAGS = {"--jq", "-q", "--paginate"}
GH_API_ENDPOINT = re.compile(r"^repos/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(/[A-Za-z0-9_.-]+)*$")
# (command, subcommand) -> (flags that take a value, flags that do not)
GH_WRITE = {
    ("issue", "create"): (
        {"--title", "-t", "--body", "-b", "--label", "-l", "--milestone", "-m", "--assignee", "-a"},
        set(),
    ),
    ("issue", "comment"): ({"--body", "-b"}, set()),
    ("issue", "close"): ({"--comment", "-c", "--reason", "-r"}, set()),
    ("issue", "reopen"): ({"--comment", "-c"}, set()),
    ("label", "create"): ({"--color", "-c", "--description", "-d"}, {"--force", "-f"}),
    ("label", "edit"): ({"--color", "-c", "--description", "-d", "--name", "-n"}, set()),
    ("issue", "edit"): (
        {"--add-label", "--remove-label", "--add-assignee", "--remove-assignee", "--milestone",
         "--title", "-t", "--body", "-b"},
        {"--remove-milestone"},
    ),
}  # fmt: skip
# The one `gh api` write the PM has (#396): create or edit a milestone, nothing else.
MILESTONE_FIELDS = {"title", "description", "due_on", "state"}
MILESTONE_STATES = {"open", "closed"}
MILESTONE_ENDPOINT = re.compile(
    r"^repos/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/milestones(?:/([0-9]+))?$"
)
STOP_LABELS = {"needs-decision", "drive-halt"}  # the owner and the halt switch lift these

# Words that are free text or a program, not paths: not scanned for secret paths.
TEXT_FLAGS = {"--body", "-b", "--title", "-t", "--jq", "-q", "--search", "-S"}
SECRET_PATH = re.compile(
    r"(^|/|:)(\.env|secrets(/|$)|\.ssh|\.aws|\.netrc|\.npmrc|\.config/gh|id_rsa|credentials)"
    r"|\.(pem|key)$",
    re.IGNORECASE,
)
# jq can print the environment or read files: refuse those builtins in any jq program.
JQ_BAD = re.compile(
    r"\benv\b|\$ENV|\binput_filename\b|\$__|\bimport\b|\binclude\b|\bget_search_list\b"
    r"|\bmodulemeta\b|\binput_line_number\b"
)
JQ_FLAGS = {"--jq", "-q"}
JQ_INLINE = ("--jq=", "-q=")  # the flag and its program in one word
UNQUOTED_BAD = "\n\r;&<>(){}`$\\*?[]~!"
GIT_BAD_CHARS = set("*?[]{}~\\")


class Deny(Exception):
    pass


def split_segments(cmd: str) -> list[list[str]]:
    """Split on unquoted `|` into segments of words. Refuse any other unquoted shell syntax
    or glob character, and substitution or variables even inside double quotes."""
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
            elif c == "`" or (c == "$" and re.match(r"[A-Za-z_(\{@*#?!$-]", cmd[i + 1 : i + 2])):
                raise Deny("substitution and variables are not allowed")
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
        elif c in UNQUOTED_BAD:
            raise Deny(f"unquoted shell syntax or glob {c!r} is not allowed")
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


def _git_path_ok(word: str) -> None:
    if word.startswith(("/", "~", ":")) or GIT_BAD_CHARS & set(word):
        raise Deny(f"git argument {word!r} is not a plain repository path or revision")
    if ".." in re.split(r"[/:]", word):
        raise Deny("git paths may not climb out of the repository")


def check_git(args: list[str]) -> None:
    if not args or args[0] not in GIT_READ:
        raise Deny(f"`git {args[0] if args else ''}` is not a read-only git command")
    sub, rest = args[0], args[1:]
    prev = ""
    for a in rest:
        if a.startswith("-O"):
            raise Deny("git -O reads an arbitrary file")
        if a.startswith("--"):
            name = a.partition("=")[0]
            # git accepts unambiguous abbreviations, so a prefix of a bad flag is bad too.
            if len(name) >= 3 and any(
                b.startswith(name) or name.startswith(b) for b in GIT_BAD_FLAGS
            ):
                raise Deny(f"git flag {a} can write, run code or read outside the repository")
            value = a.partition("=")[2]
            if value:
                _git_path_ok(value)
        elif not a.startswith("-"):
            _git_path_ok(a)
            if sub == "fetch" and not REMOTE_NAME.match(a):
                raise Deny("`git fetch` takes only a remote or branch name")
        if sub == "branch" and a not in GIT_BRANCH_FLAGS and prev not in GIT_BRANCH_TAKES_VALUE:
            raise Deny("`git branch` is read-only here (list flags only)")
        if sub == "fetch" and a.startswith("-") and a not in GIT_FETCH_FLAGS:
            raise Deny(f"git fetch flag {a} is not allowed")
        prev = a
    if sub == "tag" and rest and rest[0] not in {"-l", "--list"}:
        raise Deny("`git tag` is read-only here (-l only)")
    if sub == "remote" and any(a != "-v" for a in rest):
        raise Deny("`git remote` allows only -v")


def _flags_ok(args: list[str], allowed: set[str], what: str) -> None:
    for a in args:
        if a.startswith("-") and a.partition("=")[0] not in allowed:
            raise Deny(f"{what} flag {a} is not granted to the PM")
        if a.startswith(("/", "~")) or ".." in a.split("/"):
            raise Deny(f"{what} argument {a!r} is not a plain name or number")


def check_gh_write(key: tuple[str, str], args: list[str]) -> None:
    valued, plain = GH_WRITE[key]
    i = 0
    while i < len(args):
        a = args[i]
        i += 1
        if not a.startswith("-"):
            if key[0] == "label" and a.strip().lower() in STOP_LABELS:
                raise Deny(f"the PM may not redefine {a!r}; only the owner changes the stop labels")
            if a.startswith(("/", "~")) or ".." in a.split("/"):
                raise Deny("gh argument is not a plain issue number or URL")
            continue
        name, eq, inline = a.partition("=")
        if name in plain and not eq:
            continue
        if name not in valued:
            raise Deny(f"gh flag {a} is not granted to the PM (no --body-file: use --body)")
        if eq:
            value = inline
        elif i < len(args):
            value = args[i]
            i += 1
        else:
            raise Deny(f"{name} needs a value")
        if key[0] == "label" and name in {"--name", "-n"} and value.strip().lower() in STOP_LABELS:
            raise Deny(f"the PM may not rename a label to {value!r}")
        if name == "--remove-label":
            lifted = {v.strip().lower() for v in value.split(",")} & STOP_LABELS
            if lifted:
                raise Deny(f"the PM may not remove {sorted(lifted)}; only the owner lifts them")


def check_gh_api_milestone(args: list[str]) -> None:
    """`gh api -X POST repos/<o>/<r>/milestones` or `-X PATCH .../milestones/<number>`, with
    only title, description, due_on and state as `-f`/`-F key=value`. Every part is literal
    and exact: no `--input`, no `@file` value, no encoded or computed path, no other flag
    (`-X=PATCH`, `-iX`, `--method` and lowercase methods all fall out as unknown shapes)."""
    method, endpoint, fields = None, None, []
    i = 1  # args[0] is "api"
    while i < len(args):
        a = args[i]
        i += 1
        if a in {"-X", "-f", "-F"}:
            if i >= len(args):
                raise Deny(f"{a} needs a value")
            value = args[i]
            i += 1
            if a == "-X":
                if method is not None:
                    raise Deny("`gh api` takes one -X method")
                method = value
            else:
                key, eq, val = value.partition("=")
                if not eq or key not in MILESTONE_FIELDS:
                    raise Deny("a milestone write may set only title, description, due_on, state")
                if val.startswith("@"):
                    raise Deny("a `gh api` field value may not be read from a file (@)")
                fields.append((key, val))
        elif a.startswith("-"):
            raise Deny(f"`gh api` flag {a} is not granted to the PM for a milestone write")
        elif endpoint is None:
            endpoint = a
        else:
            raise Deny("`gh api` milestone write takes one endpoint")
    match = MILESTONE_ENDPOINT.match(endpoint or "")
    if not match or {".", ".."} & set(match.groups()[:2]):
        raise Deny("a milestone write targets repos/<owner>/<repo>/milestones[/<number>], literal")
    number = match.group(3)
    if (method, bool(number)) not in {("POST", False), ("PATCH", True)}:
        raise Deny("milestones: -X POST on the collection or -X PATCH on a numbered milestone")
    keys = [k for k, _ in fields]
    if len(set(keys)) != len(keys) or not fields or (method == "POST" and "title" not in keys):
        raise Deny("a milestone write needs unique fields (and a title to create)")
    state = dict(fields).get("state")
    if state is not None and state not in MILESTONE_STATES:
        raise Deny("a milestone state is open or closed")


def check_gh(args: list[str]) -> None:
    if len(args) < 2 or args[0].startswith("-"):
        raise Deny("unrecognised gh command")
    cmd, sub, rest = args[0], args[1], args[2:]
    if cmd == "api":
        endpoints = [a for a in args[1:] if not a.startswith("-")]
        flags = [a for a in args[1:] if a.startswith("-")]
        if any(a.partition("=")[0] not in GH_API_FLAGS for a in flags):
            check_gh_api_milestone(args)  # the only write; denies anything else
            return
        if any(a.partition("=")[0] not in GH_API_FLAGS for a in flags):
            raise Deny("`gh api` is read-only here (--jq and --paginate only)")
        if (
            len(endpoints) < 1
            or not GH_API_ENDPOINT.match(endpoints[0])
            or ".." in endpoints[0].split("/")
        ):
            raise Deny("`gh api` is limited to repos/<owner>/<repo>/... endpoints")
        return
    if sub in GH_READ.get(cmd, ()):
        _flags_ok(rest, GH_SEARCH_FLAGS if cmd == "search" else GH_READ_FLAGS, f"gh {cmd} {sub}")
        return
    if (cmd, sub) in GH_WRITE:
        check_gh_write((cmd, sub), rest)
        return
    raise Deny(f"`gh {cmd} {sub}` is not granted to the PM")


def check_filter(head: str, args: list[str]) -> None:
    flags, valued, max_pos = FILTERS[head]
    positionals = 0
    i = 0
    while i < len(args):
        a = args[i]
        i += 1
        name = a.partition("=")[0]
        if head in {"head", "tail"} and re.fullmatch(r"-\d+", a):
            continue
        if a.startswith("-") and a != "-":
            if name in flags:
                continue
            if name in valued:
                if "=" not in a:
                    i += 1  # its value
                continue
            raise Deny(f"`{head}` flag {a} is not allowed (filters read stdin only)")
        positionals += 1
        if positionals > max_pos:
            raise Deny(f"`{head}` may not be given file arguments")


def check(command: str) -> None:
    for index, argv in enumerate(split_segments(command)):
        head, args = argv[0], argv[1:]
        # Free text and programs may mention secret paths; every other word may not name one.
        prev = ""
        for a in args:
            inline = a.startswith(JQ_INLINE)
            program = a.partition("=")[2] if inline else a
            if (head == "jq" or prev in JQ_FLAGS or inline) and JQ_BAD.search(program):
                raise Deny("jq programs may not read the environment or files")
            if prev not in TEXT_FLAGS and SECRET_PATH.search(a):
                raise Deny("a secret path is not readable by the PM")
            prev = a
        if index == 0:
            if head == "git":
                check_git(args)
            elif head == "gh":
                check_gh(args)
            else:
                raise Deny(f"`{head}` is not an allowed command")
        elif head in FILTERS:
            check_filter(head, args)
        else:
            raise Deny(f"`{head}` is not an allowed pipe filter")


def main(argv: list[str]) -> int:
    try:
        only = argv[argv.index("--agent") + 1] if "--agent" in argv else None
        payload = json.load(sys.stdin)
        if only is not None and payload.get("agent_type") != only:
            return 0
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
    sys.exit(main(sys.argv[1:]))
