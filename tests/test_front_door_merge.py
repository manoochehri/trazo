"""Issue #333: the front door merges by dispatching the gated owner-merge workflow.

`gh pr merge` stays denied; the broad `gh workflow run *` deny is replaced by specific denies so the
one dispatch an agent may run is `gh workflow run owner-merge.yml -f pr=<n>`.
"""

import fnmatch
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
# .claude/settings.json is the installed copy pinned to v0.3.1 (ADR 0010, test_trazo_layout); it
# follows src/ on the next release reinstall and is not edited by hand.
SETTINGS = [ROOT / "src/adapters/claude/settings.json"]


def _denied(settings: Path, command: str) -> bool:
    deny = json.loads(settings.read_text(encoding="utf-8"))["permissions"]["deny"]
    patterns = [r[len("Bash(") : -1] for r in deny if r.startswith("Bash(")]
    return any(fnmatch.fnmatchcase(command, p) for p in patterns)


@pytest.mark.parametrize("settings", SETTINGS, ids=lambda p: str(p.relative_to(ROOT)))
def test_owner_merge_dispatch_is_allowed(settings):
    assert not _denied(settings, "gh workflow run owner-merge.yml -f pr=123")
    assert not _denied(settings, "gh workflow list")
    assert not _denied(settings, "gh run list --workflow owner-merge.yml")


@pytest.mark.parametrize("settings", SETTINGS, ids=lambda p: str(p.relative_to(ROOT)))
@pytest.mark.parametrize(
    "command",
    [
        "gh pr merge 12 --squash",
        "gh workflow run drive.yml",
        "gh workflow run drive.yml -f mode=x",
        "gh workflow run ci.yml",
        "gh workflow run review.yml",
        "gh workflow run report.yml",
        "gh workflow run docs.yml",
        "gh workflow run release.yml",
        "gh workflow run deploy.yml",
    ],
)
def test_other_merges_and_dispatches_stay_denied(settings, command):
    assert _denied(settings, command)


@pytest.mark.parametrize("settings", SETTINGS, ids=lambda p: str(p.relative_to(ROOT)))
def test_every_dispatchable_workflow_but_owner_merge_is_denied(settings):
    for base in (ROOT / ".github/workflows", ROOT / "src/harness/.github/workflows"):
        for wf in base.glob("*.yml"):
            if (
                "workflow_dispatch" in wf.read_text(encoding="utf-8")
                and wf.name != "owner-merge.yml"
            ):
                assert _denied(settings, f"gh workflow run {wf.name}"), wf


def test_rules_front_door_says_it_merges_through_owner_merge():
    text = (ROOT / "src/overlay/rules.md").read_text(encoding="utf-8")
    front = text.split("## Front door", 1)[1].split("\n## ", 1)[0]
    flat = " ".join(front.split())
    assert "owner-merge.yml" in flat
    assert "engineer and PM never merge" in flat


def test_owner_merge_copies_identical_and_say_agents_may_dispatch():
    a = (ROOT / ".github/workflows/owner-merge.yml").read_bytes()
    b = (ROOT / "src/harness/.github/workflows/owner-merge.yml").read_bytes()
    assert a == b
    assert b"agents may dispatch" in a.lower()
