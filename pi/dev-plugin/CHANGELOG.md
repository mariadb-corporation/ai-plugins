# Changelog

All notable changes to the MariaDB plugin for Pi are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/), and this
project adheres to [Semantic Versioning](https://semver.org/).

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
