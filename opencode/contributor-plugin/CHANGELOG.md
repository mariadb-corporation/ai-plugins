# Changelog

All notable changes to the MariaDB contributor OpenCode plugin are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/), and this
project adheres to [Semantic Versioning](https://semver.org/).

## [26.9.0] - 2026-09-02

### Added

- `review-shell-change` skill, bringing the plugin to two skills.

### Changed

- Skills re-vendored from `mariadb-corporation/mariadb-shell` `.claude/skills/`
  at commit `2b2d0aa` (synced 2026-09-01); the same sync refreshed
  `create-shell-plugin`.
- The bundled `LICENSE` is now the MariaDB Shell Licensing Information User
  Manual, re-copied from the repo root, in place of the bare GPL-2.0 text.
- Version bumped to 26.9.0 to stay in lockstep with the other plugins. This
  plugin ships skills only and no MCP server, so the `MARIADB_SHELL_VERSION`
  floor the others moved to 26.9.0 does not apply here.

## [26.7.0] - 2026-07-22

### Added

- Initial release of the MariaDB contributor plugin for OpenCode.
- Skills for contributing to MariaDB tooling, vendored from the
  `mariadb-corporation/mariadb-shell` repository's `.claude/skills/` tree by the
  repo-wide `scripts/sync-skills.sh`. Skills only — no MCP server yet.
