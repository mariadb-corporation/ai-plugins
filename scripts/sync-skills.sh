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
#   - claude/dev-plugin     (Claude Code)
#   - codex/dev-plugin      (Codex)
#   - opencode/dev-plugin   (OpenCode)
#
# Usage:
#   scripts/sync-skills.sh [REF]
#
# REF defaults to the pinned commit below; pass a tag/branch/commit to override.

set -euo pipefail

SOURCE_REPO="mariadb-corporation/mariadb-docs"
SUBDIR="agent-skills"
# Pinned upstream ref (commit on main, captured 2026-06-29). Override via $1.
DEFAULT_REF="c3c7e5c659f47e63cdea35bfe86dadaa911c78da"
REF="${1:-$DEFAULT_REF}"

# Resolve repo root (parent of this scripts/ dir).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Plugins to keep in sync (relative to repo root). All use a flat layout.
TARGET_PLUGINS=(
  "claude/dev-plugin"
  "codex/dev-plugin"
  "opencode/dev-plugin"
)

# This repo's own skills, vendored flat into every plugin alongside upstream.
ADDITIONAL_SKILLS_DIR="$REPO_ROOT/additional-skills"

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
  local plugin_dir="$1"
  local skills_dir="$plugin_dir/skills"
  local provenance="$plugin_dir/skills-source.json"

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
  done < <(jq -r '.layers[].skills[] | [.name, .path] | @tsv' "$MANIFEST")

  # Copy this repo's local additional-skills/ (flat) and collect their manifest
  # entries so the disk<->manifest consistency tests still pass.
  local extra_entries="[]" skill_md sdir sname
  if [ -d "$ADDITIONAL_SKILLS_DIR" ]; then
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
    done < <(find "$ADDITIONAL_SKILLS_DIR" -mindepth 2 -maxdepth 2 -name SKILL.md | sort)
  fi

  # Write the vendored manifest: flatten every upstream skill `path` to its
  # flattened location (last two segments, e.g.
  # granular/statements/mariadb-x/SKILL.md -> mariadb-x/SKILL.md), and append an
  # "additional" layer for the local skills, so all manifest-driven loaders
  # resolve against the on-disk flat layout.
  jq --argjson extra "$extra_entries" '
        .layers |= map_values(
          .skills |= map(.path = (.path | split("/") | .[-2:] | join("/")))
        )
        | if ($extra | length) > 0
          then .layers["additional"] = {tier: 3, path: ".", author: "local", skills: $extra}
          else . end
      ' "$MANIFEST" > "$skills_dir/.skills-manifest.json"

  # Preserve topical-layer attribution files (those skills are vendored under MIT).
  local f
  for f in LICENSE VENDORED.md; do
    if [ -f "$SRC_SKILLS/topical/$f" ]; then
      mkdir -p "$skills_dir/topical"
      cp "$SRC_SKILLS/topical/$f" "$skills_dir/topical/$f"
    fi
  done

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

for plugin in "${TARGET_PLUGINS[@]}"; do
  vendor_into "$REPO_ROOT/$plugin"
done

echo "Done. Synced ${#TARGET_PLUGINS[@]} plugin(s) from $SOURCE_REPO@$REF."
