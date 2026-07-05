# Changelog

All notable changes to the MariaDB Codex plugin are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/), and this
project adheres to [Semantic Versioning](https://semver.org/).

## [0.0.2] - 2026-07-05

### Changed

- Skills are now vendored in a flat layout (`skills/<skill>/SKILL.md`) instead of
  preserving the upstream layer directories, so every plugin in the repo is
  identical on disk. The vendored `.skills-manifest.json` records the flat paths.

### Added

- Vendored the repo-local `additional-skills/` tree alongside the upstream skills:
  `mariadb-schema-create-script` (25 skills total). These are recorded in the
  manifest under an `additional` layer.

## [0.0.1] - 2026-06-30

### Added

- Initial release of the MariaDB plugin for Codex.
- 24 MariaDB agent skills vendored from
  [`mariadb-corporation/mariadb-docs/agent-skills`](https://github.com/mariadb-corporation/mariadb-docs/tree/main/agent-skills)
  (baseline MariaDB 11.8 LTS):
  - 12 granular statement skills, 5 function skills, 2 tool skills, 5 topical skills.
- Native `mariadb-shell` MCP server, launched via `scripts/mariadb-mcp-launcher.sh`
  (and `.cmd` for Windows), which detects OS/arch and downloads the matching
  release binary from `mariadb-corporation/mariadb-shell` into a user cache dir.
- `scripts/sync-skills.sh` to (re)vendor skills from a pinned upstream ref.
- Marketplace entry for `/plugin install`.
