# Changelog

All notable changes to the MariaDB plugin for Pi are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/), and this
project adheres to [Semantic Versioning](https://semver.org/).

## [26.9.0] - 2026-09-02

### Changed

- The launcher now **prefers a stable release and falls back to a prerelease**
  when there is no stable one to install, so no `MARIADB_SHELL_PRERELEASE=1` is
  needed while `mariadb-shell` has only prereleases. Setting it to `1` still skips
  straight to a prerelease, and `0` refuses one and keeps the install
  stable-only.
- The `mariadb-shell` launcher no longer downloads and unpacks release assets
  itself. It now runs the first shell that satisfies `MARIADB_SHELL_VERSION`
  (`$MARIADB_SHELL_BIN`, one on `PATH`, or an existing install in `~/.local/bin`
  / `%LOCALAPPDATA%\Programs\mariadb-shell\bin`), and otherwise delegates to the
  shell's own `install.sh` / `install.ps1` — which selects the package for this
  OS, CPU and glibc version and verifies it against the release's `SHA256SUMS`.
  Asset naming is no longer duplicated here, so the launcher cannot go stale as
  releases change.
- `MARIADB_SHELL_VERSION` now means the *minimum* acceptable version and defaults
  to `26.9.0`, matching the published release series.
- New pass-through settings: `MARIADB_SHELL_BINDIR`, `MARIADB_SHELL_PREFIX`,
  `MARIADB_SHELL_TAG`, `MARIADB_SHELL_PRERELEASE` (needed while the only
  published release is a prerelease) and `MARIADB_SHELL_TOKEN` (`GH_TOKEN`,
  `GITHUB_TOKEN` and `gh auth token` are still honoured).

## [26.7.0] - 2026-07-30

### Added

- Initial release of the MariaDB plugin for the [Pi coding agent](https://pi.dev),
  packaged as a **pi extension** (`package.json` `pi` field declaring
  `extensions` + `skills`).
- The extension (`src/index.ts`) registers a `/mariadb-mcp-setup` command and, at
  session start, reminds the user to enable the MCP server when it isn't wired up.
- `pi-mcp-adapter` is declared as a dependency: the native `mariadb-shell` MCP
  server is surfaced to pi through the adapter's `mcp` proxy tool.
- `scripts/setup-pi-mcp.sh` registers the mariadb-shell server in the
  pi-mcp-adapter `mcp.json` config (global `~/.config/mcp/mcp.json` by default, or
  project-local `./.mcp.json` with `--project`); idempotent and merge-preserving.
- Native `mariadb-shell` launcher (`scripts/mariadb-mcp-launcher.sh` + `.cmd`),
  shared verbatim with the other plugins.
- MariaDB agent skills vendored flat from
  [`mariadb-corporation/mariadb-docs/agent-skills`](https://github.com/mariadb-corporation/mariadb-docs/tree/main/agent-skills)
  (baseline MariaDB 11.8 LTS) by the repo-root `scripts/sync-skills.sh`.
