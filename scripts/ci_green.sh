#!/usr/bin/env bash
# Exit 0 only if every check run on a commit is green, ignoring the running release job itself (#380).
#
#   scripts/ci_green.sh <sha>
#
# Env: GITHUB_REPOSITORY, GITHUB_RUN_ID (this workflow run), SELF_JOB (this job's check-run name).
# The dispatched release job is itself an in-progress check run on the commit it is about to tag, so it
# would read as pending forever. It is excluded only when BOTH its name is SELF_JOB and its details_url
# is under this run (/actions/runs/<GITHUB_RUN_ID>/); a same-named check from anywhere else still counts.
# Only the latest run of each check name counts (highest id), as in owner-merge.yml: a re-run leaves old
# failed or cancelled runs in the list. A latest run with no conclusion is pending. No runs at all refuses.
set -euo pipefail
sha=${1:?usage: ci_green.sh <sha>}
[[ "$sha" =~ ^[0-9a-f]{40}$ ]] || { echo "not a commit sha" >&2; exit 2; }
: "${GITHUB_REPOSITORY:?}" "${GITHUB_RUN_ID:?}" "${SELF_JOB:?}"
rows=$(gh api --paginate "repos/${GITHUB_REPOSITORY}/commits/${sha}/check-runs?per_page=100" \
  | jq -r --arg self "$SELF_JOB" --arg run "/actions/runs/${GITHUB_RUN_ID}/" '
      .check_runs[]
      | select((.name == $self and ((.details_url // "") | contains($run))) | not)
      | [.name, (.id | tostring), (.conclusion // "pending")] | @tsv')
latest=$(sort -t "$(printf '\t')" -k1,1 -k2,2n <<<"$rows" \
  | awk -F '\t' 'NF { l[$1] = $3 } END { for (n in l) print n "\t" l[n] }')
if [[ -z "$latest" ]]; then echo "no other check runs on ${sha}; not tagging" >&2; exit 1; fi
bad=$(awk -F '\t' '$2 != "success" && $2 != "skipped"' <<<"$latest")
if [[ -n "$bad" ]]; then
  echo "CI is not green on ${sha}:" >&2
  echo "$bad" >&2
  exit 1
fi
echo "CI green on ${sha}"
