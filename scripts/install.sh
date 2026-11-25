#!/usr/bin/env bash
# Install, upgrade or remove Trazo in a host repository.
#
# Usage (run from the host repository root):
#   install.sh install   <tag> [--adapter claude|agents|codex|both] [--source <path-or-url>] [--sha <commit>]
#   install.sh upgrade   <tag> [--adapter ...] [--source ...] [--sha ...] [--dry-run]
#   install.sh uninstall [--purge [--force]]
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
#                      installed as trazo-<name>.md. settings.json placed only if absent; an upgrade merges
#                      its missing deny rules and hook entries into the host's (.bak first)
#                      and drops ones it added earlier that the release dropped (.trazo/INSTALLED-settings)
#   .codex/agents/     project-scoped Codex role agents; names are prefixed with trazo-
#   .agents/skills/    Codex workflow skills; names are prefixed with trazo-
#   harness (src/harness/)
#                      CI (ci.yml; review.yml, report.yml and drive.yml with the Claude adapter), the PR
#                      template, gitleaks and pre-commit config, scripts/scan*.sh, put_secret.sh,
#                      check_pr_evidence.py, report_verdict.py, .env.example (placeholders) and a
#                      placeholder Dockerfile. A path the host already has is never overwritten;
#                      a file we placed is tracked in the manifest like an adapter file
#   .github/CODEOWNERS written only when absent (owner guessed from origin); an existing one is
#                      never edited, and suggested lines are printed
#   .trazo/INSTALLED   manifest: sha256 and path of each adapter file placed. Upgrade and
#                      uninstall touch only listed files, and skip any whose hash no longer
#                      matches (the host edited it). Entries are validated before use

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
  tag="$(git ls-remote --tags --refs -- "$src" 2>/dev/null |
    sed 's|.*refs/tags/||' | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | sort -t. -k1.2,1n -k2,2n -k3,3n |
    tail -n 1)" || true
  [ -n "$tag" ] || die "no vMAJOR.MINOR.PATCH tag found at $src"
  echo "$tag"
}

# fetch <source> <tag> <dest>: shallow clone of exactly that tag, refusing symlinks in src/.
fetch() {
  local src="$1" tag="$2" dest="$3"
  # Fetch refs/tags/<tag> explicitly: `clone --branch <name>` prefers a branch of that name,
  # so anyone able to push a branch `v0.2.0` could stand in for the release (#272).
  git init --quiet -- "$dest" >/dev/null 2>&1 || die "cannot create a work tree for $src"
  git -C "$dest" -c core.symlinks=false fetch --quiet --depth 1 --no-tags -- "$src" \
    "+refs/tags/$tag:refs/tags/$tag" >/dev/null 2>&1 ||
    die "cannot fetch tag '$tag' from $src (does the tag exist?)"
  git -C "$dest" -c core.symlinks=false checkout --quiet --detach "refs/tags/$tag" >/dev/null 2>&1 ||
    die "cannot check out tag '$tag' from $src"
  [ -d "$dest/src/overlay" ] && [ -d "$dest/src/adapters" ] ||
    die "tag '$tag' has no src/overlay and src/adapters; it predates the installer layout"
  # With core.symlinks=false a link is checked out as a plain file, so read the tree itself.
  if git -C "$dest" ls-tree -r HEAD -- src | awk '$1 == "120000" { found = 1 } END { exit !found }'; then
    die "tag '$tag' contains symlinks under src/; refusing"
  fi
  if [ -n "$(find "$dest/src" -type l)" ]; then
    die "tag '$tag' contains symlinks under src/; refusing"
  fi
}

# ---------------------------------------------------------------- hashing

hash_of() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | cut -d' ' -f1
  else
    shasum -a 256 "$1" | cut -d' ' -f1
  fi
}

# ---------------------------------------------------------------- marked blocks

# Marker lines are matched with a trailing CR ignored, so a CRLF file still has its block.
count_marker() { tr -d '\r' <"$1" | grep -cxF "$2" || true; }

# check_markers <file>: refuse unless the markers are absent or exactly one balanced pair.
check_markers() {
  local file="$1" begins ends bl el
  [ -e "$file" ] || return 0
  begins="$(count_marker "$file" "$BEGIN")"
  ends="$(count_marker "$file" "$END")"
  if [ "$begins" = 0 ] && [ "$ends" = 0 ]; then
    return 0
  fi
  if [ "$begins" = 1 ] && [ "$ends" = 1 ]; then
    bl="$(tr -d '\r' <"$file" | grep -nxF "$BEGIN" | cut -d: -f1)"
    el="$(tr -d '\r' <"$file" | grep -nxF "$END" | cut -d: -f1)"
    [ "$bl" -lt "$el" ] && return 0
    die "$file has its trazo markers in the wrong order (end before begin); fix it by hand and retry"
  fi
  die "$file has unbalanced trazo markers ($begins begin, $ends end); fix it by hand and retry"
}

# set_block <file> <body-file>: insert or replace the marked block; create the file if absent.
set_block() {
  local file="$1" body="$2" tmp
  if [ ! -e "$file" ]; then
    { echo "$BEGIN"; cat "$body"; echo "$END"; } >"$file"
    return
  fi
  check_markers "$file"
  if [ "$(count_marker "$file" "$BEGIN")" = 0 ]; then
    # Append after a blank line; the host's own bytes stay exactly where they were.
    [ -z "$(tail -c1 "$file")" ] || echo >>"$file"
    { echo; echo "$BEGIN"; cat "$body"; echo "$END"; } >>"$file"
  else
    tmp="$(mktemp)"
    awk -v b="$BEGIN" -v e="$END" -v blk="$body" '
      { l = $0; sub(/\r$/, "", l) }
      l == b { print; while ((getline x < blk) > 0) print x; skip = 1; next }
      skip && l == e { skip = 0; print; next }
      !skip { print }' "$file" >"$tmp"
    cat "$tmp" >"$file"
    rm -f "$tmp"
  fi
}

# drop_block <file>: remove the marked block (and the one blank line set_block added before
# it). A file left empty is one this script created, so it is removed.
drop_block() {
  local file="$1" tmp
  [ -e "$file" ] || return 0
  check_markers "$file"
  [ "$(count_marker "$file" "$BEGIN")" = 1 ] || return 0
  tmp="$(mktemp)"
  awk -v b="$BEGIN" -v e="$END" '
    { l = $0; sub(/\r$/, "", l) }
    skip { if (l == e) skip = 0; next }
    l == b { held = 0; skip = 1; next }
    held { print held_line; held = 0 }
    l == "" { held = 1; held_line = $0; next }
    { print }
    END { if (held) print held_line }' "$file" >"$tmp"
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
HARNESS_RE='\.github/workflows/(ci|review|report|drive|owner-merge|status)\.yml|\.github/pull_request_template\.md|\.gitleaks\.toml|\.pre-commit-config\.yaml|\.env\.example|Dockerfile|scripts/(scan\.sh|scan-preflight\.sh|put_secret\.sh|check_pr_evidence\.py|report_verdict\.py|drive_guard\.py|drive_sweep\.py|gen_status\.py)'
PATH_RE='^(\.claude/(agents|commands)/[A-Za-z0-9._-]+\.md|\.claude/settings\.json|'"$HARNESS_RE"'|\.codex/agents/[A-Za-z0-9._-]+\.toml|\.agents/skills/[A-Za-z0-9._-]+/SKILL\.md)$'

# check_manifest: the manifest is a committed file anyone can edit, and it decides what we
# overwrite and delete. Accept only "<sha256>  <path>" with a path from the allowed set.
check_manifest() {
  local line h f
  [ ! -L "$MANIFEST" ] || die "$MANIFEST must not be a symlink; refusing"
  [ ! -L "$SETTINGS_REC" ] || die "$SETTINGS_REC must not be a symlink; refusing"
  [ -f "$MANIFEST" ] || return 0
  while IFS= read -r line || [ -n "$line" ]; do
    h="${line%%  *}"
    f="${line#*  }"
    [[ "$h" =~ ^[0-9a-f]{64}$ ]] && [[ "$f" =~ $PATH_RE ]] &&
      ! [[ "$f" =~ (^|/)\.\.(/|$) ]] && [ "$line" = "$h  $f" ] ||
      die "$MANIFEST has an invalid adapter entry ($line); refusing"
  done <"$MANIFEST"
}

recorded_hash() { [ -f "$MANIFEST" ] && awk -v p="$1" '{ h = $1; $1 = ""; sub(/^ +/, ""); if ($0 == p) print h }' "$MANIFEST" || true; }
in_manifest() { [ -n "$(recorded_hash "$1")" ]; }
# edited <path>: true when the file is ours but its content no longer matches what we placed.
edited() { [ -e "$1" ] && [ "$(hash_of "$1")" != "$(recorded_hash "$1")" ]; }

# put_file <rendered> <dest> <placed-list>: write our file, unless the host edited the copy we
# placed earlier; then show the diff, warn, and leave it (the old hash stays recorded).
put_file() {
  local rendered="$1" dest="$2" placed="$3"
  if in_manifest "$dest" && edited "$dest"; then
    echo "warning: $dest was edited since Trazo placed it; not overwriting. Diff (yours -> incoming):" >&2
    diff -u "$dest" "$rendered" >&2 || true
    echo "$(recorded_hash "$dest")  $dest" >>"$placed"
    return
  fi
  mkdir -p "$(dirname "$dest")"
  cp "$rendered" "$dest"
  echo "$(hash_of "$dest")  $dest" >>"$placed"
}

# place_adapter_file <src> <dir> <name> <placed-list>: write <dir>/<name>, or trazo-<name> on a
# clash with a file this script did not place.
place_adapter_file() {
  local src="$1" dir="$2" name="$3" placed="$4" dest rendered
  dest="$dir/$name"
  if [ -e "$dest" ] && ! in_manifest "$dest"; then
    dest="$dir/trazo-$name"
    echo "clash: $dir/$name is yours; installed as $dest" >&2
    if [ -e "$dest" ] && ! in_manifest "$dest"; then
      echo "warning: $dest is also yours; skipping $name entirely" >&2
      return
    fi
  elif [ ! -e "$dest" ] && in_manifest "$dir/trazo-$name"; then
    dest="$dir/trazo-$name"
  fi
  rendered="$(mktemp)"
  case "$dest" in
    */trazo-*)
      # A prefixed agent must also be renamed inside, or it collides on `name:`.
      if [ "$(basename "$dir")" = agents ]; then
        awk '!d && /^name: / { sub(/^name: /, "name: trazo-"); d = 1 } { print }' "$src" >"$rendered"
      else
        cp "$src" "$rendered"
      fi ;;
    *) cp "$src" "$rendered" ;;
  esac
  put_file "$rendered" "$dest" "$placed"
  rm -f "$rendered"
}

# place_codex_agent <src> <name> <placed-list>: project agent filenames and TOML names must agree.
place_codex_agent() {
  local src="$1" name="$2" placed="$3" dest rendered installed_name
  installed_name="trazo-$name"
  dest=".codex/agents/$installed_name.toml"
  if [ -e "$dest" ] && ! in_manifest "$dest"; then
    echo "clash: $dest is yours; installing as trazo-trazo-$name.toml" >&2
    installed_name="trazo-trazo-$name"
    dest=".codex/agents/$installed_name.toml"
    if [ -e "$dest" ] && ! in_manifest "$dest"; then
      echo "warning: $dest is also yours; skipping $name entirely" >&2
      return
    fi
  fi
  rendered="$(mktemp)"
  if [ "$installed_name" = "trazo-$name" ]; then
    cp "$src" "$rendered"
  else
    sed "s/^name = \"trazo-$name\"$/name = \"$installed_name\"/" "$src" >"$rendered"
  fi
  put_file "$rendered" "$dest" "$placed"
  rm -f "$rendered"
}

# place_codex_skill <src> <name> <placed-list>: keep the required SKILL.md name and avoid
# overwriting a host skill directory. The skill's frontmatter name follows the chosen directory.
place_codex_skill() {
  local src="$1" name="$2" placed="$3" installed_name dest rendered
  installed_name="trazo-$name"
  dest=".agents/skills/$installed_name/SKILL.md"
  if [ -e "$dest" ] && ! in_manifest "$dest"; then
    echo "clash: $dest is yours; installing as trazo-trazo-$name/SKILL.md" >&2
    installed_name="trazo-trazo-$name"
    dest=".agents/skills/$installed_name/SKILL.md"
    if [ -e "$dest" ] && ! in_manifest "$dest"; then
      echo "warning: $dest is also yours; skipping $name entirely" >&2
      return
    fi
  fi
  rendered="$(mktemp)"
  if [ "$installed_name" = "trazo-$name" ]; then
    cp "$src" "$rendered"
  else
    sed "s/^name: trazo-$name$/name: $installed_name/" "$src" >"$rendered"
  fi
  put_file "$rendered" "$dest" "$placed"
  rm -f "$rendered"
}

# place_harness <src> <dest> <placed-list>: the host's own path is never overwritten. A path that
# is absent, or that we placed and the host has not edited, is written; one we placed and the host
# edited is left with a diff (put_file). A path the host created is skipped and not recorded.
place_harness() {
  local src="$1" dest="$2" placed="$3"
  if [ -e "$dest" ] && ! in_manifest "$dest"; then
    echo "kept: $dest is yours; not overwritten" >&2
    return
  fi
  put_file "$src" "$dest" "$placed"
}

# remote_slug: owner/repo from the origin remote when it is on github.com, else empty.
remote_slug() {
  local url
  url="$(git remote get-url origin 2>/dev/null)" || return 0
  url="${url%.git}"
  case "$url" in
    *github.com[:/]*/*) echo "${url#*github.com[:/]}" ;;
  esac
}

# place_harness_all <repo> <adapter> <placed-list>
place_harness_all() {
  local repo="$1" adapter="$2" placed="$3" h="$1/src/harness" slug owner f
  [ -d "$h" ] || { echo "note: this tag ships no src/harness; no CI or scripts placed" >&2; return 0; }
  for f in .github/workflows/ci.yml .github/pull_request_template.md .gitleaks.toml \
    .pre-commit-config.yaml Dockerfile scripts/scan.sh scripts/scan-preflight.sh \
    scripts/put_secret.sh scripts/check_pr_evidence.py scripts/report_verdict.py scripts/drive_guard.py scripts/drive_sweep.py scripts/gen_status.py; do
    place_harness "$h/$f" "$f" "$placed"
  done
  # Stored as env.example in src/ so no tool mistakes the source for a real .env file.
  place_harness "$h/env.example" .env.example "$placed"
  if [ "$adapter" = claude ] || [ "$adapter" = both ]; then
    for f in .github/workflows/review.yml .github/workflows/report.yml .github/workflows/drive.yml .github/workflows/owner-merge.yml .github/workflows/status.yml; do
      place_harness "$h/$f" "$f" "$placed"
    done
  fi
  if [ ! -e .github/CODEOWNERS ]; then
    slug="$(remote_slug)"
    owner="${slug%%/*}"
    mkdir -p .github
    if [ -n "$owner" ]; then
      sed "s/@OWNER/@$owner/" "$h/.github/CODEOWNERS" >.github/CODEOWNERS
    else
      cp "$h/.github/CODEOWNERS" .github/CODEOWNERS
    fi
    echo "created .github/CODEOWNERS (starter)"
    CODEOWNERS_NEW=1
  fi
}

# ---------------------------------------------------------------- install / upgrade

# Merge of the shipped settings.json into the host's (#337, #346). Adds missing
# permissions.deny entries and missing hooks.PreToolUse entries (matched by matcher + command);
# a hook is added only if its .trazo/hooks/ script exists in <hooks_dir>. It never reorders or
# edits a host entry and never touches `model`. It removes only what THIS INSTALLER added
# earlier (recorded in $SETTINGS_REC) and the new release no longer ships, and only while the
# replacement guard hook is installed and registered. A historic rule from before the record
# existed is never removed (the installer cannot prove it wrote it): it is kept and reported
# with the exact line to delete.
# Modes: check (validate only), dry (print what would change), apply (back up to .bak, write,
# print what changed, update the record), record (fresh install: record everything shipped).
SETTINGS_REC=.trazo/INSTALLED-settings
merge_settings() {
  local mode="$1" shipped="$2" hooks_dir="$3"
  python3 - "$mode" "$shipped" ".claude/settings.json" "$hooks_dir" "$SETTINGS_REC" <<'PY'
import json, os, re, shutil, sys

mode, shipped_p, host_p, hooks_dir, rec_p = sys.argv[1:6]

# Deny rules shipped in v0.3.0, before the record existed. Of these, the ones the current
# release does not ship were dropped later (the blanket workflow dispatch deny, replaced by the
# engineer Bash guard allowlist; the deploy-command denies). They are kept and reported, never
# removed: a host cannot prove it did not write one itself.
HISTORIC = [
    "Read(./**/.env)", "Read(./**/.env.*)", "Read(./secrets/**)", "Read(./**/*.pem)",
    "Read(./**/*.key)", "Bash(gh pr merge *)", "Bash(fly *)", "Bash(flyctl *)",
    "Bash(clasp push *)", "Bash(clasp deploy *)", "Bash(scripts/deploy*)",
    "Bash(./scripts/deploy*)", "Bash(scripts/put_secret.sh *)", "Bash(gh secret *)",
    "Bash(gh variable set *)", "Bash(gh " + "workflow run *)", "Read(~/.ssh/**)",
    "Read(~/.aws/**)", "Read(~/.config/**)", "Read(~/.claude/**)", "Read(~/.netrc)",
    "Read(~/.docker/**)", "Read(~/.gitconfig)",
]


def refuse(why):
    print("error: .claude/settings.json " + why + "; refusing, nothing changed. Fix it, "
          "or merge src/adapters/claude/settings.json by hand.", file=sys.stderr)
    sys.exit(1)


with open(shipped_p) as f:
    ship = json.load(f)
ship_deny = ship.get("permissions", {}).get("deny", [])
ship_keys = [(e.get("matcher"), h.get("command"))
             for e in ship.get("hooks", {}).get("PreToolUse", []) for h in e.get("hooks", [])]


def save_rec(deny, keys):
    data = {"deny": deny, "hooks": [list(k) for k in keys]}
    with open(rec_p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


if mode == "record":
    save_rec(list(ship_deny), ship_keys)
    sys.exit(0)

try:
    with open(host_p, encoding="utf-8") as f:
        host = json.load(f)
except ValueError:
    refuse("is not valid JSON")
if not isinstance(host, dict):
    refuse("is not a JSON object")
perms = host.get("permissions", {})
deny = perms.get("deny", []) if isinstance(perms, dict) else None
hooks = host.get("hooks", {})
pre = hooks.get("PreToolUse", []) if isinstance(hooks, dict) else None
if not isinstance(deny, list) or not isinstance(pre, list):
    refuse("has a permissions.deny or hooks.PreToolUse that is not a list")
if not all(isinstance(e, dict) and isinstance(e.get("hooks", []), list) for e in pre):
    refuse("has a hooks.PreToolUse entry of an unexpected shape")

rec_deny, rec_keys = [], []
if os.path.isfile(rec_p):
    try:
        with open(rec_p, encoding="utf-8") as f:
            rec = json.load(f)
        rec_deny = [r for r in rec["deny"] if isinstance(r, str)]
        rec_keys = [tuple(k) for k in rec["hooks"] if isinstance(k, list) and len(k) == 2]
    except (ValueError, KeyError, TypeError):
        print("note: " + rec_p + " is unreadable; ignoring it (nothing recorded is removed)",
              file=sys.stderr)

if mode == "check":
    sys.exit(0)

removed, kept, added = [], [], []

# --- removals: recorded as installer-added and no longer shipped
new_pre = []
for e in pre:
    hs = e.get("hooks", [])
    keep = []
    for h in hs:
        key = (e.get("matcher"), h.get("command") if isinstance(h, dict) else None)
        if key in rec_keys and key not in ship_keys:
            removed.append("hooks.PreToolUse [" + str(key[0]) + "]: " + str(key[1])
                           + "  (recorded as installer-added)")
        else:
            keep.append(h)
    if keep or not hs:
        e["hooks"] = keep
        new_pre.append(e)
pre[:] = new_pre

# --- additions
for rule in ship_deny:
    if rule not in deny:
        deny.append(rule)
        added.append("permissions.deny: " + rule)
have = {(e.get("matcher"), h.get("command"))
        for e in pre for h in e.get("hooks", []) if isinstance(h, dict)}
added_keys = []
for e in ship.get("hooks", {}).get("PreToolUse", []):
    for h in e.get("hooks", []):
        key = (e.get("matcher"), h.get("command"))
        m = re.search(r"\.trazo/hooks/([A-Za-z0-9._-]+)", h.get("command", ""))
        if key in have or (m and not os.path.isfile(os.path.join(hooks_dir, m.group(1)))):
            continue
        pre.append({"matcher": e.get("matcher"), "hooks": [h]})
        have.add(key)
        added_keys.append(key)
        added.append("hooks.PreToolUse [" + str(e.get("matcher")) + "]: " + h.get("command", ""))

# --- deny removals (#346): a dropped deny rule goes only when its replacement, the shipped
# engineer Bash guard hook, is installed (script present) and registered in the merged result.
# Otherwise the rule stays and is reported, so a host never ends with neither the deny nor the guard.
guard_keys = [k for k in ship_keys if "engineer_bash_guard.py" in str(k[1])]
guard_ok = bool(guard_keys)
for k in guard_keys:
    m = re.search(r"\.trazo/hooks/([A-Za-z0-9._-]+)", str(k[1]))
    if k not in have or not (m and os.path.isfile(os.path.join(hooks_dir, m.group(1)))):
        guard_ok = False
dropped_hist = [d for d in HISTORIC if d not in ship_deny]
new_deny = []
for rule in deny:
    droppable = rule in rec_deny and rule not in ship_deny
    if droppable and guard_ok:
        removed.append("permissions.deny: " + rule + "  (recorded as installer-added)")
    else:
        new_deny.append(rule)
        if droppable:
            kept.append(json.dumps(rule, ensure_ascii=False) + "  (the replacement guard hook "
                        "is not installed and registered, so the rule stays)")
        elif rule in dropped_hist and rule not in rec_deny:
            kept.append(json.dumps(rule, ensure_ascii=False))
deny[:] = new_deny

# --- the record: what we added, cumulatively, minus what is gone. A dropped rule that remains
# because its replacement guard is unavailable stays recorded for a later safe upgrade.
added_deny = [a.split(": ", 1)[1] for a in added if a.startswith("permissions.deny: ")]
new_rec_deny = [r for r in rec_deny if r in deny]
new_rec_deny += [r for r in added_deny if r not in new_rec_deny]
new_rec_keys = [k for k in rec_keys if k in ship_keys and k in have]
new_rec_keys += [k for k in added_keys if k not in new_rec_keys]

for k in kept:
    print("kept (not recorded as installer-added): " + k + "  <- a Trazo rule an older release "
          "shipped and this one dropped; delete this line from permissions.deny in "
          ".claude/settings.json if you did not write it")
if not (added or removed):
    if mode == "apply" and (new_rec_deny, new_rec_keys) != (rec_deny, rec_keys):
        save_rec(new_rec_deny, new_rec_keys)
    print(".claude/settings.json: already has everything shipped; unchanged")
    sys.exit(0)
if mode == "apply":
    shutil.copyfile(host_p, host_p + ".bak")
    host.setdefault("permissions", {})["deny"] = deny
    host.setdefault("hooks", {})["PreToolUse"] = pre
    with open(host_p, "w", encoding="utf-8") as f:
        json.dump(host, f, indent=2, ensure_ascii=False)
        f.write("\n")
    save_rec(new_rec_deny, new_rec_keys)
print(".claude/settings.json: " + ("would change" if mode == "dry" else "changed")
      + " (yours kept; backup .claude/settings.json.bak):")
for a in added:
    print("  + " + a)
for r in removed:
    print("  - removed " + r)
PY
}

do_install() {
  local mode="$1" tag="$2" source="$3" adapter="$4" dryrun="$5" want_sha="$6"
  local tmp new_managed f name dest placed kind sha line

  case "$adapter" in claude | agents | codex | both) ;; *) die "--adapter must be claude, agents, codex or both" ;; esac
  [ -d .git ] || [ -f .git ] || die "run this from the root of a git repository"
  case "$source" in -*) die "source must not start with '-'" ;; esac
  [ -z "$want_sha" ] || [[ "$want_sha" =~ ^[0-9a-f]{40}$ ]] || die "--sha must be a full 40-hex commit id"
  if [ -d .trazo ] && [ ! -f "$MANIFEST" ]; then
    # Without the manifest this may be an older layout whose adr/charter live in .trazo/
    # itself, which a managed replace would delete.
    for f in .trazo/* .trazo/.[!.]*; do
      [ -e "$f" ] || continue
      [ "$f" = "$P" ] && continue
      die ".trazo/ exists without $MANIFEST (older layout?); refusing to replace it. Move your own files into $P first"
    done
  fi
  check_manifest
  check_markers AGENTS.md
  check_markers CLAUDE.md
  if [ "$mode" = upgrade ]; then
    [ -f .trazo/VERSION ] || die "no .trazo/VERSION here; nothing to upgrade (use install)"
  elif [ -f .trazo/VERSION ]; then
    echo "note: .trazo/VERSION is $(head -n 1 .trazo/VERSION); reinstalling at $tag"
  fi

  [ "$tag" != latest ] || tag="$(resolve_latest "$source")"
  [[ "$tag" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "tag must look like v1.2.3 (or 'latest'), got '$tag'"

  work="$(mktemp -d)"
  trap 'rm -rf "${work:-}"' EXIT
  fetch "$source" "$tag" "$work/repo"
  sha="$(git -C "$work/repo" rev-parse HEAD)"
  echo "source: $source"
  echo "tag:    $tag"
  echo "commit: $sha"
  if [ -n "$want_sha" ] && [ "$want_sha" != "$sha" ]; then
    die "tag '$tag' resolves to $sha, not the pinned $want_sha; refusing"
  fi

  # Stage the managed copy of .trazo/ so upgrade can diff before it changes anything.
  new_managed="$work/new"
  mkdir -p "$new_managed"
  cp -R "$work/repo/src/overlay/." "$new_managed/"
  printf '%s\ncommit %s\n' "$tag" "$sha" >"$new_managed/VERSION"

  if [ "$mode" = upgrade ]; then
    echo "== diff of .trazo/ (installed -> $tag), $P excluded"
    tmp="$work/old"
    mkdir -p "$tmp"
    for f in .trazo/*; do
      case "$f" in "$P" | "$MANIFEST" | "$SETTINGS_REC") continue ;; esac
      [ -e "$f" ] && cp -R "$f" "$tmp/"
    done
    diff -ru "$tmp" "$new_managed" || true
    echo "== end diff"
    if [ "$adapter" = claude ] || [ "$adapter" = both ]; then
      if [ -f .claude/settings.json ] && { ! in_manifest .claude/settings.json || edited .claude/settings.json; }; then
        merge_settings check "$work/repo/src/adapters/claude/settings.json" "$new_managed/hooks" ||
          die "settings.json merge refused (see above)"
        [ "$dryrun" != 1 ] ||
          merge_settings dry "$work/repo/src/adapters/claude/settings.json" "$new_managed/hooks"
      fi
    fi
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
    case "$f" in "$P" | "$MANIFEST" | "$SETTINGS_REC") continue ;; esac
    rm -rf "$f"
  done
  cp -R "$new_managed/." .trazo/

  # The host's own state: templates only if absent.
  if [ -d "$P" ]; then
    echo "$P/ exists; left untouched except for missing templates"
    contract="$P/ARCHITECTURE_CONTRACT.md"
    contract_template="$work/repo/src/overlay/templates/docs/ARCHITECTURE_CONTRACT.md"
    if [ -f "$contract_template" ] && [ ! -e "$contract" ] && [ ! -L "$contract" ]; then
      cp "$contract_template" "$contract"
      echo "created $contract from current template"
    fi
  else
    mkdir -p "$P/charter" "$P/adr" "$P/workstreams"
    cp "$work/repo/src/overlay/templates/charter.md" "$P/charter/charter.md"
    cp -R "$work/repo/src/overlay/templates/docs/." "$P/"
    touch "$P/adr/.gitkeep" "$P/workstreams/.gitkeep"
    echo "created $P/ from blank templates"
  fi

  # Adapters. Rebuild the manifest from what is placed now.
  placed="$work/placed"
  : >"$placed"
  if [ "$adapter" = agents ] || [ "$adapter" = codex ] || [ "$adapter" = both ]; then
    set_block AGENTS.md "$work/repo/src/adapters/AGENTS.md"
    echo "AGENTS.md: trazo block set"
  fi
  if [ "$adapter" = codex ]; then
    for f in "$work/repo/src/adapters/codex/agents"/*.toml; do
      [ -f "$f" ] || continue
      place_codex_agent "$f" "$(basename "$f" .toml)" "$placed"
    done
    for f in "$work/repo/src/adapters/codex/skills"/*/SKILL.md; do
      [ -f "$f" ] || continue
      place_codex_skill "$f" "$(basename "$(dirname "$f")")" "$placed"
    done
  fi
  if [ "$adapter" = claude ] || [ "$adapter" = both ]; then
    set_block CLAUDE.md "$work/repo/src/adapters/CLAUDE.md"
    echo "CLAUDE.md: trazo block set"
    for kind in agents commands; do
      for f in "$work/repo/src/adapters/claude/$kind"/*.md; do
        place_adapter_file "$f" ".claude/$kind" "$(basename "$f")" "$placed"
      done
    done
    if [ -e .claude/settings.json ] && { ! in_manifest .claude/settings.json || { [ "$mode" = upgrade ] && edited .claude/settings.json; }; }; then
      if [ "$mode" = upgrade ]; then
        merge_settings apply "$work/repo/src/adapters/claude/settings.json" .trazo/hooks
      else
        echo "note: .claude/settings.json is yours; not touched. Trazo's deny rules for secrets are in" \
          "src/adapters/claude/settings.json at $tag; an upgrade merges them in."
      fi
    else
      put_file "$work/repo/src/adapters/claude/settings.json" .claude/settings.json "$placed"
      # The file is now exactly what we ship: record it, so a later release can drop rules.
      if cmp -s "$work/repo/src/adapters/claude/settings.json" .claude/settings.json; then
        merge_settings record "$work/repo/src/adapters/claude/settings.json" .trazo/hooks
      fi
      echo "== .claude/settings.json, as shipped (review it)"
      cat "$work/repo/src/adapters/claude/settings.json"
      echo "== end settings.json"
    fi
  fi
  CODEOWNERS_NEW=0
  place_harness_all "$work/repo" "$adapter" "$placed"
  # Keep manifest entries from an earlier adapter choice that are still on disk.
  if [ -f "$MANIFEST" ]; then
    while IFS= read -r line; do
      f="${line#*  }"
      if [ -e "$f" ] && ! awk -v p="$f" '{ sub(/^[^ ]+  /, ""); if ($0 == p) f = 1 } END { exit !f }' "$placed"; then
        echo "$line" >>"$placed"
      fi
    done <"$MANIFEST"
  fi
  sort -u "$placed" >"$MANIFEST"

  echo "installed Trazo $tag"
  print_owner_steps "$tag" "$adapter"
}

# print_owner_steps <tag> <adapter>: only what a script cannot do for the owner.
print_owner_steps() {
  local tag="$1" adapter="$2" slug n=1
  slug="$(remote_slug)"
  [ -n "$slug" ] || slug="<owner>/<repo>"
  echo
  echo "Owner-only steps (secrets, variables and settings are yours; this script never sets them):"
  echo
  if [ "$adapter" = claude ] || [ "$adapter" = both ]; then
    echo "  $n. ANTHROPIC_API_KEY secret, for automatic review and drive. One per repo, unless the"
    echo "     repo is in a GitHub organization (then set it once as an organization secret):"
    echo "       gh secret set ANTHROPIC_API_KEY -R $slug"
    n=$((n + 1))
    echo "  $n. AUTO_REVIEW_ENABLED variable. Automatic review runs only when it is true; the default"
    echo "     is off. Turn it on after the secret is set:"
    echo "       gh variable set AUTO_REVIEW_ENABLED --body true -R $slug"
    n=$((n + 1))
    echo "  $n. report.yml (sets trazo/verdict) and drive.yml's publish job declare the environment trazo-apps."
    echo "     Create it with deployment branches limited to your default branch only, and create the"
    echo "     builder and reviewer GitHub Apps with scripts/setup_github_apps.zsh from Trazo at $tag"
    echo "     (it is not installed in your repo; it also creates the environment and stores the keys there)."
    n=$((n + 1))
    echo "  $n. DRIVE_ENABLED stays unset (drive does nothing) until you can watch one run. Then set it"
    echo "     to true, watch that one watched run, and unset it again if anything looks wrong."
    n=$((n + 1))
  fi
  if [ "${CODEOWNERS_NEW:-0}" = 1 ]; then
    echo "  $n. Check .github/CODEOWNERS: the handle is guessed from origin (or is still @OWNER) and"
    echo "     must name a user or team that can review."
  else
    echo "  $n. Your .github/CODEOWNERS was not edited. Add these lines (replace @owner):"
    echo "       /.trazo/project/charter/   @owner"
    echo "       /.claude/settings.json     @owner"
    echo "       /.trazo/INSTALLED-settings @owner"
    echo "       /.github/workflows/        @owner"
    echo "       /.github/CODEOWNERS        @owner"
  fi
  n=$((n + 1))
  echo "  $n. Settings > General > Pull Requests > Automatically delete head branches. Verify:"
  echo "       gh api repos/$slug --jq .delete_branch_on_merge     (should print true)"
}

# ---------------------------------------------------------------- uninstall

do_uninstall() {
  local purge="$1" force="$2" line f st
  [ -d .trazo ] || die "no .trazo/ here; nothing to uninstall"
  check_manifest
  check_markers AGENTS.md
  check_markers CLAUDE.md
  if [ "$purge" = 1 ] && [ "$force" != 1 ] && [ -d "$P" ]; then
    # Fail closed: an unknowable state counts as "might lose work". --ignored so
    # gitignored files (a host's *.local) count too; git cannot recover those.
    st="$(git status --porcelain --ignored -- "$P" 2>/dev/null)" ||
      die "cannot read git status for $P; pass --force to delete it anyway"
    [ -z "$st" ] || die "$P has untracked, modified or gitignored files; commit or move them, or pass --force to delete them anyway"
  fi
  if [ -f "$MANIFEST" ]; then
    while IFS= read -r line; do
      f="${line#*  }"
      [ -e "$f" ] || continue
      if edited "$f"; then
        echo "warning: $f was edited since Trazo placed it; kept" >&2
      else
        rm -f "$f"
        echo "removed $f"
      fi
    done <"$MANIFEST"
  fi
  rmdir .claude/agents .claude/commands .claude 2>/dev/null || true
  rmdir .codex/agents .codex .agents/skills .agents 2>/dev/null || true
  drop_block AGENTS.md
  drop_block CLAUDE.md
  for f in .trazo/* .trazo/.[!.]*; do
    [ -e "$f" ] || continue
    [ "$f" = "$P" ] && continue
    rm -rf "$f"
  done
  if [ "$purge" = 1 ]; then
    rm -rf .trazo
    echo "removed .trazo/ including project/ (--purge)"
  elif [ -d "$P" ]; then
    echo "kept $P/ (yours); --purge removes it"
  else
    rmdir .trazo 2>/dev/null || true
  fi
  echo "uninstalled Trazo. .github/CODEOWNERS was not touched; remove the lines you added."
}

# ---------------------------------------------------------------- main

[ $# -ge 1 ] || usage
cmd="$1"
shift
tag="" adapter=both dryrun=0 purge=0 force=0 want_sha="" source="" from_env=0
if [ -n "${TRAZO_SOURCE:-}" ]; then source="$TRAZO_SOURCE"; from_env=1; else source="$DEFAULT_SOURCE"; fi
while [ $# -gt 0 ]; do
  case "$1" in
    --adapter) [ $# -ge 2 ] || die "--adapter needs a value"; adapter="$2"; shift 2 ;;
    --source) [ $# -ge 2 ] || die "--source needs a value"; source="$2"; from_env=0; shift 2 ;;
    --sha) [ $# -ge 2 ] || die "--sha needs a value"; want_sha="$2"; shift 2 ;;
    --dry-run) dryrun=1; shift ;;
    --purge) purge=1; shift ;;
    --force) force=1; shift ;;
    -h | --help) usage 0 ;;
    -*) die "unknown option $1" ;;
    *) [ -z "$tag" ] || die "unexpected argument $1"; tag="$1"; shift ;;
  esac
done
[ "$from_env" = 0 ] || echo "note: TRAZO_SOURCE overrides the default source: $source" >&2

case "$cmd" in
  install | upgrade)
    [ -n "$tag" ] || die "$cmd needs an exact release tag, e.g. $0 $cmd v0.1.0"
    do_install "$cmd" "$tag" "$source" "$adapter" "$dryrun" "$want_sha"
    ;;
  uninstall)
    [ -z "$tag" ] || die "uninstall takes no tag"
    do_uninstall "$purge" "$force"
    ;;
  -h | --help | help) usage 0 ;;
  *) usage ;;
esac
