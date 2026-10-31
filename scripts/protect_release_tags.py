"""Restrict who can create or move release tags (#263). Run by the repository owner, not an agent.

`scripts/install.sh` resolves `latest` to the highest `vX.Y.Z` tag, and the tag ruleset only blocks
deleting and force-moving tags, so anyone who can push a tag could publish a release that every
host installing `latest` would take. This adds the `creation` and `update` rules to the tag ruleset
and lists the repository Admin role as a bypass actor, so `make release` still works for the owner
and nobody else, including an agent token, can publish a `v*` tag.

Changing a ruleset is a human-only limit (rules.md, "Safety limits are human-only"): run it
yourself.

    python3 scripts/protect_release_tags.py --dry-run   # show the change, write nothing
    python3 scripts/protect_release_tags.py             # apply it, then read it back

UNVERIFIED: the Admin role's `actor_id` below (5) is from GitHub's role numbering, not from the REST
documentation, which does not state it. The script reads the ruleset back after the change and
prints it, so a wrong id shows up immediately; fix it in the repository's Settings > Rules if it
does.
"""

import json
import shutil
import subprocess  # noqa: S404 - only used to call the resolved `gh` executable
import sys

ADMIN = {"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}
ADDED_RULES = ("creation", "update")
RULESET_NAME = "v"


def build_payload(current: dict) -> dict:
    """The ruleset body to PUT: existing rules kept, creation and update added, Admin may bypass."""
    rules = [
        {key: value for key, value in rule.items() if key in ("type", "parameters")}
        for rule in current["rules"]
    ]
    present = {rule["type"] for rule in rules}
    rules += [{"type": name} for name in ADDED_RULES if name not in present]
    actors = list(current.get("bypass_actors") or [])
    if not any(
        actor.get("actor_type") == ADMIN["actor_type"]
        and actor.get("actor_id") == ADMIN["actor_id"]
        for actor in actors
    ):
        actors.append(dict(ADMIN))
    return {
        "name": current["name"],
        "target": current["target"],
        "enforcement": current["enforcement"],
        "conditions": current["conditions"],
        "bypass_actors": actors,
        "rules": rules,
    }


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
    dry_run = "--dry-run" in argv
    repo = _gh("repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner").strip()
    rulesets = json.loads(_gh("api", f"repos/{repo}/rulesets"))
    matches = [r for r in rulesets if r["target"] == "tag" and r["name"] == RULESET_NAME]
    if len(matches) != 1:
        sys.exit(
            f"Expected one tag ruleset named {RULESET_NAME!r} in {repo}, found {len(matches)}."
        )
    path = f"repos/{repo}/rulesets/{matches[0]['id']}"
    current = json.loads(_gh("api", path))
    payload = build_payload(current)
    print(
        f"Ruleset {matches[0]['id']} ({repo}), refs {current['conditions']['ref_name']['include']}"
    )
    print("  rules now:   ", [rule["type"] for rule in current["rules"]])
    print("  rules after: ", [rule["type"] for rule in payload["rules"]])
    print("  bypass now:  ", current.get("bypass_actors") or [])
    print("  bypass after:", payload["bypass_actors"])
    if dry_run:
        print("Dry run: nothing was changed.")
        return 0
    _gh("api", "-X", "PUT", path, "--input", "-", stdin=json.dumps(payload))
    after = json.loads(_gh("api", path))
    print("Applied. Read back:")
    print("  rules:  ", [rule["type"] for rule in after["rules"]])
    print("  bypass: ", after.get("bypass_actors"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
