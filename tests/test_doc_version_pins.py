"""Docs must not hard-code a Trazo release number (#403): they use `latest`."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_doc_version_pins", ROOT / "scripts" / "check_doc_version_pins.py"
)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)

# Pages already clean of release numbers. index, how-it-works, in-your-repo and
# install still show one; #411 must fix them and then pass files=None so README.md
# and every page are scanned.
CLEAN_PAGES = ["handbook/guardrails.md", "handbook/day-to-day.md"]


def tree(tmp_path: Path, **pages: str) -> Path:
    (tmp_path / "handbook").mkdir()
    for name, text in pages.items():
        target = tmp_path / (name.replace("__", "/") + ".md")
        target.write_text(text, encoding="utf-8")
    return tmp_path


def test_hard_coded_releases_are_reported(tmp_path: Path) -> None:
    root = tree(
        tmp_path,
        README="bash install.sh install v0.3.1\n",
        handbook__install=(
            "curl https://raw.githubusercontent.com/o/trazo/v0.6.0/scripts/install.sh\n"
            "bash install.sh upgrade 0.2.0\nThe current release is **0.6.0**.\n"
        ),
    )
    problems = MOD.find_stale_pins(root)
    assert len(problems) == 4
    assert any("README.md:1" in p and "0.3.1" in p for p in problems)
    assert any("install.md:1" in p and "0.6.0" in p for p in problems)
    assert any("install.md:2" in p and "0.2.0" in p for p in problems)
    assert any("install.md:3" in p and "0.6.0" in p for p in problems)


def test_latest_passes_and_exemptions_hold(tmp_path: Path) -> None:
    root = tree(
        tmp_path,
        handbook__install=(
            "curl https://raw.githubusercontent.com/o/trazo/main/scripts/install.sh\n"
            "bash install.sh install latest\nbash install.sh upgrade latest --dry-run\n"
            "See [tags](https://github.com/o/trazo/releases/tag/v0.6.0) and "
            "[changelog](https://github.com/o/trazo/blob/main/CHANGELOG.md#v0.6.0).\n"
            "Tested with codex-cli 0.162.0-alpha.2.\n"
        ),
        handbook__changelog="## v0.2.0\nupgrade v0.1.0\n",
    )
    (root / "README.md").write_text("No numbers here.\n", encoding="utf-8")
    assert MOD.find_stale_pins(root) == []


def test_files_argument_limits_scan(tmp_path: Path) -> None:
    root = tree(tmp_path, handbook__old="install v0.1.0\n", handbook__new="install latest\n")
    assert MOD.find_stale_pins(root, ["handbook/new.md"]) == []
    assert MOD.find_stale_pins(root, ["handbook/old.md"])


def test_clean_pages_hard_code_no_release() -> None:
    assert MOD.find_stale_pins(ROOT, CLEAN_PAGES) == []
