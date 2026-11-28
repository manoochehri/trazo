#!/usr/bin/env python3
"""PreToolUse hook for the Bash tool of every caller except `pm` (issues #330, #378).

The `settings.json` deny rules match command text as written, so a shell could still reach a
merge (`gh api -X PUT .../pulls/N/merge`), a commit status, a ruleset edit or a secret
(`cat .env`). This hook parses the command, resolves the verbs it runs (through `$(...)`,
backticks, heredocs, pipes and redirects) and denies a short blocklist; everything else passes.
The PM is not its business: the PM runs an allowlist (pm_bash_guard.py).

The blocklist is the irreversible or self-governing set (#377): secret and credential reads,
merging (`gh pr merge`, the merge endpoint), commit statuses (except the reviewer's and
security's own), release and tag writes, ruleset / branch-protection / Actions-secret /
collaborator / key / repo-settings edits, workflow dispatch, pushes to the default branch, and
writes to the governance paths `.claude/` and `.trazo/` (outside `.trazo/project/`).
GitHub's own rulesets and CODEOWNERS are the real limits; this hook only refuses the obvious
routes early.

One source: the protected commands and paths are read from `permissions.deny` in the project's
`.claude/settings.json` (`Bash(<prefix> *)` rules and `Read(<glob>)` rules). The rules that file
cannot express (the `gh api` blocklist, governance paths, tags) are code here. If settings.json
is missing, unreadable or carries no Bash and Read rules, the hook denies: it fails closed.

Contract (Claude Code hooks): the call arrives as JSON on stdin with `tool_input.command` and,
inside a subagent, `agent_type`. Exit 0 allows (permission deny rules still win), exit 2 blocks
and stderr is the reason. Any error blocks.

    engineer_bash_guard.py                  enforce for every caller
    engineer_bash_guard.py --skip-agent pm  step aside when agent_type == "pm"

This is a backstop, not a security boundary: a shell can still build a command this parser does
not see (`python -c`, a script it wrote, an obfuscated word). The real fix is an agent token
that cannot merge or set statuses (#320).
"""

from __future__ import annotations

import json
import os
import posixpath
import re
import shlex
import sys
from pathlib import Path
from urllib.parse import unquote

REASON = (
    "engineer guard: {why}. Merging, release and tag writes, commit statuses (other than the "
    "reviewer's and security's own), ruleset, protection, secret and settings edits, governance "
    "paths and secret reads are not the engineer's to do (issues #330, #378). Everything else "
    "through `gh`, `gh api` and `git` is allowed; the Coordinator merges through the gated "
    "workflow."
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
# `gh api` flags that take a value (a value left unlisted would be read as the endpoint).
GH_API_VALUED = {
    "-X", "--method", "-H", "--header", "-f", "-F", "--field", "--raw-field", "--input",
    "--jq", "-q", "--cache", "-t", "--template", "-p", "--preview", "--hostname",
}  # fmt: skip
GH_FIELD_FLAGS = {"-f", "-F", "--field", "--raw-field"}
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
PROTECTED_GH_ENV = {"GH_REPO", "GH_HOST", "GH_TOKEN", "GH_ENTERPRISE_TOKEN"}
ASSIGNMENT = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=.*")
# Flag values that are free text, not paths or commands.
TEXT_FLAGS = {
    "-m", "--message", "--body", "-b", "--title", "-t", "--jq", "-q", "--search", "-S", "--notes",
    "--subject", "--comment",
}  # fmt: skip
# Placeholder config files are meant to be read and edited (".trazo/rules.md": new config goes
# in the env example).
PLACEHOLDER = re.compile(r"\.env\.(example|sample|template|dist)$", re.IGNORECASE)
OPERATORS = {";", "&", "&&", "|", "||", "|&", "(", ")", "\n", ";;", ";&", ";;&", "<(", ">("}
REDIRECTS = {"<", ">", ">>", "<<", "<<<", "<&", ">&", ">|", "&>", "&>>"}
OUTPUT_REDIRECTS = {">", ">>", ">&", ">|", "&>", "&>>"}

# An expanded `$(...)` or backtick span is replaced by this word in the text the parser sees; the
# span itself is checked as its own command. `\x01<index>\x02` names the span.
SUB_MARK = re.compile(r"\$\x01(\d+)\x02")
SUB_WORD = "$\x01{}\x02"
HEREDOC = re.compile(r"<<(-?)[ \t]*(?:'([^']*)'|\"([^\"]*)\"|\\?([A-Za-z0-9_.-]+))")

# A word that is only a project-relative `.claude/` path: no home prefix, no `..`, no empty or
# dot component. The project's own `.claude/` is repo content; `Read(~/.claude/**)` is the home
# directory's. Only this one deny pattern is skipped for such a word (#364).
PROJECT_CLAUDE = re.compile(r"(\./)?\.claude(/[A-Za-z0-9_][A-Za-z0-9_.-]*)*/?")
HOME_CLAUDE_GLOB = "~/.claude/**"
# The auto-memory directory (`~/.claude/projects/<project>/memory/<note>`): notes are written
# there on purpose (#378), no `..`, no nesting.
MEMORY_NOTE = re.compile(
    r"(~|\$HOME|\$\{HOME\}|/Users/[^/]+|/home/[^/]+)/\.claude/projects/[A-Za-z0-9_.-]+/memory/"
    r"[A-Za-z0-9_][A-Za-z0-9_.-]*"
)


class Deny(Exception):
    pass


# The spans of the command being checked, for the read-only test on `gh api` endpoint spans.
_SUBS: list[list[str]] = [[]]
# The calling agent type, set once in main(); only the status carve-out reads it.
_CALLER: list[str | None] = [None]


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


def substitutions(word: str) -> list[str]:
    """The text of each `$(...)` and backtick substitution left inside a block of text."""
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


def scan(command: str) -> tuple[str, list[str]]:
    """Pre-pass over the raw text, quote-aware. Returns the text the word parser sees and the
    list of command spans to check on their own.

    - every `$(...)` and backtick span outside single quotes becomes one placeholder word and is
      listed as a span (checked recursively), so a `$(` in a body or an argument is judged by the
      verbs inside it and never rejected as a construct;
    - heredoc bodies are removed (a quoted delimiter makes the body literal text; an unquoted one
      still expands, so its substitutions are listed as spans);
    - `#` comments are removed.
    """
    out: list[str] = []
    spans: list[str] = []
    pending: list[tuple[str, bool, bool]] = []  # (delimiter, strip tabs, quoted)
    stack: list = []  # int = start of an open `$(`; "par" = a `(` group; "dq" = a double quote
    n, i = len(command), 0

    def in_sub() -> bool:
        return any(isinstance(s, int) for s in stack)

    def emit(text: str) -> None:
        if not in_sub():
            out.append(text)

    def close_span(inner: str) -> None:
        spans.append(inner)
        if not in_sub():
            out.append(SUB_WORD.format(len(spans) - 1))

    while i < n:
        c = command[i]
        top = stack[-1] if stack else None
        if top == "dq" and c == "\\":
            emit(command[i : i + 2])
            i += 2
            continue
        if top == "dq" and c == '"':
            stack.pop()
            emit(c)
            i += 1
            continue
        if c == "`":
            j = i + 1
            while j < n and command[j] != "`":
                j += 2 if command[j] == "\\" else 1
            close_span(command[i + 1 : j])
            i = j + 1
            continue
        if command.startswith("$(", i):
            stack.append(i + 2)
            i += 2
            continue
        if top == "dq":
            emit(c)
            i += 1
            continue
        # command context: top level, `$( )` or `( )`
        if c == "'":
            j = command.find("'", i + 1)
            j = n - 1 if j < 0 else j
            emit(command[i : j + 1])
            i = j + 1
            continue
        if c == "\\":
            emit("" if command[i : i + 2] == "\\\n" else command[i : i + 2])
            i += 2
            continue
        if c == '"':
            stack.append("dq")
            emit(c)
        elif c == "#" and (i == 0 or command[i - 1] in " \t\n;&|()"):
            while i < n and command[i] != "\n":
                i += 1
            continue
        elif c == "(":
            stack.append("par")
            emit(c)
        elif c == ")":
            if isinstance(top, int):
                stack.pop()
                close_span(command[top:i])
            else:
                if top == "par":
                    stack.pop()
                emit(c)
        elif command.startswith("<<<", i):
            emit("<<<")
            i += 3
            continue
        elif command.startswith("<<", i) and (m := HEREDOC.match(command, i)):
            strip, sq, dq, bare = m.groups()
            delim = sq if sq is not None else dq if dq is not None else bare
            quoted = (
                sq is not None or dq is not None or command[m.start() : m.end()].find("\\") >= 0
            )
            pending.append((delim, bool(strip), quoted))
            emit(m.group(0))
            i = m.end()
            continue
        elif c == "\n":
            emit(" ; ")
            i += 1
            for delim, strip, quoted in pending:
                body: list[str] = []
                while i < n:
                    j = command.find("\n", i)
                    j = n if j < 0 else j
                    line = command[i:j]
                    i = min(j + 1, n)
                    if (line.lstrip("\t") if strip else line) == delim:
                        break
                    body.append(line)
                if not quoted and not in_sub():
                    spans.extend(substitutions("\n".join(body).replace("\\$", "")))
            pending.clear()
            continue
        else:
            emit(c)
        i += 1
    for start in [s for s in stack if isinstance(s, int)][:1]:  # an unclosed `$(`
        spans.append(command[start:])
        out.append(SUB_WORD.format(len(spans) - 1))
    return "".join(out), spans


def segments(command: str) -> list[list[str]]:
    """Split into simple commands on operators. Redirect operators stay as words so the file they
    name is scanned."""
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
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


# --- `gh api` -------------------------------------------------------------------------------

DYN = re.compile(r"\$\x01\d+\x02|\$\{[^}]*\}|\$[A-Za-z_][A-Za-z0-9_]*|\$[0-9@*#?!$-]")
MARK = "\x00"
# Path segments that make a write a blocklisted route wherever they stand after `repos/<o>/<r>`.
API_DENY_SEGMENTS = {
    "rulesets", "protection", "hooks", "keys", "gpg_keys", "ssh_signing_keys", "collaborators",
    "invitations", "releases", "environments", "deployments", "merges", "merge", "transfer",
    "dispatches", "actions", "codespaces", "dependabot", "secrets", "variables",
    "rename", "rules", "topics", "pages", "forks", "check-runs", "vulnerability-alerts",
    "interaction-limits", "reviews",
}  # fmt: skip
API_DENY_TOP = {
    "user", "orgs", "enterprises", "applications", "authorizations", "app", "installation", "admin",
    "teams",
}  # fmt: skip
# A write whose path has a computed part is allowed only under one of these collections.
API_DYNAMIC_OK = {"issues", "pulls", "statuses", "milestones", "labels"}
READONLY_INNER = re.compile(
    r"\s*(gh (repo|pr|issue) view|git rev-parse|git remote get-url)(\s[^;&|<>`$()\n\\]*)?"
)
SHA40 = re.compile(r"[0-9a-f]{40}")
STATUS_CONTEXT = {"reviewer": "trazo/verdict", "security": "trazo/security"}
STATUS_STATES = {"success", "failure", "pending", "error"}
STATUS_FIELDS = {"state", "context", "description", "target_url"}


def parse_gh_api(args: list[str]) -> tuple[str, str | None, list[tuple[str, str]], bool]:
    """(method, endpoint, [(field key, value)], uses --input) from the words after `api`."""
    method, endpoint, fields, has_input = "", None, [], False
    i = 1
    while i < len(args):
        a = args[i]
        i += 1
        if "method-override" in a.lower():
            raise Deny("`gh api` method override headers are not allowed")
        if a.startswith("--"):
            name, eq, inline = a.partition("=")
            if name not in GH_API_VALUED:
                continue
            if eq:
                value = inline
            elif i < len(args):
                value, i = args[i], i + 1
            else:
                value = ""
            flag = name
        elif a.startswith("-") and len(a) > 1:
            # a cluster such as `-iX PUT` or `-iXPUT`: the first valued letter takes the rest
            pos = next((k for k in range(1, len(a)) if "-" + a[k] in GH_API_VALUED), None)
            if pos is None:
                continue
            flag, rest = "-" + a[pos], a[pos + 1 :]
            if rest:
                value = rest.lstrip("=") if flag == "-X" else rest
            elif i < len(args):
                value, i = args[i], i + 1
            else:
                value = ""
        else:
            endpoint = endpoint if endpoint is not None else a
            continue
        if flag in {"-X", "--method"}:
            method = value
        elif flag in GH_FIELD_FLAGS:
            key, _, val = value.partition("=")
            fields.append((key, val))
        elif flag == "--input":
            has_input = True
        elif "method-override" in value.lower():
            raise Deny("`gh api` method override headers are not allowed")
    return method, endpoint, fields, has_input


def _readonly_spans(endpoint: str) -> None:
    """A computed part of a write endpoint may only be a read-only lookup (`gh repo view`,
    `gh pr view`, `git rev-parse`) or a shell variable; anything else could build any path."""
    spans = _SUBS[-1]
    for m in SUB_MARK.finditer(endpoint):
        idx = int(m.group(1))
        inner = spans[idx] if idx < len(spans) else ""
        if not READONLY_INNER.fullmatch(inner):
            raise Deny(
                "a computed part of a `gh api` write endpoint may only be a read-only lookup"
            )


def _status_post(effective: str, fields: list[tuple[str, str]], has_input: bool) -> None:
    caller = _CALLER[0]
    if not isinstance(caller, str) or caller not in STATUS_CONTEXT:
        raise Deny("commit statuses are set only by the reviewer and security roles")
    keys = [k for k, _ in fields]
    values = dict(fields)
    if (
        effective != "POST"
        or has_input
        or len(set(keys)) != len(keys)
        or not set(keys) <= STATUS_FIELDS
        or values.get("state") not in STATUS_STATES
        or values.get("context") != STATUS_CONTEXT[caller]
    ):
        raise Deny(
            f"{caller} may post only its own {STATUS_CONTEXT[caller]} status, as a plain POST"
        )


def check_gh_api_write(
    endpoint: str, effective: str, fields: list[tuple[str, str]], has_input: bool
) -> None:
    _readonly_spans(endpoint)
    path = unquote(re.split(r"[?#]", endpoint, maxsplit=1)[0]).strip().lower()
    path = re.sub(r"\{(owner|repo)\}", "x", path)
    path = DYN.sub(MARK, path)
    segs = [s for s in path.strip("/").split("/") if s]
    dynamic = any(MARK in s for s in segs)
    if not segs or any(s in {".", ".."} for s in segs):
        raise Deny("`gh api` write to an unreadable endpoint")
    if MARK in segs[0]:
        raise Deny("a `gh api` write may not start with a computed endpoint")
    if segs[0] in API_DENY_TOP:
        raise Deny(f"`gh api` writes to `{segs[0]}/...` (settings, billing, teams) are not allowed")
    if segs[0] != "repos":
        if any(s in API_DENY_SEGMENTS for s in segs[1:]):
            raise Deny("`gh api` write to a key, secret, release or settings endpoint")
        return
    if not dynamic and len(segs) <= 3:
        raise Deny("`gh api` write to the repository itself (settings, rename, delete)")
    if has_input and "statuses" not in segs:
        raise Deny("`gh api --input` can send any body (a tag ref, a merge); use -f fields")
    scan_from = 1 if dynamic else 3
    if dynamic:
        coll = next((k for k, s in enumerate(segs) if k >= 1 and s in API_DYNAMIC_OK), None)
        if coll is None or coll - 1 > 2:
            raise Deny(
                "a `gh api` write with a computed part must name an issues, pulls, "
                "statuses, milestones or labels collection"
            )
        after = segs[coll + 1 :]
        number_only = segs[coll] in {"milestones", "issues"} and after == [MARK]
        if (
            any(MARK in x for x in after)
            and not number_only
            and not (segs[coll] == "statuses" and len(after) == 1)
        ):
            raise Deny(
                "a `gh api` write may not compute any part of its path after the collection "
                "(a variable can spell `5/merge`); write the path out"
            )
    for s in segs[scan_from:]:
        if s in API_DENY_SEGMENTS:
            raise Deny(
                f"`gh api` write to `{s}`: rulesets, protection, secrets, keys, releases, "
                "collaborators, merges and settings are not the engineer's"
            )
    tail = segs[3:] if not dynamic else segs[1:]
    if "git" in tail:
        refs = "/".join(tail[tail.index("git") + 1 :])
        names = [refs.removeprefix("refs/")] if refs.startswith("refs") else []
        names += [v.removeprefix("refs/") for k, v in fields if k == "ref"]
        if any(MARK in r or re.match(r"(tags(/|$)|heads/(main|master)$)", r) for r in names if r):
            raise Deny("`gh api` writes to tag refs and the default branch are not allowed")
    if "contents" in tail:
        branch = [v for k, v in fields if k == "branch"]
        if not branch or MARK in DYN.sub(MARK, branch[0]) or branch[0].lower() in DEFAULT_BRANCHES:
            raise Deny("`gh api` writes to `contents` need an explicit non-default `branch`")
    if "statuses" in tail:
        k = tail.index("statuses")
        rest = tail[k + 1 :]
        if len(rest) != 1 or not (SHA40.fullmatch(rest[0]) or MARK in rest[0]):
            raise Deny("a status post names exactly one 40-hex sha or a variable")
        _status_post(effective, fields, has_input)


def check_gh_api(args: list[str]) -> None:
    for word in args[1:]:
        low = word.lower().strip("/")
        if re.search(r"(^|/)dispatches(/|$|\?)|actions/workflows", low):
            raise Deny(
                "`gh api` to a dispatches or actions/workflows endpoint can start a workflow"
            )
    if any(w.lower().strip("/") == "graphql" for w in args[1:]):
        raise Deny("`gh api graphql` can mutate; use `gh pr` or `gh issue`")
    method, endpoint, fields, has_input = parse_gh_api(args)
    effective = (method or ("POST" if fields or has_input else "GET")).upper()
    if effective in {"GET", "HEAD"}:
        return
    if endpoint is None:
        raise Deny("`gh api` write without an endpoint")
    check_gh_api_write(endpoint, effective, fields, has_input)


# --- governance-path writes ------------------------------------------------------------------

WRITE_ALL = {"tee", "touch", "truncate", "rm", "mv", "chmod", "chown", "mkdir", "rmdir", "unlink"}
WRITE_DEST = {"cp", "install", "ln", "rsync"}


def governance_path(word: str) -> bool:
    """True for a path under `.claude/` or `.trazo/` that is governance (not `.trazo/project/`
    outside its charter, not a worktree, not a memory note)."""
    if SUB_MARK.search(word):
        return False
    if MEMORY_NOTE.fullmatch(posixpath.normpath(word)):
        return False
    norm = posixpath.normpath(word.replace("$HOME", "~"))
    parts = norm.split("/")
    for k, part in enumerate(parts):
        if part == ".claude":
            return parts[k + 1 : k + 2] != ["worktrees"]
        if part == ".trazo":
            rest = parts[k + 1 :]
            if rest[:1] == ["project"]:
                return rest[1:2] in (["charter"], ["SKEPTIC_BAR.md"])
            return True
    return False


def check_writes(head: str, argv: list[str]) -> None:
    args = argv[1:]
    for k, word in enumerate(args):
        if word in OUTPUT_REDIRECTS and k + 1 < len(args) and governance_path(args[k + 1]):
            raise Deny(f"a redirect into {args[k + 1]!r} writes a governance path")
    args = [
        a
        for k, a in enumerate(args)
        if a not in REDIRECTS and (k == 0 or args[k - 1] not in REDIRECTS)
    ]
    positional = [a for a in args if not a.startswith("-")]
    targets: list[str] = []
    if head in WRITE_ALL:
        targets = positional
    elif head in WRITE_DEST:
        targets = positional[-1:]
        for k, a in enumerate(args):
            if a in {"-t", "--target-directory"} and k + 1 < len(args):
                targets.append(args[k + 1])
            elif a.startswith("--target-directory="):
                targets.append(a.partition("=")[2])
    elif head in {"sed", "perl"} and any(
        re.fullmatch(r"-[A-Za-z]*i[A-Za-z0-9.]*|--in-place(=.*)?", a) for a in args
    ):
        targets = positional
    elif head == "dd":
        targets = [a[3:] for a in args if a.startswith("of=")]
    elif head == "git" and positional[:1] in (["mv"], ["rm"]):
        targets = positional[1:]
    for t in targets:
        if governance_path(t):
            raise Deny(
                f"{t!r} is a governance path (.claude/ or .trazo/); change it through a "
                "reviewed pull request and the Edit tool"
            )


# --- the rest ------------------------------------------------------------------------------


def sets_protected_gh_env(argv: list[str]) -> bool:
    """Return whether a simple command sets a GitHub environment variable for later commands."""
    i = 0
    while i < len(argv):
        word = argv[i]
        match = ASSIGNMENT.fullmatch(word)
        if match:
            if match[1] in PROTECTED_GH_ENV:
                return True
            i += 1
            continue
        if word == "export":
            return any(
                ASSIGNMENT.fullmatch(value or "").group(1) in PROTECTED_GH_ENV
                if ASSIGNMENT.fullmatch(value or "")
                else value in PROTECTED_GH_ENV
                for value in argv[i + 1 :]
                if not value.startswith("-")
            )
        if word == "env":
            i += 1
            continue
        break
    return False


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
    """`git push` may not name the default branch (or push everything or a tag); no alias
    settings. Force-pushing a branch that is not the default is allowed."""
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
    if sub is not None and "$" in sub:
        raise Deny("a `git` subcommand named by a variable or substitution cannot be checked")
    if sub != "push":
        return
    rest = args[i + 1 :]
    if any(a in {"--all", "--mirror", "--tags", "--follow-tags"} for a in rest):
        raise Deny("`git push --all/--mirror/--tags` would push the default branch or a tag")
    words = [a for a in rest if not a.startswith("-")]
    forced = any(a in {"-f", "--force"} or a.startswith("--force-with-lease") for a in rest)
    if forced and (len(words) < 2 or any(w.rpartition(":")[2] == "HEAD" for w in words[1:])):
        # the branch is whatever is checked out, possibly the default one: name it
        raise Deny("a force-push must name the branch it pushes (not none, not HEAD)")
    if len(words) > 1 and words[1] == "tag":
        raise Deny("tags are cut by the release workflow, not pushed from a session")
    for ref in words[1:]:  # words[0] is the remote
        dest = ref.rpartition(":")[2] if ":" in ref else ref
        dest = dest.removeprefix("refs/heads/").lstrip("+")
        if dest in DEFAULT_BRANCHES:
            raise Deny("the engineer never pushes to the default branch; open a pull request")
        if dest.startswith("refs/tags/"):
            raise Deny("tags are cut by the release workflow, not pushed from a session")


def check_argv(argv: list[str], prefixes: list[list[str]], paths: list[re.Pattern[str]]) -> None:
    original = argv
    argv = strip_wrappers(argv)
    if not argv:
        return
    head = os.path.basename(argv[0])
    if argv[0].startswith("$"):
        raise Deny("a command named by a variable or substitution cannot be checked")
    if head in SHELLS or head == "eval":
        check_shell(head, argv, prefixes, paths)
    if head == "git":
        check_git(argv)
    check_writes(head, argv)
    candidates = [argv]
    if head == "gh":
        args = gh_args(argv)
        candidates = [["gh", *args]]
        words = bare_words(args)
        verbs = words[:1] if words[:1] == ["api"] else words[:2]  # `api`'s next word is a path
        if any("$" in w for w in verbs):
            raise Deny("a `gh` subcommand named by a variable or substitution cannot be checked")
        for banned in GH_ALWAYS:
            if tuple(words[: len(banned)]) == banned:
                raise Deny(f"`gh {' '.join(banned)}` is not the engineer's")
        if words[:1] == ["auth"] and any(a in {"--show-token", "-t"} for a in args):
            raise Deny("`gh auth` may not print the token")
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
    home_claude = glob_to_regex(HOME_CLAUDE_GLOB).pattern
    previous = ""
    for raw_word in argv[1:]:
        # `-F body=@.env` and `curl -d @.env` read the named file: scan the path, not the `@`
        word = re.sub(r"(^|=)@", r"\1", raw_word)
        if previous not in TEXT_FLAGS and not PLACEHOLDER.search(word):
            project_claude = PROJECT_CLAUDE.fullmatch(word) is not None
            # Prose that mentions a `.claude` path, and the memory notes, are not reads of the
            # home directory (#378).
            skip_claude = (
                project_claude
                or re.search(r"\s", word) is not None
                or MEMORY_NOTE.fullmatch(posixpath.normpath(word)) is not None
            )
            if any(p.search(word) for p in paths if not (skip_claude and p.pattern == home_claude)):
                raise Deny(f"{word!r} names a secret path")
        previous = raw_word


def check(command: str, prefixes: list[list[str]], paths: list[re.Pattern[str]]) -> None:
    clean, spans = scan(command)
    _SUBS.append(spans)
    try:
        for inner in spans:
            check(inner, prefixes, paths)
        protected_env = False
        parsed = segments(clean)
        stdin_text = any(a in {"<<", "<<<"} for argv in parsed for a in argv)
        for argv in parsed:
            normalized = strip_wrappers(argv)
            lead = argv[: len(argv) - len(normalized)]
            if any(os.path.basename(w) == "xargs" for w in lead):
                target = os.path.basename(normalized[0]) if normalized else ""
                if stdin_text or target in {"gh", "git", "eval", *SHELLS}:
                    # stdin becomes the arguments (`pr merge 5`): they cannot be judged
                    raise Deny("`xargs` may not build `gh`, `git` or shell arguments from stdin")
            if protected_env and normalized and os.path.basename(normalized[0]) == "gh":
                args = gh_args(normalized)
                if bare_words(args)[:1] == ["workflow"]:
                    raise Deny(
                        "`gh workflow` may not follow an earlier protected environment assignment"
                    )
            check_argv(argv, prefixes, paths)
            protected_env = protected_env or sets_protected_gh_env(argv)
    finally:
        _SUBS.pop()


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
        _CALLER[0] = payload.get("agent_type")
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
