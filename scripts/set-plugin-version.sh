#!/usr/bin/env bash
#
# set-plugin-version.sh — set the plugin package version across every plugin in
# this repo.
#
# Updates the "version" field in each plugin manifest (.claude-plugin/plugin.json
# and .codex-plugin/plugin.json) and the "Version **x.y.z**" line in each
# plugin README, for both the dev-* and sql-* plugins across claude/, codex/,
# and opencode/. (OpenCode has no manifest version field, so only its README is
# updated. CHANGELOG history is intentionally left untouched.)
#
# This is the plugin *package* version, NOT the mariadb-shell binary version —
# use scripts/set-mariadb-shell-version.sh for the latter.
#
# Usage:
#   scripts/set-plugin-version.sh <version>
#   scripts/set-plugin-version.sh 26.7.0

set -euo pipefail

VERSION="${1:-}"
[ -n "$VERSION" ] || { echo "usage: $0 <version>   (e.g. 26.7.0)" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

command -v perl >/dev/null 2>&1 || { echo "error: perl is required" >&2; exit 1; }

# Collect manifests and READMEs across every *-plugin dir (excludes test dirs).
files=()
while IFS= read -r f; do files+=("$f"); done < <(
  find "$REPO_ROOT"/claude/*-plugin \
       "$REPO_ROOT"/codex/*-plugin \
       "$REPO_ROOT"/opencode/*-plugin \
       -type f \( -name 'plugin.json' -o -name 'README.md' \) | sort
)

[ "${#files[@]}" -gt 0 ] || { echo "error: no plugin files found under $REPO_ROOT" >&2; exit 1; }

# Two shapes the version appears in:
#   plugin manifest JSON:  "version": "<v>"
#   README header line:    Version **<v>**
V="$VERSION" perl -i -pe '
  my $v = $ENV{V};
  s/("version"\s*:\s*")[^"]*(")/${1}${v}${2}/g;
  s/^(Version \*\*)[^*]*(\*\*)$/${1}${v}${2}/g;
' "${files[@]}"

echo "Set plugin version -> $VERSION in ${#files[@]} file(s):"
grep -rnE "\"version\": \"${VERSION}\"|^Version \*\*${VERSION}\*\*" "${files[@]}" \
  | sed 's/^/  /'
