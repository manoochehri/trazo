#!/usr/bin/env bash
# Print a draft release note section from the closed issues in its GitHub milestone.
# Review and commit the result before running scripts/release.sh; this command never edits files.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
VERSION="$(tr -d '[:space:]' < .template/VERSION)"

usage() {
  cat >&2 <<'USAGE'
Usage: scripts/changelog.sh [--version X.Y.Z]

Print a Markdown changelog entry from closed issues in milestone vX.Y.Z.
Defaults to the version in .template/VERSION.
USAGE
}

die() { echo "changelog.sh: $*" >&2; exit 1; }

while [ "$#" -gt 0 ]; do
  case "$1" in
    --version)
      [ "$#" -ge 2 ] || { usage; exit 2; }
      VERSION="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage
      die "unknown argument '$1'"
      ;;
  esac
done

[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] ||
  die "version must be MAJOR.MINOR.PATCH, got '$VERSION'"
command -v gh >/dev/null 2>&1 || die "gh not found; cannot read milestone v$VERSION"

if ! ISSUES="$(gh issue list --state closed --milestone "v$VERSION" --limit 1000 \
    --json number,title --jq 'sort_by(.number) | .[] | "- #\(.number) \(.title)"')"; then
  die "could not query closed issues for milestone v$VERSION"
fi
[ -n "$ISSUES" ] || die "milestone v$VERSION has no closed issues; refusing to draft an empty entry"

printf '## %s (%s)\n%s\n' "$VERSION" "$(date +%F)" "$ISSUES"
