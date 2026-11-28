"""Guards the Install page's commands (#436, #428).

The documented steps once downloaded the installer to `install.sh` in the repository root
and deleted it afterwards, which overwrote a host repository's own tracked `install.sh`.
The installer is now downloaded into a temporary directory. The page also states no release
number, because `latest` is what the installer accepts and a number goes stale.
"""

import re
from pathlib import Path

PAGE = Path(__file__).resolve().parents[1] / "handbook" / "install.md"


def _text() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_no_command_writes_or_runs_install_sh_in_the_working_directory() -> None:
    text = _text()
    assert not re.search(r"-o\s+install\.sh\b", text), "a command downloads into install.sh"
    assert not re.search(r"\bbash\s+install\.sh\b", text), "a command runs ./install.sh"
    assert not re.search(r"delete `install\.sh`|\brm install\.sh", text), (
        "the page tells the reader to delete install.sh; it should never be in the repository"
    )
    assert 'bash "$T/install.sh" install latest' in text, "the install command is missing"
    assert "mktemp -d" in text


def test_the_page_names_no_release_and_says_how_to_check_the_installed_one() -> None:
    text = _text()
    tokens = sorted(set(re.findall(r"\bv\d+\.\d+\.\d+\b", text)))
    assert not tokens, f"the Install page hard-codes a release number: {tokens}"
    assert ".trazo/VERSION" in text, "the page must say how to read the installed version"
    assert "latest" in text


def test_the_upgrade_section_explains_a_script_out_of_step() -> None:
    text = _text()
    assert "If the upgrade reports a script out of step" in text
    assert "scripts/report_verdict.py" in text
    assert "#435" in text


def test_the_page_states_what_the_installer_really_does() -> None:
    """The skeptic ran scripts/install.sh on #438 and found four statements that were false.
    Each is pinned here to the corrected wording."""
    text = _text()
    assert "for `--adapter codex` only" in text, "Codex files are placed only for the codex adapter"
    assert "with the Claude adapter, that is `claude` or `both`" in text
    assert "`.trazo/INSTALLED` lists every adapter and harness file" in text
    assert "never overwritten or removed" in text
    assert "Works with `upgrade` only. Never pass it to `install`" in text
    assert "does not remove `.github/CODEOWNERS`" in text
    assert "`DRIVE_BUILDER_APP_LOGIN`" in text
    assert "The script prints every file it placed" not in text
    assert "is never read or written" not in text
