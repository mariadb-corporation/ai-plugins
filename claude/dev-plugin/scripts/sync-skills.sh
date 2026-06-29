#!/usr/bin/env bash
#
# sync-skills.sh — vendor MariaDB agent skills into this plugin.
#
# Pulls the agent-skills/ tree from mariadb-corporation/mariadb-docs at a pinned
# ref, reads its .skills-manifest.json, and copies every skill directory into
# claude/dev-plugin/skills/, preserving the upstream layer layout.
# Re-running is idempotent. Provenance is written to skills-source.json.
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

# Resolve plugin root (parent of this scripts/ dir).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILLS_DIR="$PLUGIN_ROOT/skills"
PROVENANCE="$PLUGIN_ROOT/skills-source.json"

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

# Reset skills/ (preserve .gitkeep).
mkdir -p "$SKILLS_DIR"
find "$SKILLS_DIR" -mindepth 1 -maxdepth 1 ! -name '.gitkeep' -exec rm -rf {} +

# Copy each skill dir into skills/, preserving its upstream layer structure
# (e.g. skills/granular/statements/mariadb-create-table/).
count=0
while IFS=$'\t' read -r name relpath; do
  if [ ! -f "$SRC_SKILLS/$relpath" ]; then
    echo "warning: missing skill '$name' at $relpath — skipping" >&2
    continue
  fi
  skill_reldir="$(dirname "$relpath")"
  dest_dir="$SKILLS_DIR/$skill_reldir"
  mkdir -p "$(dirname "$dest_dir")"
  cp -R "$SRC_SKILLS/$skill_reldir" "$dest_dir"
  count=$((count + 1))
done < <(jq -r '.layers[].skills[] | [.name, .path] | @tsv' "$MANIFEST")

# Include the upstream skills manifest alongside the vendored skills.
cp "$MANIFEST" "$SKILLS_DIR/.skills-manifest.json"

# Preserve topical-layer attribution files (those skills are vendored under MIT).
for f in LICENSE VENDORED.md; do
  if [ -f "$SRC_SKILLS/topical/$f" ]; then
    mkdir -p "$SKILLS_DIR/topical"
    cp "$SRC_SKILLS/topical/$f" "$SKILLS_DIR/topical/$f"
  fi
done

# Resolve the concrete commit SHA for provenance.
COMMIT="$(curl -s "https://api.github.com/repos/$SOURCE_REPO/commits/$REF" \
  | jq -r '.sha // empty')"
COMMIT="${COMMIT:-$REF}"
BASELINE="$(jq -r '.baseline // "unknown"' "$MANIFEST")"

jq -n \
  --arg repo "$SOURCE_REPO" \
  --arg subdir "$SUBDIR" \
  --arg ref "$REF" \
  --arg commit "$COMMIT" \
  --arg baseline "$BASELINE" \
  --arg synced_at "$(date -u +%Y-%m-%d)" \
  --argjson count "$count" \
  '{
     source_repo: $repo,
     subdir: $subdir,
     ref: $ref,
     commit: $commit,
     baseline: $baseline,
     skills_synced: $count,
     synced_at: $synced_at
   }' > "$PROVENANCE"

echo "Synced $count skills into $SKILLS_DIR"
echo "Provenance written to $PROVENANCE"
