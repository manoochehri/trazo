#!/usr/bin/env bash
# One-command rollback for a repository ruleset (#320). Run by the repository owner, not an agent.
#
#   scripts/rollback_ruleset.sh                       # restore the main ruleset from the saved copy
#   scripts/rollback_ruleset.sh <ruleset-id> <file>   # restore any ruleset from a saved JSON file
#
# It PUTs the saved JSON over the live ruleset, reads it back, and exits non-zero unless the live
# ruleset equals the file exactly (after dropping GitHub's read-only fields). The saved copy for main
# is scripts/rulesets/main-ruleset.saved.json, taken 2026-11-27 before any pin. Changing a ruleset is a
# human-only limit (rules.md, "Safety limits are human-only").
set -euo pipefail
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
MAIN_RULESET_ID=24085136
id=${1:-$MAIN_RULESET_ID}
file=${2:-$here/rulesets/main-ruleset.saved.json}
repo=${REPO:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}
[[ "$id" =~ ^[0-9]+$ ]] || { echo "ruleset id must be a number" >&2; exit 2; }
[[ -f "$file" ]] || { echo "no such file: $file" >&2; exit 2; }
norm='{name,target,enforcement,conditions,rules,bypass_actors}'
want=$(jq -S "$norm" "$file")
printf '%s' "$want" | gh api -X PUT "repos/${repo}/rulesets/${id}" --input - >/dev/null
got=$(gh api "repos/${repo}/rulesets/${id}" | jq -S "$norm")
if [[ "$got" == "$want" ]]; then
  echo "restored ruleset ${id} on ${repo}: live copy equals ${file}"
else
  echo "MISMATCH after restore of ruleset ${id}; diff (live vs saved):" >&2
  diff <(printf '%s\n' "$got") <(printf '%s\n' "$want") >&2 || true
  exit 1
fi
