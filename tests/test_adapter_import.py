"""`CLAUDE.md` must import the rules mechanically, not point at them in prose (#53).

`.trazo/rules.md` is the tool-neutral core and `CLAUDE.md` is the Claude Code adapter. The
adapter originally pointed at the rules with a markdown link and then **restated seven of
them**, which is the failure this framework exists to prevent: two copies drift, and the
copy an agent reads is whichever it happened to load. Issue #53 put it bluntly —

    "A line reading 'read .trazo/rules.md' is an instruction the agent may skip, and costs
     a tool call when it complies. That is the same advisory-versus-mechanical failure this
     framework exists to prevent."

Issue #38 then verified the mechanical form: a one-line root `CLAUDE.md` containing
`@.trazo/rules.md` is inlined at load, with zero tool calls, runtime-tested on Claude Code
2.1.284. So the adapter uses the import.

The import **fails open**, and that is the part worth pinning. #38 measured it: a missing
or mistyped target produces no error, no warning, and exit 0 — the session simply runs
with no rules at all. A typo, a sparse checkout missing `.trazo/`, or a bad merge all
degrade silently to an ungoverned agent. #38 called a resolution check **mandatory**, so
these tests are that check.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
RULES = REPO_ROOT / ".trazo" / "rules.md"

# A bare `@path` on its own line is the import form. A prose mention of the path inside a
# sentence is not, which is why this looks at line shape rather than searching for a path.
IMPORT_RE = re.compile(r"^@(?P<path>\S+)$", re.MULTILINE)


def _imports(text: str) -> list[str]:
    return [m.group("path") for m in IMPORT_RE.finditer(text)]


def test_claude_md_imports_the_rules_rather_than_pointing_at_them():
    """The adapter gets the rules by import, inlined at load with no tool call."""
    imports = _imports(CLAUDE_MD.read_text(encoding="utf-8"))
    assert ".trazo/rules.md" in imports, (
        "CLAUDE.md must import the rules with a bare `@.trazo/rules.md` line; "
        f"found imports: {imports}"
    )


def test_every_import_target_resolves_on_disk():
    """The fail-open guard #38 called mandatory.

    An unresolvable import is silent: no error, no warning, exit 0, and the agent runs with
    no rules at all. Nothing else in CI would notice, because the file it fails to read is
    not referenced by anything that executes.
    """
    text = CLAUDE_MD.read_text(encoding="utf-8")
    missing = [path for path in _imports(text) if not (REPO_ROOT / path).is_file()]
    assert not missing, (
        f"CLAUDE.md imports {missing}, which do not exist. An import that does not resolve "
        "is a SILENT failure: the session runs with no rules and nothing reports it (#38)."
    )


def test_the_imported_rules_are_the_real_rules_not_a_stub():
    """Presence is not enough — the target must carry content.

    A file that exists but has been emptied or truncated to a header would satisfy the
    check above while leaving the agent ungoverned, which is the same silent failure one
    step removed. #38 recommended a sentinel for exactly this reason.
    """
    rules = RULES.read_text(encoding="utf-8")
    assert "Trazo rules" in rules, (
        ".trazo/rules.md has lost its title; the import would resolve to a file that "
        "states no rules"
    )
    headings = re.findall(r"^## (.+)$", rules, re.MULTILINE)
    assert len(headings) >= 10, (
        f".trazo/rules.md has only {len(headings)} rules ({headings}); the import target "
        "looks gutted even though it resolves"
    )


def test_the_adapter_does_not_restate_the_rules():
    """The duplication that made the adapter advisory in the first place.

    The old CLAUDE.md carried its own numbered 'Standing rules' list covering branches,
    verification, measurement, safety limits, guessing and the skeptic gate — all already
    in `.trazo/rules.md`. Two copies is the failure mode, so assert it has not come back.
    """
    claude = CLAUDE_MD.read_text(encoding="utf-8")
    assert not re.search(r"^##\s+Standing rules", claude, re.MULTILINE), (
        "CLAUDE.md has a 'Standing rules' section again. Those rules live in "
        ".trazo/rules.md; restating them here is how they drift."
    )
    # A numbered list under any heading reintroduces the same copy-paste shape.
    assert not re.search(r"^\d+\.\s+\*\*", claude, re.MULTILINE), (
        "CLAUDE.md has a numbered bolded rule list again. Rules are imported, not copied; "
        "use the 'How this tool satisfies the rules' table to point at where each is met."
    )


def test_the_adapter_only_binds_what_is_claude_specific():
    """Whatever the adapter says about a rule must be a binding, not a second statement.

    The table maps each rule to where Claude Code answers it. It must not re-assert the
    rule's content, or the adapter drifts in exactly the way this change removed.
    """
    claude = CLAUDE_MD.read_text(encoding="utf-8")
    assert "How this tool satisfies the rules" in claude, (
        "the adapter must still say how this tool satisfies the imported rules"
    )
    for marker in (".claude/agents/", "gh pr review --comment", ".trazo/project/SKEPTIC_BAR.md"):
        assert marker in claude, (
            f"{marker} is the Claude-specific binding the adapter exists to carry; it is gone"
        )


def test_the_subdirectory_hazard_is_documented():
    """#38's other verified finding, and a trap for the next session.

    From a subdirectory the import arrives unexpanded. Nothing errors; the agent simply
    gets an `@` line it may ignore. The adapter says so at the top, where a session
    landing in this repo will read it.
    """
    claude = CLAUDE_MD.read_text(encoding="utf-8")
    assert re.search(r"repository root", claude, re.IGNORECASE), (
        "CLAUDE.md must warn that imports only resolve from the repository root (#38)"
    )


def test_the_adapters_a_host_receives_point_at_a_path_a_host_also_has():
    """`src/adapters/` is what a host is handed, and it must name `.trazo/rules.md` (#96).

    That path is identical here and in a host, which is what keeps `src/` a pure build
    input: an adapter that named `src/overlay/rules.md` would point a host at a directory
    it does not have. `CLAUDE.md` imports the file (`@`); `AGENTS.md` names it, since not
    every tool expands an import. The Claude import must also resolve (silent failure, #38).
    """
    claude = (REPO_ROOT / "src/adapters/CLAUDE.md").read_text(encoding="utf-8")
    agents = (REPO_ROOT / "src/adapters/AGENTS.md").read_text(encoding="utf-8")
    imports = _imports(claude)
    assert ".trazo/rules.md" in imports, f"src/adapters/CLAUDE.md must import the rules: {imports}"
    missing = [i for i in imports if not (REPO_ROOT / i).is_file()]
    assert not missing, f"src/adapters/CLAUDE.md imports {missing}, which do not exist (#38)"
    assert ".trazo/rules.md" in agents, "src/adapters/AGENTS.md must point at .trazo/rules.md"
    for name, text in (("CLAUDE.md", claude), ("AGENTS.md", agents)):
        assert "src/overlay/rules.md" not in text, (
            f"src/adapters/{name} names a src/ path; a host has no src/"
        )


def test_agents_adapter_routes_plain_english_to_codex_workflows():
    """A Codex host should reach the same workflows without memorizing commands (#156)."""
    agents = (REPO_ROOT / "src/adapters/AGENTS.md").read_text(encoding="utf-8")
    for route in (
        "Work on issue 12",
        "`trazo-work`",
        "`trazo-start`",
        "`trazo-check-pr`",
        "`trazo-pm`",
        "`.agents/skills/`",
        "`.codex/agents/`",
    ):
        assert route in agents, f"AGENTS.md must route plain-English requests: missing {route}"
    assert "Do not answer with a command for the owner to run" in agents


# Words and shapes that are true of one repository's build, tests or docs and so are false
# in a host. The shipped adapter is written into a host's own file (#133), where a claim
# like `make setup` or "Baseline: 132 passed" would be an instruction about a codebase the
# adapter knows nothing about. Trazo governs whether; the host's own notes say how.
REPO_SPECIFIC = {
    "a make target": re.compile(r"`make\s+\w|^\s+make\s+\w", re.MULTILINE),
    "a test count": re.compile(r"\b\d+\s+(?:passed|skipped|failed|tests?)\b", re.IGNORECASE),
    "a test baseline": re.compile(r"\bbaseline\b", re.IGNORECASE),
    "the handbook": re.compile(r"\bhandbook/"),
    "a docs build": re.compile(r"\b(?:mkdocs|pytest|ruff|uv run)\b"),
    "a repo script": re.compile(r"\bscripts/\S+"),
    "a docs location": re.compile(r"(?<![\w.])docs/"),
}


def test_the_shipped_adapters_make_no_claim_about_a_hosts_build_tests_or_docs():
    """The block a host receives is governance only (#133)."""
    found = []
    for name in ("AGENTS.md", "CLAUDE.md"):
        text = (REPO_ROOT / "src/adapters" / name).read_text(encoding="utf-8")
        for what, pattern in REPO_SPECIFIC.items():
            for m in pattern.finditer(text):
                found.append(f"src/adapters/{name}: {what}: {m.group(0)!r}")
    assert not found, (
        "the shipped adapters carry claims true only of this repository; put them in the "
        "root AGENTS.md outside the trazo markers:\n" + "\n".join(found)
    )
