"""One-time OWNER script (#380, #248): let the builder GitHub App create release tags. Run by the
owner.

`scripts/protect_release_tags.py` (#263) made tag creation owner-only through the tag ruleset
`v-create`
(rule `creation`, bypass = the repository Admin role). Release tagging moves to
`.github/workflows/release.yml`,
which runs `scripts/release.sh` as the builder App. This adds that App to `v-create`'s bypass list
so the
workflow can push the tag. It touches ONLY `v-create`: the ruleset `v` (no delete, no force-move, no
update)
gets no bypass, so an existing tag can still never be moved or deleted by the App.

    python3 scripts/allow_release_app.py <builder-app-id> --dry-run   # show the change, write
    nothing
    python3 scripts/allow_release_app.py <builder-app-id>             # apply it, read it back
    python3 scripts/allow_release_app.py <builder-app-id> --remove    # ROLLBACK: take the App off
    again

<builder-app-id> is the numeric "App ID" on the builder App's settings page (the BUILDER_APP_ID
secret).

Changing a ruleset is a human-only limit (rules.md, "Safety limits are human-only").

UNVERIFIED: the bypass actor shape `{"actor_id": <App ID>, "actor_type": "Integration",
"bypass_mode":
"always"}` is from GitHub's REST documentation for repository rulesets as recalled when this was
written; it
was not fetched or run live (no agent can write rulesets). After the PUT the script reads the
ruleset back and
exits non-zero unless the bypass list, conditions and rules are exactly as sent, so a wrong shape is
reported, never silent. Also UNVERIFIED: that a push by the App's installation token is covered by
this bypass. Check with the first real release; if the push is refused, run this script with
--remove and tag with `make release` as before.
"""

import json
import shutil
import subprocess
import sys

NAME = "v-create"


def _actor(app_id: int) -> dict:
    return {"actor_id": app_id, "actor_type": "Integration", "bypass_mode": "always"}


def check_target(ruleset: dict) -> None:
    """Refuse anything but the creation-only tag ruleset: the App must never get a bypass on `v`."""
    types = [r["type"] for r in ruleset.get("rules", [])]
    if ruleset.get("name") != NAME or ruleset.get("target") != "tag" or types != ["creation"]:
        sys.exit(
            f"refusing: expected the tag ruleset {NAME!r} with only a creation rule, got "
            f"{ruleset.get('name')!r} with {types}. Nothing was changed."
        )


def _payload(current: dict, actors: list[dict]) -> dict:
    return {
        "name": current["name"],
        "target": current["target"],
        "enforcement": current["enforcement"],
        "conditions": current["conditions"],
        "rules": [
            {k: v for k, v in r.items() if k in ("type", "parameters")} for r in current["rules"]
        ],
        "bypass_actors": actors,
    }


def add_payload(current: dict, app_id: int) -> dict:
    actors = [a for a in current.get("bypass_actors") or []]
    if not any(
        a.get("actor_type") == "Integration" and a.get("actor_id") == app_id for a in actors
    ):
        actors.append(_actor(app_id))
    return _payload(current, actors)


def remove_payload(current: dict, app_id: int) -> dict:
    actors = [
        a
        for a in current.get("bypass_actors") or []
        if not (a.get("actor_type") == "Integration" and a.get("actor_id") == app_id)
    ]
    return _payload(current, actors)


def verify(back: dict, payload: dict) -> list[str]:
    """What differs between the ruleset read back and what was sent; empty means as intended.

    Compares the bypass list (so the other actors are unchanged and the App is present or absent as
    asked), the conditions, the rules, the target and the enforcement.
    """
    wrong = []
    for key in ("bypass_actors", "conditions", "rules", "target", "enforcement", "name"):
        got = back.get(key) or ([] if key == "bypass_actors" else None)
        if got != payload[key]:
            wrong.append(f"{key} is {got!r}, expected {payload[key]!r}")
    return wrong


def _gh(*args: str, stdin: str | None = None) -> str:
    gh = shutil.which("gh")
    if gh is None:
        sys.exit("The GitHub CLI (gh) is required.")
    result = subprocess.run(  # noqa: S603 - resolved executable, fixed argv
        [gh, *args], input=stdin, capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        sys.exit(f"gh {' '.join(args)} failed:\n{result.stderr.strip()}")
    return result.stdout


def main(argv: list[str]) -> int:
    flags = {a for a in argv if a.startswith("--")}
    rest = [a for a in argv if not a.startswith("--")]
    if flags - {"--dry-run", "--remove"} or len(rest) != 1 or not rest[0].isdigit():
        sys.exit("usage: allow_release_app.py <builder-app-id> [--dry-run] [--remove]")
    app_id, dry_run, remove = int(rest[0]), "--dry-run" in flags, "--remove" in flags
    repo = _gh("repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner").strip()
    listing = json.loads(_gh("api", f"repos/{repo}/rulesets"))
    found = [r for r in listing if r["target"] == "tag" and r["name"] == NAME]
    if len(found) != 1:
        sys.exit(
            f"Expected one tag ruleset named {NAME!r} in {repo}, found {len(found)}. "
            "Run scripts/protect_release_tags.py first."
        )
    path = f"repos/{repo}/rulesets/{found[0]['id']}"
    current = json.loads(_gh("api", path))
    check_target(current)
    payload = (remove_payload if remove else add_payload)(current, app_id)
    print(f"{repo}: tag ruleset {NAME!r} (id {found[0]['id']})")
    print("  bypass now:  ", current.get("bypass_actors"))
    print("  bypass after:", payload["bypass_actors"])
    if dry_run:
        print("Dry run: nothing was changed.")
        return 0
    if payload["bypass_actors"] == (current.get("bypass_actors") or []):
        print("Already as wanted; nothing to do.")
        return 0
    _gh("api", "-X", "PUT", path, "--input", "-", stdin=json.dumps(payload))
    back = json.loads(_gh("api", path))
    wrong = verify(back, payload)
    if wrong:
        sys.exit("MISMATCH after the change: " + "; ".join(wrong) + ". Check Settings > Rules.")
    print("Applied and read back." + ("" if remove else " Undo with --remove."))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
