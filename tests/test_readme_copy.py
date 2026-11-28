"""Guards the repository's public-facing copy (#31, #410).

`README.md` is the first thing anyone reads, and for a long time it described a product
that no longer existed. It promised a lesson flywheel (`/template-improve` +
`/template-sync`, both removed in #73), called itself a starter template after the pivot
to a mountable overlay (#0005), and listed `/security` and `/reviewer` as slash commands
when decision 0003 made them subagent-only.

None of that failed a build. The same drift the docs site had, in the one file with the
most readers, and the reason it survived is that no guard compared prose to reality.

#410 cut the README to a short front page and moved the long sections to the handbook.
Each assertion that pinned a removed section now points at the handbook page that
carries the same claim, so the protection stays and the README stays short.

So these assert the specific false claims rather than a general vibe:
  - no name and no removed mechanism
  - the overlay leads, not the template
  - the mount-time contract is stated, since it is the one thing a host must supply
  - roles are described correctly (subagent-only vs role-switch), on the handbook page
  - the documented layout matches the real one, on the handbook page
  - install uses `latest` and no release number appears on the front pages
  - every link in the README resolves, and the README stays short
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"
HANDBOOK = REPO_ROOT / "handbook"
VERSION_FILE = REPO_ROOT / ".template" / "VERSION"

# Spelled out so this file's own source does not match its own scan.
OLD_NAME = "sem" + "illa"

MAX_README_LINES = 80


def _text() -> str:
    return README.read_text(encoding="utf-8")


def _handbook(name: str) -> str:
    return (HANDBOOK / name).read_text(encoding="utf-8")


def _current_version() -> str:
    return VERSION_FILE.read_text(encoding="utf-8").strip()


def test_roles_are_described_correctly() -> None:
    """Decision 0003: reviewer/security/skeptic are subagent-only. Listing them as
    slash commands was one of the two things #31 reported. The README no longer lists
    roles; the handbook pages that do must keep the same distinction."""
    text = _text()
    for command in ("/reviewer", "/security", "/skeptic"):
        assert not re.search(rf"[`\"']{re.escape(command)}[`\"',]", text), (
            f"{command} is listed as a command; it is subagent-only"
        )
    roles_page = _handbook("how-it-works.md") + _handbook("use-it.md")
    assert re.search(r"subagent-only", roles_page, re.IGNORECASE), (
        "the handbook must say which agents are subagent-only, not just drop them"
    )
    team = _handbook("how-it-works.md")
    for command in ("/pm", "/eng"):
        assert f"`{command}`" in team, f"{command} is a role command and must be listed"


def test_the_documented_layout_matches_the_real_one() -> None:
    """A layout description is a claim about the repo. The old README block listed `docs/`
    as the charter and `.template/` as 'the template's own memory', both wrong after #50.
    The layout now lives in the in-your-repo page; it must name the entries and they must exist."""
    overlay = _handbook("in-your-repo.md")
    for entry in ("rules.md", "charter/", "adr/", "workstreams/"):
        assert entry in overlay, f"the in-your-repo page omits {entry}"
    for rel in (".trazo/rules.md", ".claude/commands", ".template/CHANGELOG.md"):
        assert (REPO_ROOT / rel).exists(), f"{rel} is documented but does not exist"


def test_the_python_harness_is_not_sold_as_a_requirement() -> None:
    """#51 removed the application placeholder. `src/` is gone, so a "Python" row in
    a feature table would describe something that no longer exists. The language-neutral
    claim now lives on the in-your-repo page."""
    text = _text()
    assert "`src/` layout" not in text, "the src/ layout was removed in #51"
    assert "| **Python** |" not in text, "the README lists Python as a feature of the overlay"
    in_your_repo = _handbook("in-your-repo.md")
    assert "does not pick your language" in in_your_repo, (
        "the overlay's language-neutrality is the claim; state it on the in-your-repo page"
    )


def test_readme_exists_and_leads_with_the_product() -> None:
    assert README.exists(), "README.md is missing"
    lines = _text().splitlines()
    heading = next((ln for ln in lines if ln.startswith("# ")), "")
    assert heading == "# Trazo", f"README's H1 is {heading!r}"


def test_readme_is_a_short_front_page() -> None:
    """#410: the README is a front page. Long sections belong in the handbook."""
    lines = _text().splitlines()
    assert len(lines) < MAX_README_LINES, (
        f"README is {len(lines)} lines; the front page must stay under {MAX_README_LINES}"
    )


def test_no_stale_name_or_removed_mechanism() -> None:
    """The three claims that were false. `sends what it learned back` is the sentence
    that advertised the removed flywheel, so it is pinned rather than paraphrased."""
    text = _text()
    offenders = [
        (i, ln.strip()[:70])
        for i, ln in enumerate(text.splitlines(), 1)
        if re.search(rf"\b{OLD_NAME}\b", ln, re.IGNORECASE)
    ]
    assert not offenders, f"README still names the old project: {offenders}"

    low = text.lower()
    assert "sends what it learned back" not in low, (
        "README still promises an automatic lesson flywheel that #73 removed"
    )
    assert "template-improve" not in low
    assert "template-sync" not in low
    assert "self-improving" not in low, "the old tagline: 'a self-improving template'"


def test_the_readme_leads_with_what_it_adds_not_a_starter_template() -> None:
    """A starter template fixes the empty repo you start from. Trazo is added to the repo you
    already have (#0005), and #428 requires the opening to say what it does and for whom. The
    judgment layer is named on the index page, which the README links first."""
    text = _text()
    opening = "Trazo turns your GitHub repository"
    lead = next((ln for ln in text.splitlines() if ln.startswith(opening)), "")
    assert lead, f"README has no opening sentence that starts {opening!r}"
    assert "template for starting" not in text.lower(), "that is the pre-pivot pitch"
    assert "starter template" not in lead.lower()
    assert "well-managed engineering team" in lead, (
        "the opening must state the outcome: a well-managed engineering team"
    )
    assert "not an editor extension and not a build service" in text, (
        "the README must say what Trazo is not"
    )
    index = _handbook("index.md").lower()
    for concept in ("stop rule", "skeptic", "sample size"):
        assert concept in index, f"the judgment layer omits {concept} on the index page"


def test_the_mount_time_contract_is_stated() -> None:
    """The one thing a mounted repo must supply. Omitting it makes the overlay unusable:
    a reader would not know they need a hermetic one-command test environment."""
    low = _text().lower()
    assert "hermetic" in low, "the mount-time contract is not stated"
    assert "one-command" in low or "one command" in low, "the contract must be one command"
    for option in ("docker", "nix", "devcontainer", "makefile"):
        assert option in low, f"{option} must be named as a valid way to satisfy it"
    assert "install.sh" in low, "mounting an existing repo must be a documented path"


def test_readme_install_uses_latest_and_names_no_release() -> None:
    """#143, #402 and the owner decision on #428: a version in the docs goes stale, so every
    install and upgrade command uses `latest`, which the installer resolves to the highest
    release tag. No release number may appear in the README or on the Home page; the
    changelog page is the only place for one."""
    text = _text()
    assert not re.search(r"\]\(\.?/?\.template/VERSION\)", text), (
        "README links .template/VERSION; link the changelog or releases page instead"
    )
    for name, body in (("README.md", text), ("handbook/index.md", _handbook("index.md"))):
        tokens = sorted(set(re.findall(r"\bv\d+\.\d+\.\d+\b", body)))
        assert not tokens, f"{name} hard-codes a release number: {tokens}"
    install_block = re.search(r"```sh\n(.*?)```", text, re.DOTALL)
    assert install_block, "README has no install command block"
    assert "install.sh install latest" in install_block.group(1), (
        "the install command must run the installer with `latest`"
    )
    assert "upgrade latest --dry-run" in text, "the upgrade prompt must preview with `latest`"
    assert "/trazo/main/scripts/install.sh" in install_block.group(1), (
        "the installer is downloaded from main, which supports `latest`"
    )


def test_readme_status_names_what_is_unverified() -> None:
    """Trazo is early, and the drive workflow, the front-door hook shape and release
    automation have not run live. The README must say so, not imply they work."""
    text = _text()
    status = re.search(
        r"^## Where Trazo stands today\n(.*?)(?=^## )", text, re.DOTALL | re.MULTILINE
    )
    assert status, "README has no 'Where Trazo stands today' section"
    body = status.group(1)
    assert "VERSION" not in body, "the status must not cite .template/VERSION"
    assert "UNVERIFIED" in body, "the status must mark what is unverified"
    low = body.lower()
    assert "drive" in low and "#399" in body, "the drive workflow and its open defect are unnamed"
    assert "front-door" in low and "hook" in low, "the front-door hook is unnamed"
    assert "#366" in body, "the shared-account limit is unnamed"
    assert "release automation" in low, "release automation is unnamed"


def test_readme_links_resolve() -> None:
    """Every relative link in the README must point at a file that exists, so the front
    page never sends a reader to a dead page."""
    text = _text()
    links = re.findall(r"\]\(([^)\s]+)\)", text)
    assert links, "README has no links"
    missing = []
    for target in links:
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        path = target.split("#", 1)[0]
        if not (REPO_ROOT / path).exists():
            missing.append(target)
    assert not missing, f"README links to missing files: {missing}"
    handbook_links = [t for t in links if t.startswith("handbook/")]
    assert len(handbook_links) >= 5, "the README must link the handbook pages it points at"


def test_the_handbook_pages_the_readme_names_exist() -> None:
    for name in ("index", "how-it-works", "in-your-repo", "install", "guardrails", "use-it"):
        assert (HANDBOOK / f"{name}.md").exists(), f"handbook/{name}.md is missing"
