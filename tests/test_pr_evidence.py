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
