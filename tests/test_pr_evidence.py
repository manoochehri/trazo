"""CI validation for the evidence required in pull request descriptions."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "check_pr_evidence.py"


def _run_checker(tmp_path: Path, body: str) -> subprocess.CompletedProcess[str]:
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps({"pull_request": {"body": body}}), encoding="utf-8")
    import os

    env = os.environ | {"GITHUB_EVENT_PATH": str(event_path)}
    return subprocess.run(  # noqa: S603 - own checker with controlled input
        [sys.executable, str(CHECKER)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_accepts_fail_first_output_and_review_summary(tmp_path: Path):
    result = _run_checker(
        tmp_path,
        """Review rounds: 2
Defects found and fixed: corrected the boundary condition
Fail-first output:
=========================== short test summary info ============================
FAILED tests/test_example.py::test_regression - AssertionError: expected 2
""",
    )

    assert result.returncode == 0, result.stderr


def test_accepts_explicit_exemption_for_behavior_neutral_change(tmp_path: Path):
    result = _run_checker(
        tmp_path,
        """Review rounds: 0
Defects found and fixed: none
Fail-first exemption: documentation-only change; runtime behavior is unchanged.
""",
    )

    assert result.returncode == 0, result.stderr


def test_rejects_unfilled_template_fields(tmp_path: Path):
    result = _run_checker(
        tmp_path,
        """Review rounds: <count>
Defects found and fixed: <summary or none>
Fail-first output: <paste failing test output or explain exemption>
""",
    )

    assert result.returncode != 0
    assert "Review rounds" in result.stderr
    assert "Fail-first" in result.stderr


def test_rejects_missing_failure_marker_or_exemption(tmp_path: Path):
    result = _run_checker(
        tmp_path,
        """Review rounds: 1
Defects found and fixed: none
Fail-first output:
The test passed.
""",
    )

    assert result.returncode != 0
    assert "failing test output" in result.stderr.lower()


FAIL_OUTPUT = (
    "=========================== short test summary info ============================\n"
    "FAILED tests/test_example.py::test_regression - AssertionError: expected 2\n"
)


def test_accepts_heading_form_of_fail_first_output(tmp_path: Path):
    for heading in ("## Fail-first output", "### Fail-first output", "## Fail-first output:"):
        result = _run_checker(
            tmp_path,
            f"Review rounds: 0\nDefects found and fixed: none\n\n{heading}\n\n{FAIL_OUTPUT}",
        )
        assert result.returncode == 0, (heading, result.stderr)


def test_heading_form_still_requires_failure_marker(tmp_path: Path):
    result = _run_checker(
        tmp_path,
        "Review rounds: 0\nDefects found and fixed: none\n\n## Fail-first output\n\nAll passed.\n",
    )

    assert result.returncode != 0
    assert "failing test output" in result.stderr.lower()


def test_malformed_review_rounds_message_states_expected_format(tmp_path: Path):
    result = _run_checker(
        tmp_path,
        f"Review rounds: 1 (one round, no findings)\nDefects found and fixed: none\n"
        f"Fail-first output:\n{FAIL_OUTPUT}",
    )

    assert result.returncode != 0
    assert "'Review rounds: 1 (one round, no findings)'" in result.stderr
    assert "on its own line" in result.stderr
    assert "digits only" in result.stderr


def test_ci_workflows_rerun_evidence_check_when_body_is_edited():
    for rel in (".github/workflows/ci.yml", "src/harness/.github/workflows/ci.yml"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "types: [opened, synchronize, reopened, edited]" in text, rel
