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


def _load_validate():
    import importlib.util

    spec = importlib.util.spec_from_file_location("check_pr_evidence", CHECKER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate


def _render_template(text: str, *, exemption: bool) -> str:
    text = text.replace("<number>", "1").replace("<summary or none>", "none")
    if exemption:
        head, _, rest = text.partition("## Fail-first output")
        tail = rest.partition("Fail-first exemption:")[2]
        return (
            head
            + "Fail-first exemption:"
            + tail.replace("<reason, at least 20 characters>", "docs-only change, nothing to test")
        )
    start = text.index("<paste the failing")
    end = text.index("\n", start)
    text = text[:start] + "FAILED tests/test_x.py::test_y - AssertionError" + text[end:]
    return text.partition("No fail-first output")[0]


def test_template_renders_to_a_body_that_passes():
    validate = _load_validate()
    template = (ROOT / ".github" / "pull_request_template.md").read_text(encoding="utf-8")
    assert validate(_render_template(template, exemption=False)) == []
    assert validate(_render_template(template, exemption=True)) == []


def test_old_bullet_layout_fails():
    validate = _load_validate()
    old = (
        "- [ ] Review rounds: 1\n- [ ] defects found and fixed: none\n"
        "- Fail-first output:\n  FAILED tests/test_x.py\n"
    )
    assert validate(old) != []


def test_failure_message_prints_expected_layout(tmp_path: Path):
    result = _run_checker(tmp_path, "nothing useful")
    assert result.returncode == 1
    assert "Expected layout" in result.stderr
    assert "## Fail-first output" in result.stderr


def test_template_and_checker_copies_identical():
    for rel in (".github/pull_request_template.md", "scripts/check_pr_evidence.py"):
        assert (ROOT / rel).read_bytes() == (ROOT / "src" / "harness" / rel).read_bytes()
