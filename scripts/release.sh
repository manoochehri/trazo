#!/usr/bin/env bash
# Cut a Trazo release.
#
# Trazo is consumed by mounting `.trazo/` into another repo, so "latest" has to mean
# one unambiguous, immutable thing. That is the highest semver git tag, and nothing
# else — see `.trazo/project/adr/0006-release-process.md`. A branch is mutable and a plain file
# is not resolvable, so `.template/VERSION` alone cannot be what a consumer pins to.
#
# Usage:
#   scripts/release.sh [--dry-run]
#
# What it does, in order, refusing to proceed on any failure:
#   1. require a clean tree on the default branch, level with origin
#   2. require `.template/VERSION` to be present and MAJOR.MINOR.PATCH
#   3. require that version to have a `.template/CHANGELOG.md` entry
#   4. require the tag not to exist already
#   5. create an annotated tag `vX.Y.Z` and, unless --dry-run, push it
#
# The tag is what a consumer resolves; the commit it points at is the release.
# Bumping the version and writing the changelog entry happen *before* this runs,
# because the release commit has to exist before it can be tagged.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

VERSION_FILE=".template/VERSION"
CHANGELOG=".template/CHANGELOG.md"
DEFAULT_BRANCH="$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|^origin/||' || true)"
DEFAULT_BRANCH="${DEFAULT_BRANCH:-main}"

DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    -h|--help) sed -n '3,19p' "$0" | sed 's/^#\{1\} \{0,1\}//'; exit 0 ;;
    *) echo "release.sh: unknown argument '$arg' (expected --dry-run)" >&2; exit 2 ;;
  esac
done

die() { echo "release.sh: $*" >&2; exit 1; }

# --- 1. clean tree, on the default branch, level with origin ------------------------
# A release must be reproducible from the tag alone. Tagging a dirty or off-branch
# tree would publish something no consumer can reproduce.

if [ -n "$(git status --porcelain)" ]; then
  die "working tree is not clean; commit or stash first"
fi

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [ "$BRANCH" != "$DEFAULT_BRANCH" ]; then
  die "releases are cut from '$DEFAULT_BRANCH', not '$BRANCH'"
fi

if ! git rev-parse --verify --quiet "refs/remotes/origin/$DEFAULT_BRANCH" >/dev/null; then
  die "no origin/$DEFAULT_BRANCH found; releases are cut from a pushed commit"
fi

# `merge-base --is-ancestor` is the right question: is the commit being tagged already
# contained in the pushed default branch? `git diff` would only compare trees and would
# pass for a local commit that happens to have identical content.
if ! git merge-base --is-ancestor HEAD "origin/$DEFAULT_BRANCH"; then
  die "HEAD is not on origin/$DEFAULT_BRANCH; push or rebase first"
fi

# --- 2. version present and semver -------------------------------------------------

[ -f "$VERSION_FILE" ] || die "$VERSION_FILE not found"
VERSION="$(tr -d '[:space:]' < "$VERSION_FILE")"
[ -n "$VERSION" ] || die "$VERSION_FILE is empty"

# Intentionally strict: MAJOR.MINOR.PATCH only. Prereleases would mean deciding what a
# consumer resolves by default, which ADR 0006 deliberately left open.
if ! printf '%s' "$VERSION" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$'; then
  die "$VERSION_FILE is '$VERSION', expected MAJOR.MINOR.PATCH"
fi

TAG="v$VERSION"

# --- 3. changelog has an entry for this version ------------------------------------
# Otherwise the tag would ship a version nobody can describe, and the changelog is what
# a consumer reads to decide whether upgrading is worth it.

[ -f "$CHANGELOG" ] || die "$CHANGELOG not found"
if ! grep -qE "^## ${VERSION//./\\.} \(" "$CHANGELOG"; then
  die "$CHANGELOG has no '## $VERSION (' entry; write it before releasing"
fi

# --- 4. the tag must not already exist ---------------------------------------------
# Re-tagging in place would silently move a version a consumer may already hold.

if git rev-parse -q --verify "refs/tags/$TAG" >/dev/null 2>&1; then
  die "tag $TAG already exists; bump $VERSION_FILE to release a new version"
fi

# --- 5. tag ------------------------------------------------------------------------

echo "Releasing $TAG"
echo "  version:   $VERSION"
echo "  commit:    $(git rev-parse --short HEAD)"
echo "  changelog: $CHANGELOG ($VERSION)"

if [ "$DRY_RUN" -eq 1 ]; then
  echo
  echo "--dry-run: not tagging."
  echo "  would run: git tag -a $TAG -m 'Trazo $VERSION'"
  echo "  would run: git push origin $TAG"
  exit 0
fi

git tag -a "$TAG" -m "Trazo $VERSION"
echo "  created: $TAG -> $(git rev-parse --short "$TAG")"

git push origin "$TAG"
echo "  pushed:   origin/$TAG"
echo
echo "Published. A consumer resolves 'latest' as this tag."
