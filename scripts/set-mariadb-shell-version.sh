#!/usr/bin/env bash
#
# set-mariadb-shell-version.sh — pin the mariadb-shell MCP server version across
# every plugin in this repo.
#
# Updates the MARIADB_SHELL_VERSION value in each plugin's MCP config
# (.mcp.json / opencode.json) AND the fallback default baked into the
# launcher scripts (mariadb-mcp-launcher.sh/.cmd and their _disabled variants),
# for both the dev-* and sql-* plugins across claude/, codex/, and opencode/.
# Keeping all of them on the same version means every plugin resolves the same
# cached binary (see scripts/mariadb-mcp-launcher.sh — the cache is keyed by
# version only, so one version == one shared download).
#
# This is the mariadb-shell *binary* version, NOT the plugin package version —
# use scripts/set-plugin-version.sh for the latter.
#
# Usage:
#   scripts/set-mariadb-shell-version.sh <version>
#   scripts/set-mariadb-shell-version.sh 9.7.0

set -euo pipefail

VERSION="${1:-}"
[ -n "$VERSION" ] || { echo "usage: $0 <version>   (e.g. 9.7.0)" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

command -v perl >/dev/null 2>&1 || { echo "error: perl is required" >&2; exit 1; }

# Collect the files that carry the version: launcher scripts (all variants) and
# the MCP config files, across every *-plugin dir (excludes *-plugin-test dirs).
files=()
while IFS= read -r f; do files+=("$f"); done < <(
  find "$REPO_ROOT"/claude/*-plugin \
       "$REPO_ROOT"/codex/*-plugin \
       "$REPO_ROOT"/opencode/*-plugin \
       -type f \( \
         -name 'mariadb-mcp-launcher.sh' -o \
         -name 'mariadb-mcp-launcher.cmd' -o \
         -name '.mcp.json' -o \
         -name 'opencode.json' -o \
         -name 'README.md' \
       \) | sort
)

[ "${#files[@]}" -gt 0 ] || { echo "error: no plugin files found under $REPO_ROOT" >&2; exit 1; }

# Shapes the version appears in:
#   JSON MCP config / README example:  "MARIADB_SHELL_VERSION": "<v>"
#   bash launcher:                     VERSION="${MARIADB_SHELL_VERSION:-<v>}"
#   cmd launcher:                      set "MARIADB_SHELL_VERSION=<v>"
#   README prose:                      `MARIADB_SHELL_VERSION` (default `<v>`)
V="$VERSION" perl -i -pe '
  my $v = $ENV{V};
  s/("MARIADB_SHELL_VERSION"\s*:\s*")[^"]*(")/${1}${v}${2}/g;
  s/(MARIADB_SHELL_VERSION:-)[^}]*(\})/${1}${v}${2}/g;
  s/(set "MARIADB_SHELL_VERSION=)[^"]*(")/${1}${v}${2}/g;
  s/(MARIADB_SHELL_VERSION` \(default `)[^`]*(`\))/${1}${v}${2}/g;
' "${files[@]}"

echo "Set MARIADB_SHELL_VERSION -> $VERSION in ${#files[@]} file(s):"
grep -rn 'MARIADB_SHELL_VERSION' "${files[@]}" \
  | grep -E "\-${VERSION}\}|=${VERSION}\"|: \"${VERSION}\"" \
  | sed 's/^/  /'
