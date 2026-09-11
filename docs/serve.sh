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
# serve.sh — preview the DevHub site (docs/) locally.
#
# Runs Jekyll against docs/ and prints the URL *including the baseurl*, which is
# the detail that trips people up: `baseurl` is set to the GitHub Pages project
# path, so the site lives at http://127.0.0.1:4000/ai-plugins/ and a bare `/`
# answers 404.
#
# It adapts to whichever toolchain is present, in this order:
#
#   1. `bundle exec jekyll` when docs/Gemfile.lock exists — the closest match to
#      what GitHub actually builds with (the pinned `github-pages` bundle).
#   2. A plain `jekyll` otherwise, with JEKYLL_NO_BUNDLER_REQUIRE set so it does
#      not read the Gemfile and demand `github-pages` that was never installed.
#
# Both plugins in _config.yml are REQUIRED, not optional: _includes/head.html
# calls {% seo %}, which is an unknown Liquid tag without jekyll-seo-tag, and
# Jekyll aborts on a plugin it cannot require. So the script preflights them and
# fails with the install command rather than producing a half-built site.
#
# Usage:
#   docs/serve.sh                  # serve with live reload on :4000
#   docs/serve.sh --port 4010      # a different port
#   docs/serve.sh --open           # …and open a browser
#   docs/serve.sh --build          # build into docs/_site and exit
#   docs/serve.sh -- --incremental # pass anything else straight to jekyll
#   docs/serve.sh --help
#
# Overrides: JEKYLL_BIN, HOST, PORT.

set -euo pipefail

DOCS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-4000}"
MODE="serve"
OPEN=0
PASSTHRU=()

usage() {
  cat <<'USAGE'
serve.sh — preview the DevHub site (docs/) locally.

Usage:
  docs/serve.sh                  Serve with live reload on http://127.0.0.1:4000/<baseurl>/
  docs/serve.sh --port 4010      Serve on a different port
  docs/serve.sh --open           Serve and open a browser at the right URL
  docs/serve.sh --build          Build into docs/_site and exit (no server)
  docs/serve.sh -- <args...>     Pass the remaining args straight to jekyll
  docs/serve.sh --help

Environment:
  JEKYLL_BIN   The jekyll executable to use (default: the one on PATH).
  HOST, PORT   Bind address and port (default: 127.0.0.1 and 4000).

Remember the baseurl: the site is served under the path in docs/_config.yml,
so a bare / answers 404. The script prints the full URL.
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --build)        MODE="build"; shift ;;
    --open|-o)      OPEN=1; shift ;;
    --port|-P)      PORT="${2:?--port needs a value}"; shift 2 ;;
    --host|-H)      HOST="${2:?--host needs a value}"; shift 2 ;;
    --help|-h)      usage; exit 0 ;;
    --)             shift; PASSTHRU=("$@"); break ;;
    *)              echo "serve.sh: unknown argument '$1' (try --help)" >&2; exit 2 ;;
  esac
done

# --- Resolve a jekyll -------------------------------------------------------
# `gem install jekyll` puts the executable in the gem bin dir, which is not
# always on PATH on a Homebrew Ruby — so look there before giving up.
resolve_jekyll() {
  if [ -n "${JEKYLL_BIN:-}" ]; then
    printf '%s\n' "$JEKYLL_BIN"; return 0
  fi
  if command -v jekyll >/dev/null 2>&1; then
    command -v jekyll; return 0
  fi
  local gem_bin
  gem_bin="$(gem environment gemdir 2>/dev/null || true)"
  if [ -n "$gem_bin" ] && [ -x "$gem_bin/bin/jekyll" ]; then
    printf '%s\n' "$gem_bin/bin/jekyll"; return 0
  fi
  return 1
}

if ! JEKYLL="$(resolve_jekyll)"; then
  cat >&2 <<'ERR'
serve.sh: no jekyll found.

Install one of:
  gem install jekyll jekyll-seo-tag jekyll-sitemap    # quick local preview
  cd docs && bundle install                           # matches GitHub Pages

If jekyll is installed but not on PATH, point JEKYLL_BIN at it, or add the gem
bin directory (`gem environment gemdir`/bin) to PATH.
ERR
  exit 1
fi

# --- Pick a runner ----------------------------------------------------------
cd "$DOCS_DIR"

# A Gemfile.lock means `bundle install` was run here, so bundler can resolve the
# github-pages bundle — the build GitHub itself performs. Without one, reading
# the Gemfile would only produce "Could not find gem 'github-pages'".
if [ -f Gemfile.lock ] && command -v bundle >/dev/null 2>&1; then
  RUNNER=(bundle exec "$JEKYLL")
  BUNDLED=1
else
  export JEKYLL_NO_BUNDLER_REQUIRE=true
  RUNNER=("$JEKYLL")
  BUNDLED=0
fi

# --- Preflight the plugins --------------------------------------------------
# Ask the Ruby that will actually run Jekyll, NOT whatever `gem` comes first on
# PATH. macOS ships a system Ruby whose `gem` at /usr/bin/gem has a completely
# separate gem set — it reports zero jekyll gems while a Homebrew Ruby has them
# all. A PATH that reaches the gem bin directory (so `jekyll` resolves) without
# reaching /opt/homebrew/bin (so `gem` does not) is easy to end up with, and an
# editor launched from the Dock rather than a shell often has exactly that. The
# old `gem list -i` check then failed on gems that were installed and working.
#
# Only meaningful for the non-bundler path; under `bundle exec` the gems come
# from the lockfile instead.

# The interpreter from the jekyll shim's shebang, or nothing if it cannot be read.
ruby_for_jekyll() {
  local line interp
  line="$(head -1 "$JEKYLL" 2>/dev/null || true)"
  case "$line" in
    "#!"*) interp="${line#\#!}" ;;
    *)     return 1 ;;
  esac
  case "$interp" in
    # "#!/usr/bin/env ruby" — look the interpreter up on PATH instead.
    */env[[:space:]]*) interp="$(command -v "${interp##*[[:space:]]}" 2>/dev/null || true)" ;;
    # Otherwise drop any arguments after the interpreter path.
    *)                 interp="${interp%%[[:space:]]*}" ;;
  esac
  [ -n "$interp" ] && [ -x "$interp" ] || return 1
  printf '%s\n' "$interp"
}

# A false "missing gem" is worse than no preflight, so when the Ruby cannot be
# identified this is skipped and Jekyll reports the real problem itself.
# NB the rescue clause: find_by_name raises Gem::MissingSpecError, whose ancestry
# is Gem::LoadError < LoadError < ScriptError < Exception — it is NOT a
# StandardError, so a bare `rescue` does not catch it. Getting that wrong made
# the whole check inert: ruby aborted, the status was discarded, and every gem
# looked present.
#
# The status is honoured here too: a ruby that fails for any other reason means
# "could not determine", and the preflight is skipped rather than passed.
if [ "$BUNDLED" = "0" ] && RUBY_BIN="$(ruby_for_jekyll)" &&
   missing="$("$RUBY_BIN" -e '
     puts ARGV.reject { |name|
       begin
         Gem::Specification.find_by_name(name)
         true
       rescue Gem::LoadError, StandardError
         false
       end
     }.join(" ")
   ' jekyll-seo-tag jekyll-sitemap 2>/dev/null)"
then
  if [ -n "$missing" ]; then
    cat >&2 <<ERR
serve.sh: missing required gem(s): $missing

  gem install $missing

These are not optional decoration. _includes/head.html calls {% seo %}, which is
an unknown Liquid tag without jekyll-seo-tag, and Jekyll aborts on any plugin in
_config.yml it cannot require.

Checked against the Ruby that runs jekyll:
  jekyll: $JEKYLL
  ruby:   $RUBY_BIN
Install into that Ruby. Running gem from a different Ruby installs elsewhere
and will not help.
ERR
    exit 1
  fi
fi

CONFIGS="_config.yml"

if [ "$MODE" = "build" ]; then
  echo "serve.sh: building into $DOCS_DIR/_site"
  exec "${RUNNER[@]}" build --config "$CONFIGS" ${PASSTHRU[@]+"${PASSTHRU[@]}"}
fi

# Print the URL with the baseurl attached — a bare / is a 404 and everyone hits
# it once. `grep` rather than a YAML parser: it is one well-known line.
BASEURL="$(grep -E '^baseurl:' _config.yml | head -1 | sed -E 's/^baseurl:[[:space:]]*"?([^"#]*)"?.*/\1/' | tr -d '[:space:]')"
echo "serve.sh: http://${HOST}:${PORT}${BASEURL}/"

SERVE_ARGS=(serve --config "$CONFIGS" --host "$HOST" --port "$PORT" --livereload)
[ "$OPEN" = "1" ] && SERVE_ARGS+=(--open-url)

exec "${RUNNER[@]}" "${SERVE_ARGS[@]}" ${PASSTHRU[@]+"${PASSTHRU[@]}"}
