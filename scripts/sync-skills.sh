#!/usr/bin/env bash
#
# sync-skills.sh — vendor MariaDB agent skills into every plugin in this repo.
#
# Downloads the agent-skills/ tree from mariadb-corporation/mariadb-docs at a
# pinned ref ONCE, reads its .skills-manifest.json, and copies every skill
# directory into each plugin's skills/ dir, preserving the upstream layer layout.
# Re-running is idempotent. Per-plugin provenance is written to skills-source.json.
#
# Plugins kept in sync (relative to repo root):
#   - claude/dev-plugin   (Claude Code)
#   - codex/dev-plugin    (Codex)
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

# Plugins to keep in sync (skills/ dir lives directly under each).
TARGET_PLUGINS=(
  "claude/dev-plugin"
  "codex/dev-plugin"
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

# Vendor the downloaded skills into a single plugin's skills/ dir.
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

  # Copy each skill dir, preserving its upstream layer structure
  # (e.g. skills/granular/statements/mariadb-create-table/).
  local count=0 name relpath skill_reldir dest_dir
  while IFS=$'\t' read -r name relpath; do
    if [ ! -f "$SRC_SKILLS/$relpath" ]; then
      echo "warning: missing skill '$name' at $relpath — skipping" >&2
      continue
    fi
    skill_reldir="$(dirname "$relpath")"
    dest_dir="$skills_dir/$skill_reldir"
    mkdir -p "$(dirname "$dest_dir")"
    cp -R "$SRC_SKILLS/$skill_reldir" "$dest_dir"
    count=$((count + 1))
  done < <(jq -r '.layers[].skills[] | [.name, .path] | @tsv' "$MANIFEST")

  # Include the upstream skills manifest alongside the vendored skills.
  cp "$MANIFEST" "$skills_dir/.skills-manifest.json"

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
