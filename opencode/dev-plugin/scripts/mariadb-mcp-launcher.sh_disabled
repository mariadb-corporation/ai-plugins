#!/usr/bin/env bash
#
# mariadb-mcp-launcher.sh — download (if needed) and launch the mariadb-shell
# native MCP server.
#
# Detects OS + CPU arch, downloads the matching release asset from
# github.com/mariadb-corporation/mariadb-shell into a user cache dir, verifies
# its checksum, and execs it. All arguments are passed through to the binary
# (e.g. the "mcp" subcommand from .mcp.json), and stdio is left untouched so the
# MCP transport works.
#
# Environment:
#   MARIADB_SHELL_VERSION   Release version/tag to use (default below).
#   MARIADB_SHELL_BIN       Path to a pre-installed binary; skips all download logic.
#   GH_TOKEN                Optional token for downloading from a private release.

set -euo pipefail

VERSION="${MARIADB_SHELL_VERSION:-2026.7.0}"
REPO="mariadb-corporation/mariadb-shell"

log() { echo "mariadb-mcp-launcher: $*" >&2; }
die() { log "error: $*"; exit 1; }

# Escape hatch: use an explicitly provided binary.
if [ -n "${MARIADB_SHELL_BIN:-}" ]; then
  [ -x "$MARIADB_SHELL_BIN" ] || die "MARIADB_SHELL_BIN is not executable: $MARIADB_SHELL_BIN"
  exec "$MARIADB_SHELL_BIN" "$@"
fi

# --- Detect OS ---------------------------------------------------------------
case "$(uname -s)" in
  Darwin)            OS="darwin" ;;
  Linux)             OS="linux" ;;
  MINGW*|MSYS*|CYGWIN*) OS="windows" ;;
  *)                 die "unsupported OS: $(uname -s)" ;;
esac

# --- Detect arch -------------------------------------------------------------
case "$(uname -m)" in
  x86_64|amd64)   ARCH="amd64" ;;
  arm64|aarch64)  ARCH="arm64" ;;
  *)              die "unsupported arch: $(uname -m)" ;;
esac

# --- Asset + cache paths -----------------------------------------------------
# NOTE: adjust EXT / asset naming to match the real mariadb-shell release assets.
if [ "$OS" = "windows" ]; then EXT="zip"; BIN_NAME="mariadb-shell.exe"; else EXT="tar.gz"; BIN_NAME="mariadb-shell"; fi
ASSET="mariadb-shell_${VERSION}_${OS}_${ARCH}.${EXT}"

CACHE_BASE="${XDG_CACHE_HOME:-$HOME/.cache}/mariadb/mariadb-shell/${VERSION}"
BIN="$CACHE_BASE/$BIN_NAME"

# Already cached? Run it.
if [ -x "$BIN" ]; then
  exec "$BIN" "$@"
fi

# --- Download ----------------------------------------------------------------
mkdir -p "$CACHE_BASE"
BASE_URL="https://github.com/$REPO/releases/download/$VERSION"

# Pick a downloader.
if command -v curl >/dev/null 2>&1; then
  dl() { curl -fsSL ${GH_TOKEN:+-H "Authorization: Bearer $GH_TOKEN"} -o "$2" "$1"; }
elif command -v wget >/dev/null 2>&1; then
  dl() { wget -q ${GH_TOKEN:+--header="Authorization: Bearer $GH_TOKEN"} -O "$2" "$1"; }
else
  die "neither curl nor wget is available"
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

log "downloading $ASSET ($OS/$ARCH) ..."
dl "$BASE_URL/$ASSET" "$TMP/$ASSET" || die "failed to download $BASE_URL/$ASSET"

# --- Verify checksum (best effort; fails loudly on mismatch) -----------------
if dl "$BASE_URL/checksums.txt" "$TMP/checksums.txt" 2>/dev/null; then
  expected="$(grep " ${ASSET}\$\|  ${ASSET}\$" "$TMP/checksums.txt" | awk '{print $1}' | head -n1 || true)"
  if [ -n "$expected" ]; then
    if command -v sha256sum >/dev/null 2>&1; then
      actual="$(sha256sum "$TMP/$ASSET" | awk '{print $1}')"
    else
      actual="$(shasum -a 256 "$TMP/$ASSET" | awk '{print $1}')"
    fi
    [ "$expected" = "$actual" ] || die "checksum mismatch for $ASSET (expected $expected, got $actual)"
    log "checksum verified"
  else
    log "warning: $ASSET not listed in checksums.txt — skipping verification"
  fi
else
  log "warning: checksums.txt not available — skipping verification"
fi

# --- Extract -----------------------------------------------------------------
case "$EXT" in
  tar.gz) tar -xzf "$TMP/$ASSET" -C "$TMP" ;;
  zip)    (command -v unzip >/dev/null 2>&1 && unzip -q "$TMP/$ASSET" -d "$TMP") || die "unzip required for $ASSET" ;;
esac

SRC_BIN="$(find "$TMP" -type f -name "$BIN_NAME" | head -n1)"
[ -n "$SRC_BIN" ] || die "$BIN_NAME not found in $ASSET"

# Atomic install into the cache.
chmod +x "$SRC_BIN"
mv -f "$SRC_BIN" "$BIN.partial"
mv -f "$BIN.partial" "$BIN"

log "installed to $BIN"
exec "$BIN" "$@"
