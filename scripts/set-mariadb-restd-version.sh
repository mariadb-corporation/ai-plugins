#!/usr/bin/env bash
#
# Copyright (c) 2026, MariaDB plc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License, version 2.0,
# as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See
# the GNU General Public License, version 2.0, for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
#
# set-mariadb-restd-version.sh — set the mariadb-restd floor across every plugin
# in this repo.
#
# The MCP server (the mariadb-shell MCP plugin) reads MARIADB_RESTD_VERSION: when
# an agent sets up a REST Daemon with restd.configure_restd and names no version,
# an installed mariadb-restd older than this is passed over and the newest
# release installed. It is the restd counterpart of MARIADB_SHELL_VERSION, kept
# in the same places (see scripts/set-mariadb-shell-version.sh): each plugin's
# MCP config, the MCP launchers' fallback, the setup-codex-mcp scripts, the
# plugin READMEs and the docs-ref variable table. The launchers do not read it;
# they only pass it on, so Pi, which has no MCP config, gets the fallback.
#
# Usage:
#   scripts/set-mariadb-restd-version.sh <version>
#   scripts/set-mariadb-restd-version.sh 26.11.0
#   scripts/set-mariadb-restd-version.sh --help

set -euo pipefail

usage() {
  cat <<'USAGE'
set-mariadb-restd-version.sh — set the mariadb-restd floor across every plugin
in this repo.

Usage:
  scripts/set-mariadb-restd-version.sh <version>
  scripts/set-mariadb-restd-version.sh --help

Arguments:
  <version>   The lowest mariadb-restd the MCP server accepts when an agent
              names none, e.g. 26.11.0: X.Y.Z, as every mariadb-restd release
              is. It has to be a published release of
              mariadb-corporation/rest-daemon.

Updates, across claude/, codex/, opencode/, pi/ and hermes/:
  - MARIADB_RESTD_VERSION in each plugin's MCP config (.mcp.json,
    opencode.json, mcp.json)
  - the fallback in the MCP launchers (mariadb-mcp-launcher.sh / .cmd)
  - the version the setup-codex-mcp scripts write
  - the MARIADB_RESTD_VERSION default shown in each plugin README
  - the default in the docs-ref Configuration Reference
  - in hermes/, the committed copy of release v<version>'s SHA256SUMS that the
    MCP server checks the package against (downloaded, so this needs the
    release to be published)
USAGE
}

case "${1:-}" in
  -h | --help | help)
    usage
    exit 0
    ;;
esac

VERSION="${1:-}"
if [ -z "$VERSION" ]; then
  echo "error: no version given" >&2
  echo >&2
  usage >&2
  exit 1
fi
case "$VERSION" in
  -*)
    echo "error: unknown option '$VERSION' (see --help)" >&2
    exit 1
    ;;
esac
VERSION="${VERSION#v}"
if ! printf '%s' "$VERSION" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$'; then
  echo "error: '$VERSION' is not a mariadb-restd version (expected X.Y.Z, e.g. 26.11.0)" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

command -v perl >/dev/null 2>&1 || { echo "error: perl is required" >&2; exit 1; }

# A floor no launcher can install would make every agent's setup fail: checked
# before anything is edited. The release's SHA256SUMS is what its install
# scripts read, so a release without one could not be installed either.
#
# Hermes' launchers pin mariadb-restd as they pin the shell: they pass on
# v<version> and a copy of that release's SHA256SUMS committed next to them,
# which this replaces too.
SUMS_URL="https://github.com/mariadb-corporation/rest-daemon/releases/download/v$VERSION/SHA256SUMS"
SUMS_TMP="$(mktemp)"
trap 'rm -f "$SUMS_TMP"' EXIT
curl -fsSL --retry 3 -o "$SUMS_TMP" "$SUMS_URL" || {
  echo "error: could not download $SUMS_URL — is mariadb-restd v$VERSION published?" >&2
  exit 1
}
grep -Eq "^[0-9a-f]{64}  mariadb-restd-$VERSION-" "$SUMS_TMP" || {
  echo "error: $SUMS_URL does not list mariadb-restd $VERSION packages" >&2
  exit 1
}

files=()
while IFS= read -r f; do files+=("$f"); done < <(
  find "$REPO_ROOT"/claude/*-plugin \
       "$REPO_ROOT"/codex/*-plugin \
       "$REPO_ROOT"/opencode/*-plugin \
       "$REPO_ROOT"/pi/*-plugin \
       "$REPO_ROOT"/hermes/*-plugin \
       -type f \( \
         -name 'mariadb-mcp-launcher.sh' -o \
         -name 'mariadb-mcp-launcher.cmd' -o \
         -name 'setup-codex-mcp.sh' -o \
         -name 'setup-codex-mcp.cmd' -o \
         -name '.mcp.json' -o \
         -name 'mcp.json' -o \
         -name 'opencode.json' -o \
         -name 'README.md' \
       \) | sort
)
[ "${#files[@]}" -gt 0 ] || { echo "error: no plugin files found under $REPO_ROOT" >&2; exit 1; }

DOCS_REF="$REPO_ROOT/docs-ref/content/community/mariadb-ai-plugins/configuration-reference.md"
[ -f "$DOCS_REF" ] && files+=("$DOCS_REF")

# Shapes the version appears in:
#   JSON MCP config:          "MARIADB_RESTD_VERSION": "<v>"
#   bash launcher:            MARIADB_RESTD_VERSION="${MARIADB_RESTD_VERSION:-<v>}"
#   cmd launcher, setup .cmd: set "MARIADB_RESTD_VERSION=<v>"
#   setup-codex-mcp.sh:       RESTD_VERSION="<v>"
#   README prose:             `MARIADB_RESTD_VERSION` (default `<v>`)
#   docs-ref variable table:  | `MARIADB_RESTD_VERSION` | `<v>` |
#   Hermes README checksum:   mariadb-restd-v<v>.SHA256SUMS
V="$VERSION" perl -i -pe '
  my $v = $ENV{V};
  s/("MARIADB_RESTD_VERSION"\s*:\s*")[^"]*(")/${1}${v}${2}/g;
  s/(MARIADB_RESTD_VERSION:-)[^}]*(\})/${1}${v}${2}/g;
  s/(set "MARIADB_RESTD_VERSION=)[^"]*(")/${1}${v}${2}/g;
  s/^(RESTD_VERSION=")[^"]*(")/${1}${v}${2}/g;
  s/(MARIADB_RESTD_VERSION` \(default `)[^`]*(`\))/${1}${v}${2}/g;
  s/^(\| `MARIADB_RESTD_VERSION` \| `)[^`]*(` \|)/${1}${v}${2}/g;
  s/(mariadb-restd-v)[0-9][0-9.]*(\.SHA256SUMS)/${1}${v}${2}/g;
' "${files[@]}"

for dir in "$REPO_ROOT"/hermes/*-plugin/scripts; do
  [ -f "$dir/mariadb-mcp-launcher.sh" ] || continue
  rm -f "$dir"/mariadb-restd-v*.SHA256SUMS
  cp "$SUMS_TMP" "$dir/mariadb-restd-v$VERSION.SHA256SUMS"
  chmod 644 "$dir/mariadb-restd-v$VERSION.SHA256SUMS"
  echo "Wrote ${dir#"$REPO_ROOT"/}/mariadb-restd-v$VERSION.SHA256SUMS"
done

echo "Set MARIADB_RESTD_VERSION -> $VERSION in:"
grep -ln "RESTD_VERSION.*$VERSION" "${files[@]}" | sed "s|^$REPO_ROOT/|  |"
