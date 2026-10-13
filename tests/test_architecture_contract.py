"""The host-owned architecture contract (#196).

The blank template ships with the installer and is copied into the host's `.trazo/project/`
at install time. Kickoff, start and work discover it there. Install and upgrade behaviour is
tested in `test_install.py`.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = REPO_ROOT / "src/overlay/templates/docs/ARCHITECTURE_CONTRACT.md"
SKILLS = REPO_ROOT / "src/overlay/skills"
CONTRACT = "ARCHITECTURE_CONTRACT.md"


def test_template_ships_in_the_docs_templates():
    assert TEMPLATE.is_file()


def test_template_has_a_required_acceptance_command_placeholder():
    text = TEMPLATE.read_text()
    assert "Acceptance commands" in text
    assert "REQUIRED" in text


def test_template_labels_each_reference_check_as_proposed_or_executed():
    text = TEMPLATE.read_text()
    assert "proposed" in text
    assert "executed" in text


def test_kickoff_start_and_work_discover_the_contract():
    for name in ("kickoff.md", "start.md", "work.md"):
        assert CONTRACT in (SKILLS / name).read_text(), name
