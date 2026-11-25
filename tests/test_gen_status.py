"""#328 step 1: scripts/gen_status.py builds the generated STATUS block from canned gh JSON.

No network, no LLM, no repo writes. Field names follow `gh pr list --json
number,title,url,statusCheckRollup` and `gh api repos/{o}/{r}/milestones` (state, open_issues,
closed_issues, html_url): https://cli.github.com/manual/gh_pr_list and
https://docs.github.com/en/rest/issues/milestones
"""

import importlib.util
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("gen_status", REPO_ROOT / "scripts" / "gen_status.py")
gen_status = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen_status)

NOW = "2026-11-25T10:00:00Z"
SHA = "a" * 40


def pr(n, state="SUCCESS"):
    return {"number": n, "title": f"pr {n}", "url": f"https://x/pull/{n}", "checks": state}


def data(**kw):
    base = {
        "tag": "v0.3.1",
        "milestone": {"title": "v0.4.0", "open": 3, "closed": 5, "url": "https://x/m/1"},
        "prs": [],
        "halt_issues": [],
        "drive_enabled": "true",
        "waiting": [],
    }
    base.update(kw)
    return base


def test_running_block_has_tag_milestone_and_stamp():
    out = gen_status.build_block(data(), NOW, SHA)
    assert "v0.3.1" in out
    assert "v0.4.0" in out and "3 open" in out and "5 closed" in out
    assert "running" in out.lower() and "halted" not in out.lower()
    assert f"generated at {NOW} from main@{SHA[:7]}" in out


def test_halted_when_drive_halt_issue_is_open():
    out = gen_status.build_block(data(halt_issues=[12]), NOW, SHA)
    assert "halted" in out.lower() and "#12" in out


def test_halted_when_drive_disabled():
    out = gen_status.build_block(data(drive_enabled=""), NOW, SHA)
    assert "halted" in out.lower() or "disabled" in out.lower()


def test_no_open_milestone_and_empty_milestone():
    out = gen_status.build_block(data(milestone=None), NOW, SHA)
    assert "no open milestone" in out.lower()
    empty = {"title": "v0.5.0", "open": 0, "closed": 0, "url": "https://x/m/2"}
    out = gen_status.build_block(data(milestone=empty), NOW, SHA)
    assert "v0.5.0" in out and "0 open" in out and "0 closed" in out


def test_long_pr_list_is_truncated_to_count_and_links():
    prs = [pr(n) for n in range(1, 31)]
    out = gen_status.build_block(data(prs=prs), NOW, SHA)
    assert "30 open" in out
    links = re.findall(r"https://x/pull/\d+", out)
    assert 0 < len(links) <= gen_status.MAX_LISTED
    assert "more" in out


def test_pr_check_state_is_shown():
    out = gen_status.build_block(data(prs=[pr(4, "FAILURE")]), NOW, SHA)
    assert "#4" in out and "FAILURE" in out


def test_waiting_on_owner_lists_links_or_none():
    w = [{"number": 9, "title": "t", "url": "https://x/issues/9"}]
    assert "https://x/issues/9" in gen_status.build_block(data(waiting=w), NOW, SHA)
    assert "none" in gen_status.build_block(data(), NOW, SHA).lower()


def test_same_ignoring_stamp():
    a = gen_status.build_block(data(), "2026-11-25T10:00:00Z", "a" * 40)
    b = gen_status.build_block(data(), "2026-11-26T11:30:00Z", "b" * 40)
    c = gen_status.build_block(data(tag="v0.4.0"), NOW, SHA)
    assert gen_status.same_ignoring_stamp(a, b)
    assert not gen_status.same_ignoring_stamp(a, c)


def test_collect_uses_only_read_gh_calls(monkeypatch):
    calls = []

    def fake(*args):
        calls.append(args)
        return "[]"

    monkeypatch.setattr(gen_status, "_gh", fake)
    gen_status.collect("o/r", "true")
    assert calls
    assert all(a[0] in ("pr", "issue", "api", "release") for a in calls)
    assert not any(x in ("create", "edit", "close", "merge", "comment") for a in calls for x in a)
