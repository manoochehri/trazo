"""Docs must not pin a Trazo version other than .template/VERSION (#403)."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_doc_version_pins", ROOT / "scripts" / "check_doc_version_pins.py"
)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)

# Pages already rewritten. #411 extends this to README.md and every page once the
# old pages are gone (then pass files=None).
REWRITTEN = [
    "handbook/index.md",
    "handbook/how-it-works.md",
    "handbook/in-your-repo.md",
    "handbook/install.md",
    "handbook/guardrails.md",
    "handbook/day-to-day.md",
]


def tree(tmp_path: Path, **pages: str) -> Path:
    (tmp_path / ".template").mkdir()
    (tmp_path / ".template" / "VERSION").write_text("0.6.0\n", encoding="utf-8")
    (tmp_path / "handbook").mkdir()
    for name, text in pages.items():
        target = tmp_path / (name.replace("__", "/") + ".md")
        target.write_text(text, encoding="utf-8")
    return tmp_path


def test_old_pins_are_reported(tmp_path: Path) -> None:
    root = tree(
        tmp_path,
        README="",
        handbook__install=(
            "curl https://raw.githubusercontent.com/o/trazo/v0.3.1/scripts/install.sh\n"
            "bash install.sh upgrade v0.2.0\nThe current release is **0.5.0**.\n"
        ),
    )
    (root / "README.md").write_text("bash install.sh install v0.3.1\n", encoding="utf-8")
    problems = MOD.find_stale_pins(root)
    assert len(problems) == 4
    assert any("README.md:1" in p and "v0.3.1" in p for p in problems)
    assert any("install.md:2" in p and "v0.2.0" in p for p in problems)
    assert any("install.md:3" in p and "v0.5.0" in p for p in problems)


def test_clean_tree_passes_and_exemptions_hold(tmp_path: Path) -> None:
    root = tree(
        tmp_path,
        handbook__install="bash install.sh upgrade v0.6.0\nThe current release is v0.6.0.\n",
        handbook__changelog="## v0.2.0\nupgrade v0.1.0\n",
    )
    (root / "README.md").write_text("Since 0.4.0 things changed.\n", encoding="utf-8")
    assert MOD.find_stale_pins(root) == []


def test_files_argument_limits_scan(tmp_path: Path) -> None:
    root = tree(tmp_path, handbook__old="install v0.1.0\n", handbook__new="install v0.6.0\n")
    assert MOD.find_stale_pins(root, ["handbook/new.md"]) == []
    assert MOD.find_stale_pins(root, ["handbook/old.md"])


def test_rewritten_pages_pin_only_the_current_version() -> None:
    assert MOD.find_stale_pins(ROOT, REWRITTEN) == []
