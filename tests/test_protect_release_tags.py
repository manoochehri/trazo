"""The owner-run script restricting release-tag creation builds the right ruleset change (#263)."""

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "protect_release_tags.py"
spec = importlib.util.spec_from_file_location("protect_release_tags", SCRIPT)
protect = importlib.util.module_from_spec(spec)
spec.loader.exec_module(protect)
ADMIN = protect.ADMIN
build_payload = protect.build_payload

CURRENT = {
    "id": 24755941,
    "name": "v",
    "target": "tag",
    "enforcement": "active",
    "bypass_actors": [],
    "conditions": {"ref_name": {"exclude": [], "include": ["refs/tags/v*"]}},
    "rules": [{"type": "deletion"}, {"type": "non_fast_forward"}],
}


def _types(payload: dict) -> list[str]:
    return [rule["type"] for rule in payload["rules"]]


def test_adds_creation_and_update_and_keeps_existing_rules() -> None:
    payload = build_payload(CURRENT)
    assert set(_types(payload)) == {"deletion", "non_fast_forward", "creation", "update"}


def test_only_the_admin_role_may_bypass() -> None:
    assert build_payload(CURRENT)["bypass_actors"] == [ADMIN]


def test_running_it_twice_changes_nothing() -> None:
    once = build_payload(CURRENT)
    assert build_payload({**CURRENT, **once}) == once


def test_existing_bypass_actors_are_kept() -> None:
    other = {"actor_id": 7, "actor_type": "Team", "bypass_mode": "always"}
    payload = build_payload({**CURRENT, "bypass_actors": [other]})
    assert payload["bypass_actors"] == [other, ADMIN]


def test_the_ref_pattern_and_name_are_preserved() -> None:
    payload = build_payload(CURRENT)
    assert payload["conditions"] == CURRENT["conditions"]
    assert (payload["name"], payload["target"], payload["enforcement"]) == ("v", "tag", "active")
