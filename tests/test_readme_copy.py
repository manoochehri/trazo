"""Guards the repository's public-facing copy (#31).

`README.md` is the first thing anyone reads, and for a long time it described a product
that no longer existed. It promised a lesson flywheel (`/template-improve` +
`/template-sync`, both removed in #73), called itself a starter template after the pivot
to a mountable overlay (#0005), and listed `/security` and `/reviewer` as slash commands
when decision 0003 made them subagent-only.

None of that failed a build. The same drift the docs site had, in the one file with the
most readers, and the reason it survived is that no guard compared prose to reality.

So these assert the specific false claims rather than a general vibe:
  - no name and no removed mechanism
  - the overlay leads, not the template
  - the mount-time contract is stated, since it is the one thing a host must supply
  - roles are described correctly (subagent-only vs role-switch)
  - the documented layout matches the real one
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"

# Spelled out so this file's own source does not match its own scan.
OLD_NAME = "sem" + "illa"


def _text() -> str:
    return README.read_text(encoding="utf-8")


def test_roles_are_described_correctly() -> None:
    """Decision 0003: reviewer/security/skeptic are subagent-only. Listing them as
    slash commands was one of the two things #31 reported."""
    text = _text()
    for command in ("/reviewer", "/security", "/skeptic"):
        assert not re.search(rf"[`\"']{re.escape(command)}[`\"',]", text), (
            f"{command} is listed as a command; it is subagent-only"
        )
    assert re.search(r"subagent-only", text, re.IGNORECASE), (
        "the README must say which agents are subagent-only, not just drop them"
    )
    for command in ("/pm", "/eng"):
        assert f"`{command}`" in text, f"{command} is a role command and must be listed"


def test_the_documented_layout_matches_the_real_one() -> None:
    """A layout table is a claim about the repo. The old one listed `docs/` as the
    charter and `.template/` as 'the template's own memory', both wrong after #50."""
    text = _text()
    block = re.search(r"## Repository layout\s*```\n(.*?)```", text, re.DOTALL)
    assert block, "no repository-layout block"
    listed = block.group(1)
    for entry in (".trazo/", "rules.md", "charter/", "adr/", ".claude/", ".template/", "project/"):
        assert entry in listed, f"the layout omits {entry}"
    for rel in (".trazo/rules.md", ".claude/commands", ".template/CHANGELOG.md"):
        assert (REPO_ROOT / rel).exists(), f"{rel} is listed in the layout but does not exist"


def test_the_python_harness_is_not_sold_as_a_requirement() -> None:
    """#51 removed the application placeholder. `src/` is gone, so a "Python" row in
    the feature table would describe something that no longer exists."""
    text = _text()
    assert "`src/` layout" not in text, "the src/ layout was removed in #51"
    table = re.search(r"\| Area \| What's included \|.*?\n\n", text, re.DOTALL)
    assert table and "| **Python** |" not in table.group(0), (
        "the feature table still lists Python as a feature of the overlay"
    )
    low = text.lower()
    assert "not python?" in low, "the non-Python case must still be answered"
    assert "nothing in `.trazo/` or `.claude/` assumes a language" in low, (
        "the overlay's language-neutrality is the claim; state it"
    )


def test_readme_exists_and_leads_with_the_product() -> None:
    assert README.exists(), "README.md is missing"
    lines = _text().splitlines()
    heading = next((ln for ln in lines if ln.startswith("# ")), "")
    assert heading == "# Trazo", f"README's H1 is {heading!r}"


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


def test_the_overlay_leads_and_the_judgment_layer_is_named() -> None:
    """A starter template fixes the empty repo you start from. The overlay mounts on the
    one you already have, and the judgment layer is the differentiator per #0005."""
    text = _text()
    tagline = next((ln for ln in text.splitlines()[1:] if ln.strip().startswith("**")), "")
    assert "overlay" in tagline.lower(), "the tagline does not lead with the overlay"
    assert "template for starting" not in tagline.lower(), "that is the pre-pivot pitch"
    assert "any repo" in tagline.lower(), "the whole point is an existing repo"
    for concept in ("stop rule", "skeptic", "sample size"):
        assert concept in text.lower(), f"the judgment layer omits {concept}"


def test_the_mount_time_contract_is_stated() -> None:
    """The one thing a mounted repo must supply. Omitting it makes the overlay unusable:
    a reader would not know they need a hermetic one-command test environment."""
    low = _text().lower()
    assert "hermetic" in low, "the mount-time contract is not stated"
    assert "one-command" in low or "one command" in low, "the contract must be one command"
    for option in ("docker", "nix", "devcontainer", "makefile"):
        assert option in low, f"{option} must be named as a valid way to satisfy it"
    assert "option c" in low, "mounting an existing repo must be a documented path"
