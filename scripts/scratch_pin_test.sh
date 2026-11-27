#!/usr/bin/env bash
# Scratch-branch test of pinning trazo/verdict to the reviewer App (#320, #212). Run by the owner.
#
#   scripts/scratch_pin_test.sh <reviewer-app-id> [<sha-with-app-success>]
#
# <reviewer-app-id> is the numeric "App ID" on https://github.com/settings/apps/trazo-reviewer.
# It touches ONLY: two scratch branches (scratch/pin-base, scratch/pin-head), one scratch ruleset
# named "scratch-pin-test" that targets only scratch/pin-base, and one scratch pull request between
# them. It never reads or writes the main ruleset, and refuses to continue if the ruleset it made
# would match any ref but scratch/pin-base. Everything is deleted on exit (trap), including on error.
#
# Cases, each printed with its raw output so the result can be pasted on the issue:
#   A. trazo/verdict=success set by the OWNER login is NOT enough: the pull request stays BLOCKED.
#   B. (only if <sha-with-app-success> is given) a head whose trazo/verdict success was set by the
#      reviewer App IS enough: the pull request is not BLOCKED. UNVERIFIED until run; at the time of
#      writing no commit in this repository carries an App success, only App failures.
#   C. with the owner (repository Admin role) as bypass actor, the owner's own merge into the scratch
#      base still works.
#   D. rollback rehearsal: scripts/rollback_ruleset.sh restores the scratch ruleset to the saved
#      pre-pin JSON and reports an exact match.
# UNVERIFIED: the Admin role's bypass actor_id 5 (same assumption as scripts/protect_release_tags.py).
set -euo pipefail
app_id=${1:?usage: scratch_pin_test.sh <reviewer-app-id> [<sha-with-app-success>]}
pos_sha=${2:-}
[[ "$app_id" =~ ^[0-9]+$ ]] || { echo "app id must be a number" >&2; exit 2; }
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo=${REPO:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}
base=scratch/pin-base head=scratch/pin-head rs_name=scratch-pin-test
work=$(mktemp -d)
rs_id="" pr=""
cleanup() {
  set +e
  [[ -n "$pr" ]] && gh pr close "$pr" -R "$repo" >/dev/null 2>&1
  [[ -n "$rs_id" ]] && gh api -X DELETE "repos/${repo}/rulesets/${rs_id}" >/dev/null 2>&1
  gh api -X DELETE "repos/${repo}/git/refs/heads/${head}" >/dev/null 2>&1
  gh api -X DELETE "repos/${repo}/git/refs/heads/${base}" >/dev/null 2>&1
  rm -rf "$work"
  echo "cleanup done: scratch ruleset ${rs_id:-none}, branches ${base} and ${head}, PR ${pr:-none}"
}
trap cleanup EXIT

main_sha=$(gh api "repos/${repo}/git/ref/heads/main" -q .object.sha)
gh api -X POST "repos/${repo}/git/refs" -f ref="refs/heads/${base}" -f sha="$main_sha" >/dev/null
# A head one commit ahead of the base, made through the API so nothing is checked out.
tree=$(gh api "repos/${repo}/git/commits/${main_sha}" -q .tree.sha)
commit=$(gh api -X POST "repos/${repo}/git/commits" -f message="scratch: pin test" -f tree="$tree" -f "parents[]=${main_sha}" -q .sha)
gh api -X POST "repos/${repo}/git/refs" -f ref="refs/heads/${head}" -f sha="$commit" >/dev/null

# Scratch ruleset: only scratch/pin-base, trazo/verdict pinned to the reviewer App, NO bypass yet.
jq -n --arg name "$rs_name" --argjson app "$app_id" '{
  name: $name, target: "branch", enforcement: "active",
  conditions: {ref_name: {include: ["refs/heads/scratch/pin-base"], exclude: []}},
  rules: [{type: "required_status_checks", parameters: {strict_required_status_checks_policy: false,
    do_not_enforce_on_create: false, required_status_checks: [{context: "trazo/verdict", integration_id: $app}]}}],
  bypass_actors: []}' > "$work/pinned.json"
jq -n --arg name "$rs_name" '{
  name: $name, target: "branch", enforcement: "active",
  conditions: {ref_name: {include: ["refs/heads/scratch/pin-base"], exclude: []}},
  rules: [{type: "required_status_checks", parameters: {strict_required_status_checks_policy: false,
    do_not_enforce_on_create: false, required_status_checks: [{context: "trazo/verdict"}]}}],
  bypass_actors: []}' > "$work/before.json"
# Create it unpinned first so there is a saved pre-pin copy to roll back to (case D).
rs_id=$(gh api -X POST "repos/${repo}/rulesets" --input "$work/before.json" -q .id)
live=$(gh api "repos/${repo}/rulesets/${rs_id}" -q '.conditions.ref_name.include|join(",")')
[[ "$live" == "refs/heads/scratch/pin-base" ]] || { echo "scratch ruleset targets ${live}; refusing" >&2; exit 1; }
[[ "$rs_id" != "24085136" ]] || { echo "refusing: that is the main ruleset" >&2; exit 1; }
norm='{name,target,enforcement,conditions,rules,bypass_actors}'
gh api "repos/${repo}/rulesets/${rs_id}" | jq -S "$norm" > "$work/saved.json"
gh api -X PUT "repos/${repo}/rulesets/${rs_id}" --input "$work/pinned.json" >/dev/null
echo "== pinned ruleset ${rs_id}:"; gh api "repos/${repo}/rulesets/${rs_id}" -q '.rules[0].parameters.required_status_checks'

pr=$(gh pr create -R "$repo" --base "$base" --head "$head" --title "scratch: pin test (do not merge)" --body "Scratch pin test for #320. Closed by the script." | grep -oE '[0-9]+$')
state() { gh pr view "$pr" -R "$repo" --json mergeStateStatus -q .mergeStateStatus; }

echo "== A. verdict success from the owner login"
gh api -X POST "repos/${repo}/statuses/${commit}" -f state=success -f context=trazo/verdict -f description="scratch: owner-set" >/dev/null
sleep 5; echo "mergeStateStatus: $(state)   (expected BLOCKED)"

if [[ -n "$pos_sha" ]]; then
  echo "== B. head whose verdict success came from the reviewer App: ${pos_sha}"
  who=$(gh api "repos/${repo}/commits/${pos_sha}/statuses" -q '[.[]|select(.context=="trazo/verdict" and .state=="success")][0].creator.login')
  echo "success set by: ${who}   (must be the reviewer App bot)"
  gh api -X PATCH "repos/${repo}/git/refs/heads/${head}" -f sha="$pos_sha" -F force=true >/dev/null
  sleep 5; echo "mergeStateStatus: $(state)   (expected not BLOCKED)"
  gh api -X PATCH "repos/${repo}/git/refs/heads/${head}" -f sha="$commit" -F force=true >/dev/null
else
  echo "== B. skipped: no <sha-with-app-success> given"
fi

echo "== C. owner as bypass actor (Admin role), then the owner merges into the scratch base"
jq '.bypass_actors = [{actor_id: 5, actor_type: "RepositoryRole", bypass_mode: "always"}]' "$work/pinned.json" > "$work/bypass.json"
gh api -X PUT "repos/${repo}/rulesets/${rs_id}" --input "$work/bypass.json" >/dev/null
gh api "repos/${repo}/rulesets/${rs_id}" -q '{current_user_can_bypass, bypass_actors}'
gh pr merge "$pr" -R "$repo" --squash --admin && echo "owner merge into ${base}: OK" || echo "owner merge into ${base}: FAILED"

echo "== D. rollback rehearsal on the scratch ruleset"
"$here/rollback_ruleset.sh" "$rs_id" "$work/saved.json"
