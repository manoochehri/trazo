"""The installer ships the full harness to hosts (issue #285; ADR 0010, 0011).

A fresh install must leave a host with CI, review, drive (kill switch off), secret scanning,
the PR template and the scripts that check it, and a starter CODEOWNERS, and must print only
the steps an owner has to do. Stack-specific parts (the test command, the Dockerfile) are
placeholders that fail loudly. A file the host already owns is never overwritten.
"""

# ruff: noqa: S603, S607
import importlib.util
import re
import stat
import subprocess

import pytest

from test_install import (
    GIT_ENV,
    INSTALL,
    REPO_ROOT,
    git,
    make_host,
    make_source,
    manifest_lines,
    run,
)

HARNESS = REPO_ROOT / "src" / "harness"

SHIPPED = [
    ".github/workflows/ci.yml",
    ".github/workflows/review.yml",
    ".github/workflows/drive.yml",
    ".github/pull_request_template.md",
    ".github/CODEOWNERS",
    ".gitleaks.toml",
    ".pre-commit-config.yaml",
    ".env.example",
    "Dockerfile",
    "scripts/scan.sh",
    "scripts/scan-preflight.sh",
    "scripts/put_secret.sh",
    "scripts/check_pr_evidence.py",
    "scripts/report_verdict.py",
    "scripts/drive_guard.py",
    "scripts/drive_sweep.py",
]


@pytest.fixture
def source(tmp_path):
    return make_source(tmp_path)


@pytest.fixture
def host(tmp_path):
    h = make_host(tmp_path)
    git(h, "remote", "add", "origin", "https://github.com/acme/widgets.git")
    return h


def test_fresh_install_ships_the_harness(host, source):
    run(host, "install", "v0.1.0", source=source)
    missing = [p for p in SHIPPED if not (host / p).is_file()]
    assert missing == []
    for script in ("scan.sh", "scan-preflight.sh", "put_secret.sh"):
        assert (host / "scripts" / script).stat().st_mode & stat.S_IXUSR, script


def test_the_shared_files_are_the_ones_this_repo_runs():
    """One definition. A change to this repo's gate must reach hosts, so they may not drift."""
    for rel in (
        ".github/workflows/review.yml",
        ".github/workflows/drive.yml",
        ".github/pull_request_template.md",
        "scripts/scan.sh",
        "scripts/scan-preflight.sh",
        "scripts/put_secret.sh",
        "scripts/check_pr_evidence.py",
        "scripts/report_verdict.py",
        "scripts/drive_guard.py",
        "scripts/drive_sweep.py",
    ):
        assert (HARNESS / rel).read_bytes() == (REPO_ROOT / rel).read_bytes(), rel


def test_drive_ships_with_its_kill_switch(host, source):
    run(host, "install", "v0.1.0", source=source)
    text = (host / ".github/workflows/drive.yml").read_text()
    # Every job is named, so a new job added upstream without a gate fails here until someone
    # decides it. A job is gated when its own `if:` reads the owner's variable, or when it only
    # runs on a gated job's output (`needs:`, with no always()).
    jobs_text = text.split("\njobs:\n", 1)[1]
    blocks = re.split(r"^  (\w+):\n", jobs_text, flags=re.M)
    jobs = dict(zip(blocks[1::2], blocks[2::2], strict=True))
    assert set(jobs) == {"work", "publish", "stuck", "merge", "breaker", "digest", "sweep"}
    conds = {}
    gated = {}
    for name, body in jobs.items():
        m = re.search(r"^    if: (.*?)(?=^    \S)", body, re.M | re.S)
        conds[name] = m.group(1) if m else ""
        gated[name] = "vars.DRIVE_ENABLED == 'true'" in conds[name]
    for name, body in jobs.items():
        if gated[name]:
            continue
        needs = re.search(r"^    needs: (.+)$", body, re.M)
        deps = re.findall(r"\w+", needs.group(1)) if needs else []
        assert deps and all(gated[d] for d in deps), f"job {name} has no kill-switch gate"
        assert conds[name] and "always()" not in conds[name], f"job {name} runs when needs skip"
    assert gated["work"] and not gated["publish"]
    review = (host / ".github/workflows/review.yml").read_text()
    assert "vars.AUTO_REVIEW_ENABLED == 'true'" in review


def test_pr_template_carries_the_fields_the_checker_requires(host, source):
    run(host, "install", "v0.1.0", source=source)
    template = (host / ".github/pull_request_template.md").read_text()
    for field in ("Review rounds:", "efects found and fixed:", "Fail-first output:"):
        assert field in template, field
    spec = importlib.util.spec_from_file_location(
        "host_check_pr_evidence", host / "scripts/check_pr_evidence.py"
    )
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    assert checker.validate("nothing here")
    good = "Fail-first output:\nFAILED test_x\nReview rounds: 0\nDefects found and fixed: none\n"
    assert checker.validate(good) == []


def test_ci_has_the_evidence_check_and_a_test_placeholder_that_fails_loudly(host, source):
    run(host, "install", "v0.1.0", source=source)
    ci = (host / ".github/workflows/ci.yml").read_text()
    assert "scripts/check_pr_evidence.py" in ci
    assert "gitleaks" in ci
    # The test command is the host's stack; nothing is guessed, and the placeholder fails.
    assert "/kickoff" in ci and "exit 1" in ci
    assert "uv run pytest" not in ci
    dockerfile = (host / "Dockerfile").read_text()
    assert "/kickoff" in dockerfile and "exit 1" in dockerfile


def test_env_example_holds_placeholders_only(host, source):
    run(host, "install", "v0.1.0", source=source)
    for line in (host / ".env.example").read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            key, _, value = line.partition("=")
            assert re.fullmatch(r"<[^<>]+>|", value), line


def test_codeowners_starter_covers_prompts_roles_and_settings(host, source):
    run(host, "install", "v0.1.0", source=source)
    text = (host / ".github/CODEOWNERS").read_text()
    for path in (
        "/.github/workflows/",
        "/.github/CODEOWNERS",
        "/.claude/",
        "/.trazo/rules.md",
        "/.trazo/roles/",
        "/.trazo/project/charter/",
        "/.trazo/hooks/",
        "/.trazo/templates/",
        "/.trazo/ADVISOR.md",
        "/.trazo/ARCHITECTURE.md",
        "/.trazo/project/SKEPTIC_BAR.md",
        "/.mcp.json",
        "/CLAUDE.md",
        "/AGENTS.md",
    ):
        assert path in text, path
    # The owner comes from the origin remote, and no placeholder is left behind.
    assert "@acme" in text and "@OWNER" not in text


def test_codeowners_owner_placeholder_when_origin_is_unknown(tmp_path, source):
    h = make_host(tmp_path)
    run(h, "install", "v0.1.0", source=source)
    assert "@OWNER" in (h / ".github/CODEOWNERS").read_text()


def test_printout_is_the_owner_only_steps(host, source):
    out = run(host, "install", "v0.1.0", source=source).stdout
    assert "gh secret set ANTHROPIC_API_KEY -R acme/widgets" in out
    assert "AUTO_REVIEW_ENABLED" in out
    assert "GitHub App" in out
    assert "DRIVE_ENABLED" in out and "unset" in out
    assert "one watched run" in out
    # Nothing an agent can do for itself is asked of the owner.
    assert "make " not in out.split("Owner-only steps", 1)[1]


def test_second_install_keeps_host_edits_and_host_owned_files(host, source):
    (host / "Dockerfile").parent.mkdir(exist_ok=True)
    (host / "Dockerfile").write_text("FROM node:22\n")
    (host / ".github").mkdir()
    (host / ".github/CODEOWNERS").write_text("* @mine\n")
    (host / "scripts").mkdir()
    (host / "scripts/scan.sh").write_text("#!/bin/sh\necho mine\n")
    run(host, "install", "v0.1.0", source=source)
    assert (host / "Dockerfile").read_text() == "FROM node:22\n"
    assert (host / ".github/CODEOWNERS").read_text() == "* @mine\n"
    assert (host / "scripts/scan.sh").read_text() == "#!/bin/sh\necho mine\n"
    # A file the host owns is not ours to record, so uninstall cannot remove it.
    assert not any("Dockerfile" in line or "scan.sh" in line for line in manifest_lines(host))

    # Edit a file Trazo placed, reinstall, and the edit survives.
    ci = host / ".github/workflows/ci.yml"
    ci.write_text(ci.read_text() + "\n# host edit\n")
    edited = ci.read_bytes()
    pre = host / ".gitleaks.toml"
    pre.write_text("# host config\n")
    r = run(host, "install", "v0.1.0", source=source)
    assert ci.read_bytes() == edited
    assert pre.read_text() == "# host config\n"
    assert "edited since Trazo placed it" in r.stderr


def test_uninstall_removes_untouched_harness_files_only(host, source):
    run(host, "install", "v0.1.0", source=source)
    edited = host / ".github/workflows/ci.yml"
    edited.write_text("name: mine\n")
    run(host, "uninstall")
    assert edited.read_text() == "name: mine\n"
    assert not (host / "scripts/check_pr_evidence.py").exists()
    assert (host / ".github/CODEOWNERS").is_file()


def test_review_and_drive_need_the_claude_adapter(host, source):
    run(host, "install", "v0.1.0", "--adapter", "agents", source=source)
    assert (host / ".github/workflows/ci.yml").is_file()
    assert not (host / ".github/workflows/review.yml").exists()
    assert not (host / ".github/workflows/drive.yml").exists()


def test_install_script_still_parses():
    r = subprocess.run(["bash", "-n", str(INSTALL)], capture_output=True, text=True, env=GIT_ENV)
    assert r.returncode == 0, r.stderr
