#!/usr/bin/env bash
# Install, upgrade or remove Trazo in a host repository.
#
# Usage (run from the host repository root):
#   install.sh install   <tag> [--adapter claude|agents|both] [--source <path-or-url>]
#   install.sh upgrade   <tag> [--adapter ...] [--source ...] [--dry-run]
#   install.sh uninstall [--purge]
#
# <tag> is an exact release tag such as v0.1.0, or `latest`, which resolves to the highest
# vMAJOR.MINOR.PATCH tag at the source. There is no default tag: with none, this refuses.
# The source defaults to $TRAZO_SOURCE, then the public repository. `--source` accepts any
# git URL or a local path, which is how the tests run without a network.
#
# What it touches, and what it never touches (ADR 0010, 0011):
#   .trazo/            managed: replaced from src/overlay/ at the tag; VERSION records the tag
#   .trazo/project/    the host's own. Created from blank templates only if absent; never
#                      overwritten, never removed except by `uninstall --purge`
#   AGENTS.md, CLAUDE.md
#                      only the <!-- trazo:begin --> ... <!-- trazo:end --> block. Content
#                      outside the markers is never read into, rewritten or removed
#   .claude/           agents/ and commands/ files; a name that is already the host's is
#                      installed as trazo-<name>.md. settings.json only if absent
#   .github/CODEOWNERS never edited; suggested lines are printed
#   .trazo/INSTALLED   manifest of the adapter files placed, so upgrade and uninstall touch
#                      only what this script put there

set -euo pipefail

DEFAULT_SOURCE="https://github.com/manoochehri/trazo.git"
BEGIN='<!-- trazo:begin -->'
END='<!-- trazo:end -->'

die() {
  echo "install.sh: $*" >&2
  exit 1
}

usage() {
  sed -n '2,/^$/p' "$0" | sed 's/^# \{0,1\}//' >&2
  exit "${1:-2}"
}

# ---------------------------------------------------------------- source

resolve_latest() {
  local src="$1" tag
  tag="$(git ls-remote --tags --refs "$src" 2>/dev/null |
    sed 's|.*refs/tags/||' | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | sort -t. -k1.2,1n -k2,2n -k3,3n |
    tail -n 1)" || true
  [ -n "$tag" ] || die "no vMAJOR.MINOR.PATCH tag found at $src"
  echo "$tag"
}

# fetch <source> <tag> <dest>: shallow clone of exactly that tag.
fetch() {
  local src="$1" tag="$2" dest="$3"
  git clone --quiet --depth 1 --branch "$tag" "$src" "$dest" >/dev/null 2>&1 ||
    die "cannot fetch tag '$tag' from $src (does the tag exist?)"
  [ -d "$dest/src/overlay" ] && [ -d "$dest/src/adapters" ] ||
    die "tag '$tag' has no src/overlay and src/adapters; it predates the installer layout"
}

# ---------------------------------------------------------------- marked blocks

# set_block <file> <body-file>: insert or replace the marked block; create the file if absent.
set_block() {
  local file="$1" body="$2" begins ends tmp
  if [ ! -e "$file" ]; then
    { echo "$BEGIN"; cat "$body"; echo "$END"; } >"$file"
    return
  fi
  begins="$(grep -cxF "$BEGIN" "$file" || true)"
  ends="$(grep -cxF "$END" "$file" || true)"
  if [ "$begins" = 0 ] && [ "$ends" = 0 ]; then
    # Append after a blank line; the host's own bytes stay exactly where they were.
    [ -z "$(tail -c1 "$file")" ] || echo >>"$file"
    { echo; echo "$BEGIN"; cat "$body"; echo "$END"; } >>"$file"
  elif [ "$begins" = 1 ] && [ "$ends" = 1 ]; then
    tmp="$(mktemp)"
    awk -v b="$BEGIN" -v e="$END" -v blk="$body" '
      $0 == b { print; while ((getline l < blk) > 0) print l; skip = 1; next }
      skip && $0 == e { skip = 0; print; next }
      !skip { print }' "$file" >"$tmp"
    cat "$tmp" >"$file"
    rm -f "$tmp"
  else
    die "$file has unbalanced trazo markers ($begins begin, $ends end); fix it by hand and retry"
  fi
}

# drop_block <file>: remove the marked block (and the one blank line set_block added before
# it). A file left empty is one this script created, so it is removed.
drop_block() {
  local file="$1" tmp
  [ -e "$file" ] || return 0
  grep -qxF "$BEGIN" "$file" || return 0
  tmp="$(mktemp)"
  awk -v b="$BEGIN" -v e="$END" '
    skip { if ($0 == e) skip = 0; next }
    $0 == b { held = 0; skip = 1; next }
    held { print ""; held = 0 }
    $0 == "" { held = 1; next }
    { print }
    END { if (held) print "" }' "$file" >"$tmp"
  if grep -q '[^[:space:]]' "$tmp"; then
    cat "$tmp" >"$file"
    echo "removed trazo block from $file"
  else
    rm -f "$file"
    echo "removed $file (it held only the trazo block)"
  fi
  rm -f "$tmp"
}

# ---------------------------------------------------------------- manifest

MANIFEST=.trazo/INSTALLED
P=.trazo/project

in_manifest() { [ -f "$MANIFEST" ] && grep -qxF "$1" "$MANIFEST"; }

# place_adapter_file <src> <dest-dir> <name>: write <dest-dir>/<name>, or trazo-<name> on a
# clash with a file this script did not place. Echoes the path written.
place_adapter_file() {
  local src="$1" dir="$2" name="$3" dest
  dest="$dir/$name"
  if [ -e "$dest" ] && ! in_manifest "$dest"; then
    dest="$dir/trazo-$name"
    echo "clash: $dir/$name is yours; installed as $dest" >&2
  elif [ ! -e "$dest" ] && in_manifest "$dir/trazo-$name"; then
    dest="$dir/trazo-$name"
  fi
  mkdir -p "$dir"
  case "$dest" in
    */trazo-*)
      # A prefixed agent must also be renamed inside, or it collides on `name:`.
      if [ "$(basename "$dir")" = agents ]; then
        awk '!d && /^name: / { sub(/^name: /, "name: trazo-"); d = 1 } { print }' "$src" >"$dest"
      else
        cp "$src" "$dest"
      fi ;;
    *) cp "$src" "$dest" ;;
  esac
  echo "$dest"
}

# ---------------------------------------------------------------- install / upgrade

do_install() {
  local mode="$1" tag="$2" source="$3" adapter="$4" dryrun="$5"
  local tmp new_managed f name dest placed kind

  case "$adapter" in claude | agents | both) ;; *) die "--adapter must be claude, agents or both" ;; esac
  [ -d .git ] || [ -f .git ] || die "run this from the root of a git repository"
  if [ "$mode" = upgrade ]; then
    [ -f .trazo/VERSION ] || die "no .trazo/VERSION here; nothing to upgrade (use install)"
  elif [ -f .trazo/VERSION ]; then
    echo "note: .trazo/VERSION is $(cat .trazo/VERSION); reinstalling at $tag"
  fi

  [ "$tag" != latest ] || tag="$(resolve_latest "$source")"
  [[ "$tag" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "tag must look like v1.2.3 (or 'latest'), got '$tag'"

  work="$(mktemp -d)"
  trap 'rm -rf "${work:-}"' EXIT
  fetch "$source" "$tag" "$work/repo"

  # Stage the managed copy of .trazo/ so upgrade can diff before it changes anything.
  new_managed="$work/new"
  mkdir -p "$new_managed"
  cp -R "$work/repo/src/overlay/." "$new_managed/"
  printf '%s\n' "$tag" >"$new_managed/VERSION"

  if [ "$mode" = upgrade ]; then
    echo "== diff of .trazo/ (installed -> $tag), .trazo/project/ excluded"
    tmp="$work/old"
    mkdir -p "$tmp"
    for f in .trazo/* ; do
      case "$f" in .trazo/project | .trazo/INSTALLED) continue ;; esac
      [ -e "$f" ] && cp -R "$f" "$tmp/"
    done
    diff -ru "$tmp" "$new_managed" || true
    echo "== end diff"
    if [ "$dryrun" = 1 ]; then
      echo "dry run: nothing changed"
      return 0
    fi
  fi

  # Managed part of .trazo/: everything except project/ and the manifest, replaced wholesale
  # so a file dropped upstream disappears here too.
  mkdir -p .trazo
  for f in .trazo/* .trazo/.[!.]*; do
    [ -e "$f" ] || continue
    case "$f" in .trazo/project | .trazo/INSTALLED) continue ;; esac
    rm -rf "$f"
  done
  cp -R "$new_managed/." .trazo/

  # The host's own state: templates only if absent.
  if [ -d .trazo/project ]; then
    echo ".trazo/project/ exists; left untouched"
  else
    mkdir -p .trazo/project/charter .trazo/project/adr .trazo/project/workstreams
    cp "$work/repo/src/overlay/templates/charter.md" .trazo/project/charter/charter.md
    cp -R "$work/repo/src/overlay/templates/docs/." .trazo/project/
    touch "$P/adr/.gitkeep" "$P/workstreams/.gitkeep"
    echo "created .trazo/project/ from blank templates"
  fi

  # Adapters. Rebuild the manifest from what is placed now.
  placed="$work/placed"
  : >"$placed"
  if [ "$adapter" = agents ] || [ "$adapter" = both ]; then
    set_block AGENTS.md "$work/repo/src/adapters/AGENTS.md"
    echo "AGENTS.md: trazo block set"
  fi
  if [ "$adapter" = claude ] || [ "$adapter" = both ]; then
    set_block CLAUDE.md "$work/repo/src/adapters/CLAUDE.md"
    echo "CLAUDE.md: trazo block set"
    for kind in agents commands; do
      for f in "$work/repo/src/adapters/claude/$kind"/*.md; do
        name="$(basename "$f")"
        dest="$(place_adapter_file "$f" ".claude/$kind" "$name")"
        echo "$dest" >>"$placed"
      done
    done
    if [ -e .claude/settings.json ] && ! in_manifest .claude/settings.json; then
      echo "note: .claude/settings.json is yours; not touched. Trazo's deny rules for secrets are in" \
        "src/adapters/claude/settings.json at $tag; merge them yourself."
    else
      mkdir -p .claude
      cp "$work/repo/src/adapters/claude/settings.json" .claude/settings.json
      echo .claude/settings.json >>"$placed"
    fi
  fi
  # Keep manifest entries from an earlier adapter choice that are still on disk.
  if [ -f "$MANIFEST" ]; then
    while IFS= read -r f; do
      [ -e "$f" ] && ! grep -qxF "$f" "$placed" && echo "$f" >>"$placed"
    done <"$MANIFEST"
  fi
  sort -u "$placed" >"$MANIFEST"

  echo "installed Trazo $tag"
  cat <<EOF

CODEOWNERS is never edited by this script. Safety limits are only limits if the owner
reviews them; add these lines to .github/CODEOWNERS (replace @owner):

  /.trazo/project/charter/   @owner
  /.claude/settings.json     @owner
  /.github/workflows/        @owner
  /.github/CODEOWNERS        @owner
EOF
}

# ---------------------------------------------------------------- uninstall

do_uninstall() {
  local purge="$1" f
  [ -d .trazo ] || die "no .trazo/ here; nothing to uninstall"
  if [ -f "$MANIFEST" ]; then
    while IFS= read -r f; do
      [ -n "$f" ] && [ -e "$f" ] && rm -f "$f" && echo "removed $f"
    done <"$MANIFEST"
  fi
  rmdir .claude/agents .claude/commands .claude 2>/dev/null || true
  drop_block AGENTS.md
  drop_block CLAUDE.md
  for f in .trazo/* .trazo/.[!.]*; do
    [ -e "$f" ] || continue
    [ "$f" = .trazo/project ] && continue
    rm -rf "$f"
  done
  if [ "$purge" = 1 ]; then
    rm -rf .trazo
    echo "removed .trazo/ including project/ (--purge)"
  elif [ -d .trazo/project ]; then
    echo "kept .trazo/project/ (yours); --purge removes it"
  else
    rmdir .trazo 2>/dev/null || true
  fi
  echo "uninstalled Trazo. .github/CODEOWNERS was not touched; remove the lines you added."
}

# ---------------------------------------------------------------- main

[ $# -ge 1 ] || usage
cmd="$1"
shift
tag="" adapter=both source="${TRAZO_SOURCE:-$DEFAULT_SOURCE}" dryrun=0 purge=0
while [ $# -gt 0 ]; do
  case "$1" in
    --adapter) [ $# -ge 2 ] || die "--adapter needs a value"; adapter="$2"; shift 2 ;;
    --source) [ $# -ge 2 ] || die "--source needs a value"; source="$2"; shift 2 ;;
    --dry-run) dryrun=1; shift ;;
    --purge) purge=1; shift ;;
    -h | --help) usage 0 ;;
    -*) die "unknown option $1" ;;
    *) [ -z "$tag" ] || die "unexpected argument $1"; tag="$1"; shift ;;
  esac
done

case "$cmd" in
  install | upgrade)
    [ -n "$tag" ] || die "$cmd needs an exact release tag, e.g. $0 $cmd v0.1.0"
    do_install "$cmd" "$tag" "$source" "$adapter" "$dryrun"
    ;;
  uninstall)
    [ -z "$tag" ] || die "uninstall takes no tag"
    do_uninstall "$purge"
    ;;
  -h | --help | help) usage 0 ;;
  *) usage ;;
esac
