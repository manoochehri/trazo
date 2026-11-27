#!/usr/bin/env bash
# Scratch-ruleset test of scripts/drop_verdict_check.sh and its rollback (#380). Run by the owner; an agent
# cannot, because the guard blocks `gh api` writes. Same method as scripts/scratch_pin_test.sh (#365).
#
#   scripts/scratch_drop_verdict_test.sh
#
# It creates ONE ruleset named "scratch-drop-verdict-test" that targets only refs/heads/scratch/drop-verdict-test
# (a branch that does not exist), copies the main ruleset's rules into it, runs the drop script against it,
# checks the result, then runs scripts/rollback_ruleset.sh against it with the pre-drop copy. It never reads
# or writes the main ruleset's id and deletes the scratch ruleset on exit (trap), including on error.
set -euo pipefail
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo=${REPO:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}
rs_name=scratch-drop-verdict-test
work=$(mktemp -d)
rs_id=""
cleanup() {
  set +e
  if [[ -n "$rs_id" ]]; then
    gh api -X DELETE "repos/${repo}/rulesets/${rs_id}" >/dev/null 2>&1 || echo "WARNING: scratch ruleset ${rs_id} was NOT deleted; delete it by hand" >&2
  fi
  rm -rf "$work"
  echo "cleanup done: scratch ruleset ${rs_id:-none}"
}
trap cleanup EXIT
jq --arg n "$rs_name" '{name: $n, target, enforcement, rules, bypass_actors: [],
  conditions: {ref_name: {include: ["refs/heads/scratch/drop-verdict-test"], exclude: []}}}' \
  "$here/rulesets/main-ruleset.saved.json" > "$work/scratch.json"
rs_id=$(gh api -X POST "repos/${repo}/rulesets" --input "$work/scratch.json" -q .id)
[[ "$rs_id" != "24085136" ]] || { echo "refusing: that is the main ruleset" >&2; exit 1; }
live=$(gh api "repos/${repo}/rulesets/${rs_id}" -q '.conditions.ref_name.include|join(",")')
[[ "$live" == "refs/heads/scratch/drop-verdict-test" ]] || { echo "scratch ruleset targets ${live}; refusing" >&2; exit 1; }
norm='{name,target,enforcement,conditions,rules,bypass_actors}'
gh api "repos/${repo}/rulesets/${rs_id}" | jq -S "$norm" > "$work/before.json"
echo "== drop"
"$here/drop_verdict_check.sh" "$rs_id" "$rs_name"
ctx=$(gh api "repos/${repo}/rulesets/${rs_id}" -q '[.rules[] | select(.type=="required_status_checks") | .parameters.required_status_checks[].context] | join(",")')
echo "required after drop: ${ctx}   (expected secrets-scan,docker,test,docs-updated)"
[[ "$ctx" == "secrets-scan,docker,test,docs-updated" ]] || { echo "FAILED" >&2; exit 1; }
echo "== rollback"
"$here/rollback_ruleset.sh" "$rs_id" "$work/before.json"
echo "PASS: drop and rollback both verified on the scratch ruleset"
