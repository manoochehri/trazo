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
V_CREATE_OK = {
    "id": 3,
    "name": "v-create",
    "target": "tag",
    "enforcement": "active",
    "current_user_can_bypass": "always",
    "rules": [{"type": "creation"}],
}
LISTING = [{"id": 1, "name": "v", "target": "tag"}]
LISTING_WITH_CREATE = LISTING + [{"id": 3, "name": "v-create", "target": "tag"}]


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


def test_the_creation_ruleset_has_only_creation_and_only_the_admin_bypass() -> None:
    payload = protect.create_payload(V)
    assert _types(payload) == ["creation"]
    assert payload["bypass_actors"] == [protect.ADMIN]
    assert payload["conditions"] == V["conditions"]
    assert payload["name"] == "v-create"


class FakeGh:
    """Stands in for `gh`: records every call and request body and answers the few it needs."""

    def __init__(
        self,
        rulesets: list[dict],
        can_bypass: str | None = "always",
        v: dict | None = None,
        v_create: dict | None = None,
        delete_fails: bool = False,
    ) -> None:
        self.rulesets = rulesets
        self.can_bypass = can_bypass
        self.v = v or V
        self.v_create = v_create or V_CREATE_OK
        self.delete_fails = delete_fails
        self.calls: list[tuple[str, ...]] = []
        self.bodies: list[tuple[str, str, dict]] = []

    def __call__(self, *args: str, stdin: str | None = None) -> str:
        self.calls.append(args)
        if args[:2] == ("repo", "view"):
            return "o/r\n"
        method = args[args.index("-X") + 1] if "-X" in args else "GET"
        path = args[args.index("-X") + 2] if "-X" in args else args[1]
        if method != "GET":
            self.bodies.append((method, path, json.loads(stdin) if stdin else {}))
        if method == "DELETE" and self.delete_fails:
            raise SystemExit("gh api -X DELETE failed: boom")
        if method == "POST":
            return json.dumps({"id": 2})
        if method != "GET":
            return "{}"
        if path == "repos/o/r/rulesets":
            return json.dumps(self.rulesets)
        if path == "repos/o/r/rulesets/1":
            return json.dumps(self.v)
        if path == "repos/o/r/rulesets/3":
            return json.dumps(self.v_create)
        body = {"id": 2}
        if self.can_bypass is not None:
            body["current_user_can_bypass"] = self.can_bypass
        return json.dumps(body)

    def writes(self) -> list[tuple[str, str, dict]]:
        return self.bodies


def _run(monkeypatch: pytest.MonkeyPatch, fake: FakeGh, argv: list[str]) -> int:
    monkeypatch.setattr(protect, "_gh", fake)
    return protect.main(argv)


def test_a_dry_run_writes_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeGh(LISTING)
    assert _run(monkeypatch, fake, ["--dry-run"]) == 0
    assert fake.writes() == []


def test_an_unknown_argument_makes_no_calls_and_exits(monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_a_ruleset_that_is_not_active_stops_before_any_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeGh(LISTING, v={**V, "enforcement": "evaluate"})
    with pytest.raises(SystemExit):
        _run(monkeypatch, fake, [])
    assert fake.writes() == []


def test_applying_sends_update_to_v_and_creation_alone_to_a_new_ruleset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeGh(LISTING)
    assert _run(monkeypatch, fake, []) == 0
    (m1, p1, b1), (m2, p2, b2) = fake.writes()
    assert (m1, p1) == ("PUT", "repos/o/r/rulesets/1")
    assert _types(b1) == ["deletion", "non_fast_forward", "update"]
    assert b1["bypass_actors"] == []
    assert (m2, p2) == ("POST", "repos/o/r/rulesets")
    assert _types(b2) == ["creation"]
    assert b2["bypass_actors"] == [protect.ADMIN]


def test_a_wrong_admin_id_is_undone_and_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeGh(LISTING, can_bypass="never")
    with pytest.raises(SystemExit) as raised:
        _run(monkeypatch, fake, [])
    assert "current_user_can_bypass" in str(raised.value)
    assert ("api", "-X", "DELETE", "repos/o/r/rulesets/2") in fake.calls


def test_a_failed_undo_names_the_ruleset_to_remove(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeGh(LISTING, can_bypass="never", delete_fails=True)
    with pytest.raises(SystemExit) as raised:
        _run(monkeypatch, fake, [])
    assert "id 2" in str(raised.value)
    assert "Settings > Rules" in str(raised.value)


def test_a_missing_bypass_report_keeps_the_ruleset(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeGh(LISTING, can_bypass=None)
    assert _run(monkeypatch, fake, []) == 0
    assert not any(call[:3] == ("api", "-X", "DELETE") for call in fake.calls)


def test_an_existing_creation_ruleset_that_works_is_left_alone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeGh(LISTING_WITH_CREATE)
    assert _run(monkeypatch, fake, []) == 0
    assert [(m, p) for m, p, _ in fake.writes()] == [("PUT", "repos/o/r/rulesets/1")]


@pytest.mark.parametrize(
    "detail",
    [
        {**V_CREATE_OK, "rules": [{"type": "deletion"}]},
        {**V_CREATE_OK, "enforcement": "disabled"},
        {**V_CREATE_OK, "current_user_can_bypass": "never"},
    ],
    ids=["no creation rule", "not active", "cannot bypass"],
)
def test_an_existing_creation_ruleset_that_differs_is_never_edited(
    monkeypatch: pytest.MonkeyPatch, detail: dict
) -> None:
    fake = FakeGh(LISTING_WITH_CREATE, v_create=detail)
    with pytest.raises(SystemExit) as raised:
        _run(monkeypatch, fake, [])
    assert "never edits an existing one" in str(raised.value)
    assert fake.writes() == []
