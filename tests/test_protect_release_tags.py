"""The owner-run tag-protection script tightens limits and never loosens them (#263)."""

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "protect_release_tags.py"
spec = importlib.util.spec_from_file_location("protect_release_tags", SCRIPT)
protect = importlib.util.module_from_spec(spec)
spec.loader.exec_module(protect)

V = {
    "id": 1,
    "name": "v",
    "target": "tag",
    "enforcement": "active",
    "bypass_actors": [],
    "conditions": {"ref_name": {"exclude": [], "include": ["refs/tags/v*"]}},
    "rules": [{"type": "deletion"}, {"type": "non_fast_forward"}],
}


def _types(payload: dict) -> list[str]:
    return [rule["type"] for rule in payload["rules"]]


def test_v_gains_update_and_keeps_everything_else() -> None:
    payload = protect.tighten_payload(V)
    assert _types(payload) == ["deletion", "non_fast_forward", "update"]
    assert payload["bypass_actors"] == []
    assert payload["conditions"] == V["conditions"]
    assert (payload["name"], payload["target"], payload["enforcement"]) == ("v", "tag", "active")


def test_v_never_gains_a_bypass_actor() -> None:
    other = {"actor_id": 7, "actor_type": "Team", "bypass_mode": "always"}
    payload = protect.tighten_payload({**V, "bypass_actors": [other]})
    assert payload["bypass_actors"] == [other]


def test_tightening_twice_changes_nothing() -> None:
    once = protect.tighten_payload(V)
    assert protect.tighten_payload({**V, **once}) == once


def test_creation_ruleset_has_only_creation_and_only_the_admin_bypass() -> None:
    payload = protect.create_payload(V)
    assert _types(payload) == ["creation"]
    assert payload["bypass_actors"] == [protect.ADMIN]
    assert payload["conditions"] == V["conditions"]
    assert payload["name"] == "v-create"


class FakeGh:
    """Stands in for `gh`: records every call and answers the few the script makes."""

    def __init__(self, rulesets: list[dict], can_bypass: str | None = "always") -> None:
        self.rulesets = rulesets
        self.can_bypass = can_bypass
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, *args: str, stdin: str | None = None) -> str:
        self.calls.append(args)
        if args[:2] == ("repo", "view"):
            return "o/r\n"
        method = args[args.index("-X") + 1] if "-X" in args else "GET"
        path = args[1] if args[0] == "api" and not args[1].startswith("-") else ""
        if method == "GET" and path == "repos/o/r/rulesets":
            return json.dumps(self.rulesets)
        if method == "GET" and path == "repos/o/r/rulesets/1":
            return json.dumps(V)
        if method == "GET":
            body = {"id": 2}
            if self.can_bypass is not None:
                body["current_user_can_bypass"] = self.can_bypass
            return json.dumps(body)
        if method == "POST":
            return json.dumps({"id": 2})
        return "{}"

    def writes(self) -> list[tuple[str, ...]]:
        return [c for c in self.calls if "-X" in c]


LISTING = [{"id": 1, "name": "v", "target": "tag"}]


def _run(monkeypatch: pytest.MonkeyPatch, fake: FakeGh, argv: list[str]) -> int:
    monkeypatch.setattr(protect, "_gh", fake)
    return protect.main(argv)


def test_a_dry_run_writes_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeGh(LISTING)
    assert _run(monkeypatch, fake, ["--dry-run"]) == 0
    assert fake.writes() == []


def test_an_unknown_argument_changes_nothing_and_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeGh(LISTING)
    with pytest.raises(SystemExit):
        _run(monkeypatch, fake, ["--dryrun"])
    assert fake.calls == []


@pytest.mark.parametrize(
    "listing",
    [[], LISTING + [{"id": 9, "name": "v", "target": "tag"}]],
    ids=["no tag ruleset", "two tag rulesets"],
)
def test_zero_or_two_matching_rulesets_exit_without_writing(
    monkeypatch: pytest.MonkeyPatch, listing: list[dict]
) -> None:
    fake = FakeGh(listing)
    with pytest.raises(SystemExit):
        _run(monkeypatch, fake, [])
    assert fake.writes() == []


def test_applying_tightens_v_and_creates_the_creation_ruleset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeGh(LISTING)
    assert _run(monkeypatch, fake, []) == 0
    methods = [(c[c.index("-X") + 1], c[c.index("-X") + 2]) for c in fake.writes()]
    assert methods == [("PUT", "repos/o/r/rulesets/1"), ("POST", "repos/o/r/rulesets")]


def test_a_wrong_admin_id_is_undone_and_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeGh(LISTING, can_bypass="never")
    with pytest.raises(SystemExit) as raised:
        _run(monkeypatch, fake, [])
    assert "current_user_can_bypass" in str(raised.value)
    assert ("api", "-X", "DELETE", "repos/o/r/rulesets/2") in fake.calls
