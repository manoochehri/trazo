#!/bin/sh
# Runs inside the gitleaks container (Alpine + git), invoked by scripts/scan.sh.
#
# gitleaks exits 0 after scanning 0 commits: in a git worktree whose shared git dir
# is not mounted, it resolves no repository, scans nothing, prints "no leaks found"
# and still succeeds (issue #43). A secrets gate that cannot tell what it scanned
# must fail loudly instead, so prove git can read the history here before scanning.
#
# Usage: scan-preflight.sh [repo-path]   (repo-path defaults to /repo)
set -eu

repo="${1:-/repo}"

if ! git -C "$repo" rev-parse --git-dir >/dev/null 2>&1; then
    echo "error: make scan: git cannot resolve a repository at $repo" >&2
    echo "hint: a worktree's .git file points at the shared git dir outside the working tree, which must be mounted too" >&2
    exit 2
fi

commits="$(git -C "$repo" rev-list --count --all 2>/dev/null || echo 0)"
if [ "${commits:-0}" -eq 0 ]; then
    echo "error: make scan: $repo holds no commits to scan; refusing to report success" >&2
    exit 2
fi

exec gitleaks git "$repo"
