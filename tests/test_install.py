"""The installer (`scripts/install.sh`, issue #118; ADR 0010, 0011).

Every test installs from a local bare git repository holding a copy of this repo's `src/`
and a tag, so nothing touches the network. The host is a throwaway git repo.
"""

# ruff: noqa: S603, S607
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL = REPO_ROOT / "scripts" / "install.sh"
BEGIN = "<!-- trazo:begin -->"
END = "<!-- trazo:end -->"

GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.com",
}


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, env=GIT_ENV)


def make_source(tmp_path: Path, tags=("v0.1.0",), mutate=None) -> Path:
    """A bare repo whose tags each carry src/; `mutate(src_dir, tag)` edits it per tag."""
    work = tmp_path / "source-work"
    bare = tmp_path / "source.git"
    git(tmp_path, "init", "-q", "--bare", str(bare))
    git(tmp_path, "init", "-q", str(work))
    for tag in tags:
        shutil.rmtree(work / "src", ignore_errors=True)
        shutil.copytree(
            REPO_ROOT / "src", work / "src", ignore=shutil.ignore_patterns("__pycache__")
        )
        if mutate:
            mutate(work / "src", tag)
        git(work, "add", "-A")
        git(work, "commit", "-q", "--allow-empty", "-m", f"release {tag}")
        git(work, "tag", tag)
    git(work, "push", "-q", str(bare), "--tags", "HEAD:refs/heads/main")
    return bare


def make_host(tmp_path: Path) -> Path:
    host = tmp_path / "host"
    host.mkdir()
    git(host, "init", "-q")
    return host


def run(host: Path, *args, source: Path | None = None, check=True):
    cmd = ["bash", str(INSTALL), *args]
    if source is not None:
        cmd += ["--source", str(source)]
    r = subprocess.run(cmd, cwd=host, capture_output=True, text=True, env=GIT_ENV)
    if check:
        assert r.returncode == 0, r.stdout + r.stderr
    return r


def snapshot(root: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file() and ".git" not in p.relative_to(root).parts
    }


@pytest.fixture
def source(tmp_path):
    return make_source(tmp_path)


@pytest.fixture
def host(tmp_path):
    return make_host(tmp_path)


def test_fresh_install(host, source):
    out = run(host, "install", "v0.1.0", source=source).stdout
    assert (host / ".trazo/VERSION").read_text().strip() == "v0.1.0"
    assert (host / ".trazo/rules.md").read_bytes() == (
        REPO_ROOT / "src/overlay/rules.md"
    ).read_bytes()
    # Blank templates land in the host's own project dir.
    for p in ("charter/charter.md", "STATUS.md", "PLAN.md", "RUNBOOK.md", "SKEPTIC_BAR.md"):
        assert (host / ".trazo/project" / p).is_file(), p
    # Both adapters by default, each as a marked block.
    for name in ("AGENTS.md", "CLAUDE.md"):
        text = (host / name).read_text()
        assert text.startswith(BEGIN + "\n") and text.rstrip().endswith(END)
    assert (host / ".claude/agents/pm.md").is_file()
    assert (host / ".claude/commands/work.md").is_file()
    assert (host / ".claude/settings.json").is_file()
    # CODEOWNERS is suggested, never written.
    assert "/.trazo/project/charter/" in out
    assert not (host / ".github/CODEOWNERS").exists()


def test_agents_adapter_only(host, source):
    run(host, "install", "v0.1.0", "--adapter", "agents", source=source)
    assert (host / "AGENTS.md").is_file()
    assert not (host / "CLAUDE.md").exists()
    assert not (host / ".claude").exists()


def test_existing_agents_md_is_preserved_byte_for_byte(host, source):
    before = b"# Mine\r\n\r\nbuild: make\n\n<!-- a comment -->\ntrailing   \n"
    (host / "AGENTS.md").write_bytes(before)
    run(host, "install", "v0.1.0", source=source)
    after = (host / "AGENTS.md").read_bytes()
    assert after.startswith(before)
    assert BEGIN.encode() in after[len(before) :]


def test_content_after_the_block_survives_a_reinstall(host, source):
    run(host, "install", "v0.1.0", source=source)
    p = host / "AGENTS.md"
    p.write_text("# Top\n\n" + p.read_text() + "\n## Footer\nkeep me\n")
    top, footer = "# Top\n\n", "\n## Footer\nkeep me\n"
    run(host, "install", "v0.1.0", source=source)
    text = p.read_text()
    assert text.startswith(top + BEGIN) and text.endswith(END + "\n" + footer)


def test_reinstall_is_idempotent(host, source):
    (host / "AGENTS.md").write_text("# Mine\n")
    run(host, "install", "v0.1.0", source=source)
    first = snapshot(host)
    run(host, "install", "v0.1.0", source=source)
    assert snapshot(host) == first


def test_name_clash_gets_trazo_prefix(host, source):
    (host / ".claude/agents").mkdir(parents=True)
    mine = "---\nname: pm\ndescription: my own pm\n---\nhost pm\n"
    (host / ".claude/agents/pm.md").write_text(mine)
    r = run(host, "install", "v0.1.0", "--adapter", "claude", source=source)
    assert (host / ".claude/agents/pm.md").read_text() == mine
    prefixed = host / ".claude/agents/trazo-pm.md"
    assert prefixed.is_file() and "name: trazo-pm" in prefixed.read_text()
    assert "trazo-pm.md" in r.stderr  # reported
    # Re-install keeps the same decision, and still leaves the host's file alone.
    first = snapshot(host)
    run(host, "install", "v0.1.0", "--adapter", "claude", source=source)
    assert snapshot(host) == first


def test_existing_settings_json_is_not_overwritten(host, source):
    (host / ".claude").mkdir()
    (host / ".claude/settings.json").write_text('{"mine": true}\n')
    run(host, "install", "v0.1.0", "--adapter", "claude", source=source)
    assert (host / ".claude/settings.json").read_text() == '{"mine": true}\n'


def test_upgrade_leaves_project_untouched_and_shows_diff(tmp_path, host):
    def mutate(src, tag):
        if tag == "v0.2.0":
            (src / "overlay/rules.md").write_text("# new rules\n")
            (src / "overlay/NEW.md").write_text("new\n")
            (src / "overlay/ADVISOR.md").unlink()

    src = make_source(tmp_path, ("v0.1.0", "v0.2.0"), mutate)
    run(host, "install", "v0.1.0", source=src)
    mine = host / ".trazo" / "project" / "adr" / "0001-mine.md"
    mine.write_text("my decision\n")
    (host / ".trazo/project/STATUS.md").write_text("my status\n")
    project_before = snapshot(host / ".trazo/project")

    dry = run(host, "upgrade", "v0.2.0", "--dry-run", source=src)
    assert "new rules" in dry.stdout
    assert (host / ".trazo/VERSION").read_text().strip() == "v0.1.0"

    out = run(host, "upgrade", "v0.2.0", source=src).stdout
    assert "new rules" in out  # the diff was shown
    assert (host / ".trazo/VERSION").read_text().strip() == "v0.2.0"
    assert (host / ".trazo/rules.md").read_text() == "# new rules\n"
    assert (host / ".trazo" / "NEW.md").is_file()
    assert not (host / ".trazo/ADVISOR.md").exists()
    assert snapshot(host / ".trazo/project") == project_before


def test_upgrade_requires_an_install(host, source):
    r = run(host, "upgrade", "v0.1.0", source=source, check=False)
    assert r.returncode != 0 and "nothing to upgrade" in r.stderr


def test_uninstall_leaves_host_content_intact(host, source):
    agents = b"# Mine\n\nhost rules\n"
    (host / "AGENTS.md").write_bytes(agents)
    (host / ".claude/agents").mkdir(parents=True)
    (host / ".claude/agents/pm.md").write_text("---\nname: pm\n---\nmine\n")
    run(host, "install", "v0.1.0", source=source)
    run(host, "uninstall", source=None)
    assert (host / "AGENTS.md").read_bytes() == agents
    assert not (host / "CLAUDE.md").exists()  # we created it, it held only our block
    assert (host / ".claude/agents/pm.md").read_text() == "---\nname: pm\n---\nmine\n"
    assert not (host / ".claude/agents/trazo-pm.md").exists()
    assert not (host / ".claude/commands").exists()
    assert not (host / ".trazo/rules.md").exists()
    # The host's project state stays unless asked.
    assert (host / ".trazo/project/STATUS.md").is_file()


def test_uninstall_purge_removes_project(host, source):
    run(host, "install", "v0.1.0", source=source)
    run(host, "uninstall", "--purge")
    assert not (host / ".trazo").exists()


def test_missing_tag_refuses(host, source):
    r = run(host, "install", "v9.9.9", source=source, check=False)
    assert r.returncode != 0
    assert not (host / ".trazo").exists()


def test_no_tag_refuses(host, source):
    r = run(host, "install", source=source, check=False)
    assert r.returncode != 0 and "tag" in r.stderr
    assert not (host / ".trazo").exists()


def test_branch_name_is_not_a_tag(host, source):
    r = run(host, "install", "main", source=source, check=False)
    assert r.returncode != 0
    assert not (host / ".trazo").exists()


def test_latest_resolves_to_the_highest_tag(tmp_path, host):
    src = make_source(tmp_path, ("v0.2.0", "v0.10.0", "v0.9.0"))
    run(host, "install", "latest", source=src)
    assert (host / ".trazo/VERSION").read_text().strip() == "v0.10.0"


def test_unbalanced_markers_refuse_without_editing(host, source):
    (host / "AGENTS.md").write_text(f"# Mine\n{BEGIN}\nhalf a block\n")
    r = run(host, "install", "v0.1.0", "--adapter", "agents", source=source, check=False)
    assert r.returncode != 0
    assert (host / "AGENTS.md").read_text() == f"# Mine\n{BEGIN}\nhalf a block\n"
