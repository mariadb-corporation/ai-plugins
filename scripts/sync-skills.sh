#!/usr/bin/env bash
#
# sync-skills.sh — vendor MariaDB agent skills into every plugin in this repo.
#
# Downloads the agent-skills/ tree from mariadb-corporation/mariadb-docs at a
# pinned ref ONCE, reads its .skills-manifest.json, and copies every skill
# directory into each plugin's skills/ dir. It also vendors this repo's own
# additional-skills/ tree. Re-running is idempotent. Per-plugin provenance is
# written to skills-source.json.
#
# All plugins use a FLAT skill layout: every skill dir is placed directly under
# skills/<skill>/, regardless of how it is grouped upstream. This is what
# OpenCode requires (it discovers skills only one directory deep), and it keeps
# every plugin identical on disk. The vendored .skills-manifest.json is rewritten
# so each skill `path` points at its flat location, keeping the test suites'
# manifest-driven loaders valid. The manifest's layer grouping is preserved
# (only the paths flatten), so tests that key off a skill's layer still work.
#
# Local additional-skills/ (this repo's own skills, not from upstream) are copied
# flat alongside the upstream skills and recorded in the manifest under an
# "additional" layer so the disk<->manifest consistency tests pass.
#
# Plugins kept in sync (relative to repo root), all flat:
#   - claude/dev-plugin     (Claude Code)   — all skill layers
#   - codex/dev-plugin      (Codex)         — all skill layers
#   - opencode/dev-plugin   (OpenCode)      — all skill layers
#   - pi/dev-plugin         (Pi / pi.dev)   — all skill layers
#   - claude/sql-plugin     (Claude Code)   — statements + functions + topical only
#   - codex/sql-plugin      (Codex)         — statements + functions + topical only
#   - opencode/sql-plugin   (OpenCode)      — statements + functions + topical only
#   - claude/contributor-plugin   (Claude Code)  — mariadb-shell .claude/skills only
#   - codex/contributor-plugin    (Codex)        — mariadb-shell .claude/skills only
#   - opencode/contributor-plugin (OpenCode)     — mariadb-shell .claude/skills only
#
# The contributor-* plugins vendor a DIFFERENT source repo — the skills tracked in
# mariadb-corporation/mariadb-shell under .claude/skills/ (private; needs a token).
# They share none of the mariadb-docs layers or the local additional-skills/.
#
# The dev-* plugins vendor EVERY upstream layer — granular/statements,
# granular/functions, granular/tools (client tools), granular/connectors
# (database connector skills), topical — plus the local additional-skills/.
#
# The sql-* plugins are a SQL-focused variant vendored from an explicit
# include-list: the upstream layers granular/statements, granular/functions and
# topical, plus the local additional-skills/sql subfolder. So the client-tool and
# connector layers, and the additional-skills/rest and
# additional-skills/schema-management subfolders, are dev-only.
# vendor_into() takes an optional list of include keys; upstream layers are picked
# by their manifest layer key, and local additional-skills/ subfolders by an
# "additional-<subfolder>" key (or "additional" for every subfolder). Only the
# selected upstream layers are written into the vendored .skills-manifest.json,
# and only the selected additional-skills/ subfolders are copied. With NO include
# list, every upstream layer plus every additional-skills/ subfolder is vendored
# — the full dev behavior.
#
# Usage:
#   scripts/sync-skills.sh [REF]
#
# REF defaults to the pinned commit below; pass a tag/branch/commit to override.

set -euo pipefail

SOURCE_REPO="mariadb-corporation/mariadb-docs"
SUBDIR="agent-skills"
# Pinned upstream ref (commit on main, captured 2026-07-22; adds the
# granular/connectors layer). Override via $1.
DEFAULT_REF="1513b3b234ae95b5381b10272645198ec8792a8b"
REF="${1:-$DEFAULT_REF}"

# Resolve repo root (parent of this scripts/ dir).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Plugins to keep in sync (relative to repo root). All use a flat layout.
# The "dev" plugins vendor every layer; the "sql" plugins vendor only the layers
# in SQL_INCLUDE_LAYERS below.
TARGET_PLUGINS=(
  "claude/dev-plugin"
  "codex/dev-plugin"
  "opencode/dev-plugin"
  "pi/dev-plugin"
)
SQL_PLUGINS=(
  "claude/sql-plugin"
  "codex/sql-plugin"
  "opencode/sql-plugin"
)
# Include keys the sql plugins vendor: the upstream manifest layers
# granular/statements, granular/functions and topical, plus the local
# additional-skills/sql subfolder ("additional-sql"). The additional-skills/rest
# and additional-skills/schema-management subfolders are omitted from sql (they
# are dev-only), as are the granular/tools + connectors layers. Use
# "additional-<subfolder>" to pick a subfolder, or "additional" for all of them.
SQL_INCLUDE_LAYERS=("granular-statements" "granular-functions" "topical" "additional-sql")

# This repo's own skills, vendored flat into every plugin alongside upstream.
# They are grouped in per-topic subfolders; dev vendors all of them, while the
# sql plugins select a subset (see SQL_INCLUDE_LAYERS). Add a new subfolder here
# to make it selectable via the "additional-<subfolder>" include key.
ADDITIONAL_SKILLS_DIR="$REPO_ROOT/additional-skills"
ADDITIONAL_SUBDIRS=("sql" "rest" "schema-management")

# The "contributor" plugins vendor a DIFFERENT source: the skills tracked in the
# mariadb-shell repository under .claude/skills/ (no manifest — every SKILL.md
# under it is a skill). That repo is currently PRIVATE, so the fetch needs a
# GitHub token ($GH_TOKEN, else `gh auth token`); without one this plugin is
# skipped (the dev/sql sync still succeeds). Override the ref via $CONTRIB_REF.
CONTRIB_REPO="mariadb-corporation/mariadb-shell"
CONTRIB_SUBDIR=".claude/skills"
CONTRIB_REF="${CONTRIB_REF:-main}"
CONTRIB_PLUGINS=(
  "claude/contributor-plugin"
  "codex/contributor-plugin"
  "opencode/contributor-plugin"
)

command -v jq >/dev/null 2>&1 || { echo "error: jq is required" >&2; exit 1; }
command -v curl >/dev/null 2>&1 || { echo "error: curl is required" >&2; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "Fetching $SOURCE_REPO@$REF ..."
curl -fsSL "https://codeload.github.com/$SOURCE_REPO/tar.gz/$REF" \
  | tar -xz -C "$TMP"

# codeload extracts into <repo>-<ref>/ ; locate the agent-skills dir.
SRC_ROOT="$(find "$TMP" -maxdepth 1 -type d -name '*-*' | head -n1)"
SRC_SKILLS="$SRC_ROOT/$SUBDIR"
MANIFEST="$SRC_SKILLS/.skills-manifest.json"
[ -f "$MANIFEST" ] || { echo "error: manifest not found at $MANIFEST" >&2; exit 1; }

# Resolve the concrete commit SHA + baseline once, shared across plugins.
COMMIT="$(curl -s "https://api.github.com/repos/$SOURCE_REPO/commits/$REF" \
  | jq -r '.sha // empty')"
COMMIT="${COMMIT:-$REF}"
BASELINE="$(jq -r '.baseline // "unknown"' "$MANIFEST")"
SYNCED_AT="$(date -u +%Y-%m-%d)"

# Vendor the downloaded skills into a single plugin's skills/ dir (flat layout).
vendor_into() {
  local plugin_dir="$1"; shift
  local skills_dir="$plugin_dir/skills"
  local provenance="$plugin_dir/skills-source.json"

  # Remaining args = INCLUDE keys. Empty = the full dev set: every upstream
  # manifest layer plus every local additional-skills/ subfolder. A non-empty list
  # restricts vendoring to exactly those upstream layer keys, and selects local
  # additional-skills/ subfolders via "additional-<subfolder>" keys (or
  # "additional" for every subfolder).
  local include_json='[]'
  local -a add_subdirs=()
  if [ "$#" -eq 0 ]; then
    add_subdirs=("${ADDITIONAL_SUBDIRS[@]}")
  else
    include_json="$(printf '%s\n' "$@" | jq -R . | jq -s .)"
    if printf '%s\n' "$@" | grep -qx 'additional'; then
      add_subdirs=("${ADDITIONAL_SUBDIRS[@]}")
    else
      local sub
      for sub in "${ADDITIONAL_SUBDIRS[@]}"; do
        if printf '%s\n' "$@" | grep -qx "additional-$sub"; then
          add_subdirs+=("$sub")
        fi
      done
    fi
  fi

  if [ ! -d "$plugin_dir" ]; then
    echo "warning: plugin dir not found, skipping: $plugin_dir" >&2
    return
  fi

  # Reset skills/ (preserve .gitkeep).
  mkdir -p "$skills_dir"
  find "$skills_dir" -mindepth 1 -maxdepth 1 ! -name '.gitkeep' -exec rm -rf {} +

  # Copy each upstream skill dir flat: skills/<skill>/ regardless of its
  # upstream grouping (OpenCode discovers skills only one level deep, and a flat
  # layout keeps every plugin identical on disk).
  local count=0 name relpath skill_reldir
  while IFS=$'\t' read -r name relpath; do
    if [ ! -f "$SRC_SKILLS/$relpath" ]; then
      echo "warning: missing skill '$name' at $relpath — skipping" >&2
      continue
    fi
    skill_reldir="$(dirname "$relpath")"
    cp -R "$SRC_SKILLS/$skill_reldir" "$skills_dir/$(basename "$skill_reldir")"
    count=$((count + 1))
  done < <(jq -r --argjson include "$include_json" '
      .layers | to_entries[]
      | select(($include | length) == 0 or (.key as $k | $include | index($k)))
      | .value.skills[] | [.name, .path] | @tsv
    ' "$MANIFEST")

  # Copy this repo's local additional-skills/ (flat) from the selected subfolders
  # and collect their manifest entries so the disk<->manifest consistency tests
  # still pass. dev vendors every subfolder; the sql plugins omit "rest".
  local extra_entries="[]" skill_md sdir sname sub base
  if [ "${#add_subdirs[@]}" -gt 0 ]; then
    for sub in "${add_subdirs[@]}"; do
      base="$ADDITIONAL_SKILLS_DIR/$sub"
      [ -d "$base" ] || continue
      while IFS= read -r skill_md; do
        sdir="$(dirname "$skill_md")"
        sname="$(basename "$sdir")"
        cp -R "$sdir" "$skills_dir/$sname"
        count=$((count + 1))
        extra_entries="$(jq \
          --arg n "$sname" \
          --arg p "$sname/SKILL.md" \
          --arg baseline "$BASELINE" \
          '. + [{name: $n, path: $p, status: "local", baseline_version: $baseline}]' \
          <<<"$extra_entries")"
      done < <(find "$base" -mindepth 2 -maxdepth 2 -name SKILL.md | sort)
    done
  fi

  # Write the vendored manifest: flatten every upstream skill `path` to its
  # flattened location (last two segments, e.g.
  # granular/statements/mariadb-x/SKILL.md -> mariadb-x/SKILL.md), and append an
  # "additional" layer for the local skills, so all manifest-driven loaders
  # resolve against the on-disk flat layout.
  jq --argjson extra "$extra_entries" --argjson include "$include_json" '
        .layers |= map_values(
          .skills |= map(.path = (.path | split("/") | .[-2:] | join("/")))
        )
        | if ($include | length) > 0
          then .layers |= with_entries(select(.key as $k | $include | index($k)))
          else . end
        | if ($extra | length) > 0
          then .layers["additional"] = {tier: 3, path: ".", author: "local", skills: $extra}
          else . end
      ' "$MANIFEST" > "$skills_dir/.skills-manifest.json"

  jq -n \
    --arg repo "$SOURCE_REPO" \
    --arg subdir "$SUBDIR" \
    --arg ref "$REF" \
    --arg commit "$COMMIT" \
    --arg baseline "$BASELINE" \
    --arg synced_at "$SYNCED_AT" \
    --argjson count "$count" \
    '{
       source_repo: $repo,
       subdir: $subdir,
       ref: $ref,
       commit: $commit,
       baseline: $baseline,
       skills_synced: $count,
       synced_at: $synced_at
     }' > "$provenance"

  echo "  $plugin_dir: synced $count skills"
}

# Vendor manifest-less contributor skills (every SKILL.md under $src) flat into a
# contributor plugin, writing a synthesized manifest + provenance.
vendor_contributor_into() {
  local plugin_dir="$1" src="$2" commit="$3"
  local skills_dir="$plugin_dir/skills"
  local provenance="$plugin_dir/skills-source.json"

  if [ ! -d "$plugin_dir" ]; then
    echo "warning: plugin dir not found, skipping: $plugin_dir" >&2
    return
  fi

  mkdir -p "$skills_dir"
  find "$skills_dir" -mindepth 1 -maxdepth 1 ! -name '.gitkeep' -exec rm -rf {} +

  local count=0 entries="[]" skill_md sdir sname
  while IFS= read -r skill_md; do
    sdir="$(dirname "$skill_md")"
    sname="$(basename "$sdir")"
    cp -R "$sdir" "$skills_dir/$sname"
    count=$((count + 1))
    entries="$(jq --arg n "$sname" --arg p "$sname/SKILL.md" \
      '. + [{name: $n, path: $p, status: "contributor"}]' <<<"$entries")"
  done < <(find "$src" -mindepth 2 -maxdepth 2 -name SKILL.md | sort)

  jq -n --argjson skills "$entries" \
    '{baseline: "n/a", layers: {contributor: {tier: 0, path: ".", author: "mariadb-shell", skills: $skills}}}' \
    > "$skills_dir/.skills-manifest.json"

  jq -n \
    --arg repo "$CONTRIB_REPO" --arg subdir "$CONTRIB_SUBDIR" \
    --arg ref "$CONTRIB_REF" --arg commit "$commit" \
    --arg synced_at "$SYNCED_AT" --argjson count "$count" \
    '{source_repo: $repo, subdir: $subdir, ref: $ref, commit: $commit,
      skills_synced: $count, synced_at: $synced_at}' > "$provenance"

  echo "  $plugin_dir: synced $count skills"
}

for plugin in "${TARGET_PLUGINS[@]}"; do
  vendor_into "$REPO_ROOT/$plugin"
done

for plugin in "${SQL_PLUGINS[@]}"; do
  vendor_into "$REPO_ROOT/$plugin" "${SQL_INCLUDE_LAYERS[@]}"
done

# Contributor plugins: skills from the (private) mariadb-shell repo. Best-effort —
# needs a GitHub token; on any failure we warn and leave these plugins untouched.
CONTRIB_SYNCED=0
CONTRIB_TOKEN="${GH_TOKEN:-}"
if [ -z "$CONTRIB_TOKEN" ] && command -v gh >/dev/null 2>&1; then
  CONTRIB_TOKEN="$(gh auth token 2>/dev/null || true)"
fi
if [ -z "$CONTRIB_TOKEN" ]; then
  echo "warning: no GH_TOKEN / gh auth token — skipping contributor plugins (private $CONTRIB_REPO)" >&2
else
  echo "Fetching $CONTRIB_REPO@$CONTRIB_REF ($CONTRIB_SUBDIR) ..."
  CONTRIB_TMP="$TMP/contrib"
  mkdir -p "$CONTRIB_TMP"
  if curl -fsSL -H "Authorization: Bearer $CONTRIB_TOKEN" \
       -H "Accept: application/vnd.github+json" \
       "https://api.github.com/repos/$CONTRIB_REPO/tarball/$CONTRIB_REF" \
       | tar -xz -C "$CONTRIB_TMP" 2>/dev/null; then
    CONTRIB_SRC_ROOT="$(find "$CONTRIB_TMP" -maxdepth 1 -type d -name '*-*' | head -n1)"
    CONTRIB_SKILLS="$CONTRIB_SRC_ROOT/$CONTRIB_SUBDIR"
    CONTRIB_COMMIT="$(curl -s -H "Authorization: Bearer $CONTRIB_TOKEN" \
      "https://api.github.com/repos/$CONTRIB_REPO/commits/$CONTRIB_REF" \
      | jq -r '.sha // empty')"
    CONTRIB_COMMIT="${CONTRIB_COMMIT:-$CONTRIB_REF}"
    if [ -d "$CONTRIB_SKILLS" ]; then
      for plugin in "${CONTRIB_PLUGINS[@]}"; do
        vendor_contributor_into "$REPO_ROOT/$plugin" "$CONTRIB_SKILLS" "$CONTRIB_COMMIT"
      done
      CONTRIB_SYNCED=${#CONTRIB_PLUGINS[@]}
    else
      echo "warning: $CONTRIB_SUBDIR not found in $CONTRIB_REPO@$CONTRIB_REF — skipping contributor plugins" >&2
    fi
  else
    echo "warning: failed to fetch $CONTRIB_REPO@$CONTRIB_REF (auth/access?) — skipping contributor plugins" >&2
  fi
fi

total_plugins=$(( ${#TARGET_PLUGINS[@]} + ${#SQL_PLUGINS[@]} ))
echo "Done. Synced $total_plugins plugin(s) from $SOURCE_REPO@$REF" \
     "and $CONTRIB_SYNCED contributor plugin(s) from $CONTRIB_REPO@$CONTRIB_REF."
