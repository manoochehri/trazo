#!/usr/bin/env bash
# One-time OWNER script (#380, from the architect finding on #377): stop requiring trazo/verdict in the
# "protect main" ruleset. Run by the repository owner, never by an agent: changing a ruleset is a
# human-only limit (rules.md, "Safety limits are human-only").
#
#   scripts/drop_verdict_check.sh --dry-run    # show the change, write nothing
#   scripts/drop_verdict_check.sh              # apply it, read it back, verify
#   scripts/rollback_ruleset.sh                # ONE-COMMAND ROLLBACK: restores the saved ruleset
#
# Why: owner-merge.yml already demands trazo/verdict AND trazo/security on a risky diff and nothing on a
# docs-only one (ADR 0031). The ruleset entry only made that relaxation inert. The four CI checks
# (secrets-scan, docker, test, docs-updated) stay required, as do PR-required, no-deletion and no-force-push.
# This removes one entry and nothing else; the script refuses if any other required check would change.
#
# Optional: scripts/drop_verdict_check.sh [--dry-run] [<ruleset-id> [<expected-name>]] to point it at a
# scratch ruleset (scripts/scratch_drop_verdict_test.sh does this).
set -euo pipefail
dry=0
args=()
for a in "$@"; do if [[ "$a" == "--dry-run" ]]; then dry=1; else args+=("$a"); fi; done
MAIN_RULESET_ID=24085136
id=${args[0]:-$MAIN_RULESET_ID}
expect=${args[1]:-protect main}
repo=${REPO:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}
[[ "$id" =~ ^[0-9]+$ ]] || { echo "ruleset id must be a number" >&2; exit 2; }
norm='{name,target,enforcement,conditions,rules,bypass_actors}'
ctxs='[.rules[] | select(.type=="required_status_checks") | .parameters.required_status_checks[].context]'
live=$(gh api "repos/${repo}/rulesets/${id}" | jq -S "$norm")
name=$(jq -r .name <<<"$live")
[[ "$name" == "$expect" ]] || { echo "refusing: ruleset ${id} is named '${name}', expected '${expect}'" >&2; exit 2; }
want=$(jq -S '(.rules[] | select(.type == "required_status_checks") | .parameters.required_status_checks)
  |= map(select(.context != "trazo/verdict"))' <<<"$live")
# Only trazo/verdict may differ, and something must remain required.
before=$(jq -r "${ctxs} | map(select(. != \"trazo/verdict\")) | join(\",\")" <<<"$live")
after=$(jq -r "${ctxs} | join(\",\")" <<<"$want")
[[ "$before" == "$after" && -n "$after" ]] || { echo "refusing: removal would change more than trazo/verdict" >&2; exit 2; }
echo "${repo} ruleset ${id} '${name}'"
echo "  required checks now:   $(jq -r "${ctxs} | join(\", \")" <<<"$live")"
echo "  required checks after: ${after//,/, }"
if [[ "$dry" == 1 ]]; then echo "Dry run: nothing was changed."; exit 0; fi
if [[ "$live" == "$want" ]]; then echo "trazo/verdict is already not required; nothing to do."; exit 0; fi
printf '%s' "$want" | gh api -X PUT "repos/${repo}/rulesets/${id}" --input - >/dev/null
got=$(gh api "repos/${repo}/rulesets/${id}" | jq -S "$norm")
if [[ "$got" == "$want" ]]; then
  echo "Applied: live ruleset equals the intended copy. Roll back with scripts/rollback_ruleset.sh"
else
  echo "MISMATCH after apply; run scripts/rollback_ruleset.sh. diff (live vs intended):" >&2
  diff <(printf '%s\n' "$got") <(printf '%s\n' "$want") >&2 || true
  exit 1
fi
