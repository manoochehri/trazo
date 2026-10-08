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


def version(host: Path) -> str:
    """First line of .trazo/VERSION is the tag; the second records the commit."""
    return (host / ".trazo" / "VERSION").read_text().splitlines()[0]


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
    assert version(host) == "v0.1.0"
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


def test_kickoff_product_and_installed_copy_use_current_layout(host, source):
    run(host, "install", "v0.1.0", "--adapter", "claude", source=source)
    product = REPO_ROOT / "src/adapters/claude/commands/kickoff.md"
    installed = host / ".claude/commands/kickoff.md"
    assert installed.read_bytes() == product.read_bytes()
    for text in (installed.read_text(), (host / ".trazo/skills/kickoff.md").read_text()):
        assert "semilla" not in text.lower()
        assert "templates/docs/" not in text


def test_codex_adapter_installs_agents_and_skills(host, source):
    run(host, "install", "v0.1.0", "--adapter", "codex", source=source)
    agents = (host / "AGENTS.md").read_text()
    pm = host / ".codex/agents/trazo-pm.toml"
    reviewer = host / ".codex/agents/trazo-reviewer.toml"
    work = host / ".agents/skills/trazo-work/SKILL.md"
    assert agents.startswith(BEGIN + "\n") and agents.rstrip().endswith(END)
    assert pm.is_file() and 'name = "trazo-pm"' in pm.read_text()
    assert reviewer.is_file() and ".trazo/roles/reviewer.md" in reviewer.read_text()
    assert work.is_file() and work.read_text().startswith("---\nname: trazo-work\n")
    assert ".trazo/skills/work.md" in work.read_text()
    assert (host / ".trazo/roles/engineer.md").is_file()
    assert (host / ".trazo/roles/reviewer.md").is_file()
    assert (host / ".trazo/skills/work.md").is_file()
    assert "installer created" in (host / ".trazo/skills/kickoff.md").read_text()
    assert ".trazo/roles/engineer.md" in (host / ".codex/agents/trazo-engineer.toml").read_text()
    assert not (host / "CLAUDE.md").exists()
    assert not (host / ".claude").exists()
    manifest = "\n".join(manifest_lines(host))
    assert ".codex/agents/trazo-pm.toml" in manifest
    assert ".agents/skills/trazo-work/SKILL.md" in manifest


def test_codex_adapter_preserves_host_name_collisions(host, source):
    (host / ".codex/agents").mkdir(parents=True)
    (host / ".codex/agents/trazo-pm.toml").write_text('name = "mine"\n')
    (host / ".agents/skills/trazo-work").mkdir(parents=True)
    (host / ".agents/skills/trazo-work/SKILL.md").write_text("mine\n")
    run(host, "install", "v0.1.0", "--adapter", "codex", source=source)
    assert (host / ".codex/agents/trazo-pm.toml").read_text() == 'name = "mine"\n'
    assert (host / ".codex/agents/trazo-trazo-pm.toml").is_file()
    assert (host / ".agents/skills/trazo-work/SKILL.md").read_text() == "mine\n"
    installed_skill = host / ".agents/skills/trazo-trazo-work/SKILL.md"
    assert installed_skill.is_file() and "name: trazo-trazo-work" in installed_skill.read_text()


def test_codex_adapter_uninstalls_only_manifest_files(host, source):
    run(host, "install", "v0.1.0", "--adapter", "codex", source=source)
    project = host / ".trazo/project/charter/charter.md"
    project.write_text("host project state\n")
    run(host, "uninstall")
    assert project.read_text() == "host project state\n"
    assert not (host / ".codex/agents/trazo-pm.toml").exists()
    assert not (host / ".agents/skills/trazo-work/SKILL.md").exists()
    assert not (host / "AGENTS.md").exists()


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
    assert version(host) == "v0.1.0"

    out = run(host, "upgrade", "v0.2.0", source=src).stdout
    assert "new rules" in out  # the diff was shown
    assert version(host) == "v0.2.0"
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
    # The project dir is untracked here, so --purge refuses until --force.
    r = run(host, "uninstall", "--purge", check=False)
    assert r.returncode != 0 and "--force" in r.stderr
    assert (host / ".trazo/project/STATUS.md").is_file()
    run(host, "uninstall", "--purge", "--force")
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
    assert version(host) == "v0.10.0"


def test_unbalanced_markers_refuse_without_editing(host, source):
    (host / "AGENTS.md").write_text(f"# Mine\n{BEGIN}\nhalf a block\n")
    r = run(host, "install", "v0.1.0", "--adapter", "agents", source=source, check=False)
    assert r.returncode != 0
    assert (host / "AGENTS.md").read_text() == f"# Mine\n{BEGIN}\nhalf a block\n"


def manifest_lines(host):
    return (host / ".trazo" / "INSTALLED").read_text().splitlines()


@pytest.mark.parametrize(
    "bad",
    [
        "../x",
        "/etc/passwd",
        ".github/CODEOWNERS",
        ".claude/agents/../../x.md",
        ".agents/skills/../SKILL.md",
        ".codex/agents/../../inject.toml",
    ],
)
def test_hostile_manifest_is_refused(host, source, bad):
    run(host, "install", "v0.1.0", source=source)
    victim = host / ".github" / "CODEOWNERS"
    victim.parent.mkdir(parents=True)
    victim.write_text("owner\n")
    with (host / ".trazo" / "INSTALLED").open("a") as f:
        f.write(f"{'0' * 64}  {bad}\n")
    for args in (("uninstall",), ("install", "v0.1.0"), ("upgrade", "v0.1.0")):
        r = run(host, *args, source=source if args[0] != "uninstall" else None, check=False)
        assert r.returncode != 0 and "INSTALLED" in r.stderr, args
    assert victim.read_text() == "owner\n"
    assert (host / ".trazo/rules.md").is_file()


def test_symlink_in_tag_is_refused(tmp_path, host):
    def mutate(src, tag):
        (src / "adapters/claude/agents/leak.md").symlink_to("/etc/hosts")

    src = make_source(tmp_path, ("v0.1.0",), mutate)
    r = run(host, "install", "v0.1.0", source=src, check=False)
    assert r.returncode != 0 and "symlink" in r.stderr
    assert not (host / ".trazo").exists() and not (host / ".claude").exists()


def test_uninstall_refuses_unbalanced_markers_and_deletes_nothing(host, source):
    run(host, "install", "v0.1.0", source=source)
    broken = f"# top\n{BEGIN}\nstuff\n## my important section\nkeep\n"
    (host / "AGENTS.md").write_text(broken)
    r = run(host, "uninstall", check=False)
    assert r.returncode != 0 and "unbalanced" in r.stderr
    assert (host / "AGENTS.md").read_text() == broken
    assert (host / ".trazo/rules.md").is_file()
    assert (host / ".claude/agents/pm.md").is_file()


def test_crlf_markers_are_recognised(host, source):
    run(host, "install", "v0.1.0", "--adapter", "agents", source=source)
    p = host / "AGENTS.md"
    p.write_bytes(p.read_bytes().replace(b"\n", b"\r\n"))
    run(host, "install", "v0.1.0", "--adapter", "agents", source=source)
    assert p.read_bytes().count(BEGIN.encode()) == 1
    run(host, "uninstall")
    assert not p.exists()


@pytest.mark.parametrize(
    "adapter,rel",
    [
        ("claude", ".claude/settings.json"),
        ("claude", ".claude/agents/pm.md"),
        ("claude", ".claude/commands/work.md"),
        ("codex", ".codex/agents/trazo-reviewer.toml"),
        ("codex", ".agents/skills/trazo-work/SKILL.md"),
    ],
)
def test_edited_installed_file_survives_upgrade_and_uninstall(tmp_path, host, adapter, rel):
    def mutate(src, tag):
        if tag == "v0.2.0":
            for f in (src / "adapters").rglob("*"):
                if f.is_file():
                    f.write_text(f.read_text() + "\n")

    src = make_source(tmp_path, ("v0.1.0", "v0.2.0"), mutate)
    run(host, "install", "v0.1.0", "--adapter", adapter, source=src)
    mine = host / rel
    mine.write_text("host edit\n")
    r = run(host, "upgrade", "v0.2.0", "--adapter", adapter, source=src)
    assert mine.read_text() == "host edit\n"
    assert "edited" in r.stderr and "host edit" in r.stderr  # warning and diff
    other = (
        host / ".claude/commands/start.md"
        if adapter == "claude"
        else host / ".agents/skills/trazo-start/SKILL.md"
    )
    assert other.read_text().endswith("\n\n")  # untouched files do upgrade
    r = run(host, "uninstall")
    assert mine.read_text() == "host edit\n"
    assert not other.exists()


def test_commit_is_printed_recorded_and_pinnable(tmp_path, host, source):
    sha = subprocess.run(
        ["git", "rev-parse", "v0.1.0^{commit}"], cwd=source, capture_output=True, text=True
    ).stdout.strip()
    r = run(host, "install", "v0.1.0", "--sha", "0" * 40, source=source, check=False)
    assert r.returncode != 0 and sha in r.stderr and not (host / ".trazo").exists()
    r = run(host, "install", "v0.1.0", "--sha", "abc", source=source, check=False)
    assert r.returncode != 0
    out = run(host, "install", "v0.1.0", "--sha", sha, source=source).stdout
    assert sha in out
    assert (host / ".trazo/VERSION").read_text() == f"v0.1.0\ncommit {sha}\n"


def test_pre_manifest_layout_refuses(host, source):
    (host / ".trazo" / "adr").mkdir(parents=True)
    (host / ".trazo" / "adr" / "0001.md").write_text("mine\n")
    (host / ".trazo" / "VERSION").write_text("v0.0.1\n")
    for cmd in ("install", "upgrade"):
        r = run(host, cmd, "v0.1.0", source=source, check=False)
        assert r.returncode != 0 and "older layout" in r.stderr
    assert (host / ".trazo" / "adr" / "0001.md").read_text() == "mine\n"


def test_option_like_source_is_refused(host):
    r = run(host, "install", "v0.1.0", "--source", "--upload-pack=touch pwned", check=False)
    assert r.returncode != 0
    assert not (host / "pwned").exists() and not (host / ".trazo").exists()


def test_env_source_is_announced(host, source):
    env = {**GIT_ENV, "TRAZO_SOURCE": str(source)}
    r = subprocess.run(
        ["bash", str(INSTALL), "install", "v0.1.0"],
        cwd=host,
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 0 and "TRAZO_SOURCE overrides" in r.stderr


def test_settings_are_printed_on_install(host, source):
    out = run(host, "install", "v0.1.0", source=source).stdout
    assert '"deny"' in out


def test_shipped_settings_keep_deny_rules_and_engineer_default():
    """The installed model default may change; its secret deny rules may only tighten."""
    import json

    perms = json.loads((REPO_ROOT / "src/adapters/claude/settings.json").read_text())
    assert perms["model"] == "haiku"
    assert set(perms) == {"model", "permissions"}
    assert set(perms["permissions"]) == {"deny"}, "shipped settings may only deny"


def test_reversed_markers_are_refused(host, source):
    reversed_ = f"# top\n{END}\nmid\n{BEGIN}\n## host section after\nkeep\n"
    (host / "AGENTS.md").write_text(reversed_)
    r = run(host, "install", "v0.1.0", "--adapter", "agents", source=source, check=False)
    assert r.returncode != 0 and "order" in r.stderr
    assert (host / "AGENTS.md").read_text() == reversed_
    (host / "AGENTS.md").unlink()
    run(host, "install", "v0.1.0", "--adapter", "claude", source=source)
    (host / "AGENTS.md").write_text(reversed_)
    r = run(host, "uninstall", check=False)
    assert r.returncode != 0
    assert (host / "AGENTS.md").read_text() == reversed_


def test_host_owning_both_name_and_prefixed_name_is_not_overwritten(host, source):
    d = host / ".claude" / "agents"
    d.mkdir(parents=True)
    (d / "pm.md").write_text("host pm\n")
    (d / "trazo-pm.md").write_text("host trazo-pm\n")
    r = run(host, "install", "v0.1.0", "--adapter", "claude", source=source)
    assert "also yours" in r.stderr
    assert (d / "trazo-pm.md").read_text() == "host trazo-pm\n"
    run(host, "uninstall")
    assert (d / "pm.md").read_text() == "host pm\n"
    assert (d / "trazo-pm.md").read_text() == "host trazo-pm\n"


def test_manifest_keep_loop_compares_whole_paths(tmp_path, host):
    def mutate(src, tag):
        if tag == "v0.2.0":
            agents = src / "adapters/claude/agents"
            (agents / "pm.md").rename(agents / "pm.md.md")

    src = make_source(tmp_path, ("v0.1.0", "v0.2.0"), mutate)
    run(host, "install", "v0.1.0", "--adapter", "claude", source=src)
    run(host, "upgrade", "v0.2.0", "--adapter", "claude", source=src)
    mf = host / ".trazo" / "INSTALLED"
    paths = [x.split("  ", 1)[1] for x in mf.read_text().splitlines()]
    # pm.md is no longer shipped but is still on disk; it must stay listed even though
    # pm.md.md (which contains its name) was placed.
    assert ".claude/agents/pm.md" in paths and ".claude/agents/pm.md.md" in paths


def test_purge_fails_closed_when_project_is_ignored(host, source):
    run(host, "install", "v0.1.0", source=source)
    (host / ".gitignore").write_text(".trazo/project/\n")
    r = run(host, "uninstall", "--purge", check=False)
    assert r.returncode != 0 and "--force" in r.stderr
    assert (host / ".trazo/project/STATUS.md").is_file()


def test_purge_fails_closed_when_git_status_fails(host, source):
    run(host, "install", "v0.1.0", source=source)
    shutil.rmtree(host / ".git")
    (host / ".git").write_text("gitdir: /nonexistent\n")
    r = run(host, "uninstall", "--purge", check=False)
    assert r.returncode != 0 and "--force" in r.stderr
    assert (host / ".trazo/project/STATUS.md").is_file()


def test_purge_keeps_gitignored_file_without_force(host, source):
    run(host, "install", "v0.1.0", source=source)
    (host / ".gitignore").write_text("*.local\n")
    subprocess.run(["git", "add", "-A", "-f", ".trazo/project", ".gitignore"], cwd=host, check=True)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x"],
        cwd=host,
        check=True,
    )
    note = host / ".trazo" / "project" / "notes.local"
    note.write_text("mine\n")
    r = run(host, "uninstall", "--purge", check=False)
    assert r.returncode != 0 and "--force" in r.stderr
    assert note.read_text() == "mine\n"
    run(host, "uninstall", "--purge", "--force")
    assert not note.exists()
