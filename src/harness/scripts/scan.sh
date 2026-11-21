#!/usr/bin/env bash
# Local secrets gate: scan the repo's full git history for secrets. Called by
# `make scan`. See scripts/scan-preflight.sh for the in-container guard.
set -euo pipefail

image="${GITLEAKS_IMAGE:-zricethezav/gitleaks:latest}"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

die() { echo "error: make scan: $*" >&2; exit 2; }

git rev-parse --git-dir >/dev/null 2>&1 || die "not inside a git repository; refusing to report success"

root="$(git rev-parse --show-toplevel)"
common="$(git rev-parse --git-common-dir)"
# --git-common-dir is relative to the cwd (e.g. "../.git") unless it is already absolute.
case "$common" in
    /*) ;;
    *) common="$(cd "$common" && pwd)" ;;
esac

mounts=(-v "$root:/repo")
# In a worktree `.git` is a file whose `gitdir:` points at <main>/.git/worktrees/<name>,
# outside the working tree. Mount the shared git dir at the same absolute path so the
# container's git can follow the pointer instead of scanning 0 commits (issue #43).
if [ -f "$root/.git" ]; then
    mounts+=(-v "$common:$common")
fi

exec docker run --rm \
    "${mounts[@]}" \
    -v "$here/scan-preflight.sh:/scan-preflight.sh:ro" \
    --entrypoint sh \
    "$image" /scan-preflight.sh /repo
