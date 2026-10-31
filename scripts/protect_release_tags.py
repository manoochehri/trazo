"""Restrict who can create or move release tags (#263). Run by the repository owner, not an agent.

`scripts/install.sh` resolves `latest` to the highest `vX.Y.Z` tag, and the tag ruleset only blocks
deleting and force-moving tags, so anyone who can push a tag could publish a release that every
host installing `latest` would take. This makes two changes, and neither loosens anything:

1. It adds the `update` rule to the existing tag ruleset `v`, with no bypass. `scripts/release.sh`
   only creates tags, so nothing in the release flow needs to update one.
2. It adds a second tag ruleset, `v-create`, with only the `creation` rule and the repository Admin
   role as its bypass actor. A bypass actor covers every rule in its own ruleset, so the bypass is
   kept out of `v`, whose deletion and force-move protection stays absolute.

Who this stops: collaborators below Admin, GitHub Apps and the built-in `GITHUB_TOKEN`. Who it does
not stop: the owner's own account, and any agent session running as the owner (#44).

Changing a ruleset is a human-only limit (rules.md, "Safety limits are human-only"): run it
yourself.

    python3 scripts/protect_release_tags.py --dry-run   # show the change, write nothing
    python3 scripts/protect_release_tags.py             # apply it, then check it

UNVERIFIED: the Admin role's `actor_id` below (5) is the commonly cited GitHub role numbering, not
something GitHub's REST documentation states. After creating `v-create` the script reads it back
and requires `current_user_can_bypass` to be "always" for you; if it is not, it deletes the ruleset
it just created and exits non-zero, so a wrong id cannot lock you out of tagging a release.

Running it again is safe: an existing `v-create` is never edited (a hand edit, or a bypass added
later for automatic tagging, would be lost). If it already does its job the script leaves it alone;
if it does not, the script says what is wrong and changes nothing.
"""

import json
import shutil
import subprocess
import sys

ADMIN = {"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}
RULESET_NAME = "v"
CREATE_RULESET_NAME = "v-create"


def _keep(rules: list[dict]) -> list[dict]:
    return [
        {key: value for key, value in r.items() if key in ("type", "parameters")} for r in rules
    ]


def tighten_payload(current: dict) -> dict:
    """The body for ruleset `v`: the same rules plus `update`, and the same bypass actors."""
    rules = _keep(current["rules"])
    if not any(rule["type"] == "update" for rule in rules):
        rules.append({"type": "update"})
    return {
        "name": current["name"],
        "target": current["target"],
        "enforcement": current["enforcement"],
        "conditions": current["conditions"],
        "bypass_actors": list(current.get("bypass_actors") or []),
        "rules": rules,
    }


def create_payload(current: dict) -> dict:
    """The body for `v-create`: only `creation`, on the same refs, with Admin as the only bypass."""
    return {
        "name": CREATE_RULESET_NAME,
        "target": "tag",
        "enforcement": "active",
        "conditions": current["conditions"],
        "bypass_actors": [dict(ADMIN)],
        "rules": [{"type": "creation"}],
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


def _tag_rulesets(rulesets: list[dict], name: str) -> list[dict]:
    return [r for r in rulesets if r["target"] == "tag" and r["name"] == name]


def _existing_problems(detail: dict) -> list[str]:
    """What is wrong with an existing `v-create` ruleset; empty means it already does its job."""
    problems = []
    if not any(rule["type"] == "creation" for rule in detail["rules"]):
        problems.append("it has no creation rule")
    if detail.get("enforcement") != "active":
        problems.append(f"its enforcement is {detail.get('enforcement')!r}, not 'active'")
    can_bypass = detail.get("current_user_can_bypass")
    if can_bypass is not None and can_bypass != "always":
        problems.append(f"current_user_can_bypass is {can_bypass!r}, not 'always'")
    return problems


def main(argv: list[str]) -> int:
    unknown = [arg for arg in argv if arg != "--dry-run"]
    if unknown:
        sys.exit(
            f"Unknown argument(s) {unknown}; nothing was changed. Use --dry-run or no arguments."
        )
    dry_run = "--dry-run" in argv
    repo = _gh("repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner").strip()
    rulesets = json.loads(_gh("api", f"repos/{repo}/rulesets"))
    base = _tag_rulesets(rulesets, RULESET_NAME)
    if len(base) != 1:
        sys.exit(f"Expected one tag ruleset named {RULESET_NAME!r} in {repo}, found {len(base)}.")
    existing = _tag_rulesets(rulesets, CREATE_RULESET_NAME)
    if len(existing) > 1:
        sys.exit(f"Found {len(existing)} tag rulesets named {CREATE_RULESET_NAME!r} in {repo}.")
    base_path = f"repos/{repo}/rulesets/{base[0]['id']}"
    current = json.loads(_gh("api", base_path))
    if current.get("enforcement") != "active":
        sys.exit(
            f"Ruleset {RULESET_NAME!r} is {current.get('enforcement')!r}, not 'active'. "
            "Nothing was changed; fix that first."
        )
    tighten, create = tighten_payload(current), create_payload(current)
    if existing:
        detail = json.loads(_gh("api", f"repos/{repo}/rulesets/{existing[0]['id']}"))
        problems = _existing_problems(detail)
        if problems:
            sys.exit(
                f"{CREATE_RULESET_NAME!r} already exists and does not do its job: "
                f"{'; '.join(problems)}. This script never edits an existing one (a hand edit or "
                "a later bypass would be lost); fix it in Settings > Rules. Nothing was changed."
            )
    print(
        f"{repo}: tag ruleset {RULESET_NAME!r} (id {base[0]['id']}), "
        f"enforcement {current['enforcement']!r}, "
        f"refs {current['conditions']['ref_name']['include']}"
    )
    print("  v rules now:  ", [rule["type"] for rule in current["rules"]])
    print("  v rules after:", [rule["type"] for rule in tighten["rules"]], "(bypass unchanged)")
    status = (
        "already in place, left alone" if existing else "create new (creation rule, Admin bypass)"
    )
    print(f"  {CREATE_RULESET_NAME}: {status}")
    if dry_run:
        print("Dry run: nothing was changed.")
        return 0
    _gh("api", "-X", "PUT", base_path, "--input", "-", stdin=json.dumps(tighten))
    if existing:
        print(
            f"Applied. v now has {[rule['type'] for rule in tighten['rules']]}; "
            f"{CREATE_RULESET_NAME} was already in place."
        )
        return 0
    saved = json.loads(
        _gh("api", "-X", "POST", f"repos/{repo}/rulesets", "--input", "-", stdin=json.dumps(create))
    )
    created_path = f"repos/{repo}/rulesets/{saved['id']}"
    check = json.loads(_gh("api", created_path))
    can_bypass = check.get("current_user_can_bypass")
    if can_bypass is not None and can_bypass != "always":
        try:
            _gh("api", "-X", "DELETE", created_path)
        except SystemExit as failure:
            sys.exit(
                f"current_user_can_bypass is {can_bypass!r}, not 'always', and removing the new "
                f"ruleset (id {saved['id']}) failed: {failure}. Remove {CREATE_RULESET_NAME!r} in "
                "Settings > Rules now, or you cannot tag a release."
            )
        sys.exit(
            f"After the change current_user_can_bypass is {can_bypass!r}, not 'always': the Admin "
            "role id is probably wrong, which would stop you tagging releases. I removed the new "
            f"{CREATE_RULESET_NAME!r} ruleset again. Ruleset v still has the added 'update' rule."
        )
    note = (
        "" if can_bypass else " (current_user_can_bypass was not reported; check Settings > Rules)"
    )
    print(
        f"Applied. v now has {[rule['type'] for rule in tighten['rules']]}; "
        f"{CREATE_RULESET_NAME} is in place{note}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
