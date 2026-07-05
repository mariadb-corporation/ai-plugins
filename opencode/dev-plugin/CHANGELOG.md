# Changelog

All notable changes to the MariaDB OpenCode plugin are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/), and this
project adheres to [Semantic Versioning](https://semver.org/).

## [0.0.2] - 2026-07-05

### Added

- Vendored the repo-local `additional-skills/` tree alongside the upstream skills:
  `mariadb-schema-create-script` (25 skills total). These are recorded in the
  manifest under an `additional` layer.

### Changed

- The flat skill layout (already used by OpenCode) is now shared by every plugin
  in the repo, so all three are identical on disk.

## [0.0.1] - 2026-06-30

### Added

- Initial release of the MariaDB plugin for OpenCode.
- 24 MariaDB agent skills vendored from
  [`mariadb-corporation/mariadb-docs/agent-skills`](https://github.com/mariadb-corporation/mariadb-docs/tree/main/agent-skills)
  (baseline MariaDB 11.8 LTS):
  - 12 granular statement skills, 5 function skills, 2 tool skills, 5 topical skills.
  - Vendored in a flat layout, since OpenCode discovers skills only one directory deep.
- Native `mariadb-shell` MCP server, configured in `opencode.json` and launched via
  `scripts/mariadb-mcp-launcher.sh` (and `.cmd` for Windows), which detects OS/arch
  and downloads the matching release binary from `mariadb-corporation/mariadb-shell`
  into a user cache dir.
- Skills kept in sync by the repo-wide `scripts/sync-skills.sh` (flat layout for this
  target).
