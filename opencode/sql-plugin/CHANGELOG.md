# Changelog

All notable changes to the MariaDB SQL OpenCode plugin are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/), and this
project adheres to [Semantic Versioning](https://semver.org/).

## [26.7.0] - 2026-07-20

### Added

- Initial release of the MariaDB SQL plugin for OpenCode.
- MariaDB agent skills vendored from
  [`mariadb-corporation/mariadb-docs/agent-skills`](https://github.com/mariadb-corporation/mariadb-docs/tree/main/agent-skills)
  (baseline MariaDB 11.8 LTS): SQL statement, function, and topical skills. The
  client-tool skills (`granular/tools`) are intentionally omitted from this
  SQL-focused plugin.
  - Vendored in a flat layout, since OpenCode discovers skills only one directory deep.
- Native `mariadb-shell` MCP server, configured in `opencode.json` and launched via
  `scripts/mariadb-mcp-launcher.sh` (and `.cmd` for Windows), which detects OS/arch
  and downloads the matching release binary from `mariadb-corporation/mariadb-shell`
  into a user cache dir.
- Skills kept in sync by the repo-wide `scripts/sync-skills.sh` (flat layout for this
  target).
