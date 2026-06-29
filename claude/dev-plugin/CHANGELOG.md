# Changelog

All notable changes to the MariaDB Claude Code plugin are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/), and this
project adheres to [Semantic Versioning](https://semver.org/).

## [0.0.1] - 2026-06-29

### Added

- Initial release of the MariaDB plugin for Claude Code.
- 24 MariaDB agent skills vendored from
  [`mariadb-corporation/mariadb-docs/agent-skills`](https://github.com/mariadb-corporation/mariadb-docs/tree/main/agent-skills)
  (baseline MariaDB 11.8 LTS):
  - 12 granular statement skills, 5 function skills, 2 tool skills, 5 topical skills.
- Native `mariadb-shell` MCP server, launched via `scripts/mariadb-mcp-launcher.sh`
  (and `.cmd` for Windows), which detects OS/arch and downloads the matching
  release binary from `mariadb-corporation/mariadb-shell` into a user cache dir.
- `scripts/sync-skills.sh` to (re)vendor skills from a pinned upstream ref.
- Marketplace entry for `/plugin install`.
