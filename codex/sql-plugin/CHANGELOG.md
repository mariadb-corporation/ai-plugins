# Changelog

All notable changes to the MariaDB SQL Codex plugin are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/), and this
project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed

- **Codex 0.147 compatibility.** Three things kept this plugin from working as
  installed, all of them silent:
  - `.mcp.json` declared its server under `mcp_servers`; Codex reads only
    `mcpServers`, so it registered nothing at all. Renamed.
  - the command used `${CODEX_PLUGIN_ROOT}`, which is not a name Codex knows (it
    recognises `${CLAUDE_PLUGIN_ROOT}` alone). Renamed.
  - Codex resolves `dev@mariadb` through `.agents/plugins/marketplace.json`,
    falling back to `.claude-plugin/marketplace.json`, and never reads
    `.codex-plugin/marketplace.json` — so installing from this repo gave Codex the
    *Claude* plugin. The repo now ships `.agents/plugins/marketplace.json`, and the
    unread `.codex-plugin/marketplace.json` has been deleted rather than left to
    drift out of sync with it. (The per-plugin `.codex-plugin/plugin.json` stays —
    Codex does read that, and without it the installed version degrades to
    `local`.)
- **New `scripts/setup-codex-mcp.sh`.** Codex expands no placeholder when it
  spawns a plugin's MCP server, so a plugin cannot register a working one; the
  script does it with `codex mcp add` and an absolute path. Registering is now a
  documented second installation step.

### Changed

- The `mariadb-shell` launcher no longer downloads and unpacks release assets
  itself. It now runs the first shell that satisfies `MARIADB_SHELL_VERSION`
  (`$MARIADB_SHELL_BIN`, one on `PATH`, or an existing install in `~/.local/bin`
  / `%LOCALAPPDATA%\Programs\mariadb-shell\bin`), and otherwise delegates to the
  shell's own `install.sh` / `install.ps1` — which selects the package for this
  OS, CPU and glibc version and verifies it against the release's `SHA256SUMS`.
  Asset naming is no longer duplicated here, so the launcher cannot go stale as
  releases change.
- `MARIADB_SHELL_VERSION` now means the *minimum* acceptable version and defaults
  to `26.8.0`, matching the published release series.
- New pass-through settings: `MARIADB_SHELL_BINDIR`, `MARIADB_SHELL_PREFIX`,
  `MARIADB_SHELL_TAG`, `MARIADB_SHELL_PRERELEASE` (needed while the only
  published release is a prerelease) and `MARIADB_SHELL_TOKEN` (`GH_TOKEN`,
  `GITHUB_TOKEN` and `gh auth token` are still honoured).

## [26.7.0] - 2026-07-20

### Added

- Initial release of the MariaDB SQL plugin for Codex.
- MariaDB agent skills vendored from
  [`mariadb-corporation/mariadb-docs/agent-skills`](https://github.com/mariadb-corporation/mariadb-docs/tree/main/agent-skills)
  (baseline MariaDB 11.8 LTS): SQL statement, function, and topical skills. The
  client-tool skills (`granular/tools`) are intentionally omitted from this
  SQL-focused plugin.
- Native `mariadb-shell` MCP server, launched via `scripts/mariadb-mcp-launcher.sh`
  (and `.cmd` for Windows), which detects OS/arch and downloads the matching
  release binary from `mariadb-corporation/mariadb-shell` into a user cache dir.
- Skills kept in sync by the repo-wide `scripts/sync-skills.sh`.
- Marketplace entry for `/plugin install`.
