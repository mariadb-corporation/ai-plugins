# MariaDB plugin for Claude Code

Version **26.7.0**

This plugin gives Claude Code first-class MariaDB support through two parts:

1. **Skills** — MariaDB agent skills (SQL statements, functions, client tools,
   and topical deep-dives) vendored from
   [`mariadb-corporation/mariadb-docs/agent-skills`](https://github.com/mariadb-corporation/mariadb-docs/tree/main/agent-skills),
   baseline **MariaDB 11.8 LTS**.
2. **A native MCP server** — the [`mariadb-shell`](https://github.com/mariadb-corporation/mariadb-shell)
   binary, started automatically by a launcher that downloads the right build for
   your OS and CPU architecture.

## Installation

```text
/plugin marketplace add mariadb-corporation/ai-plugins
/plugin install dev@mariadb
```

On first use of a MariaDB tool, the launcher downloads `mariadb-shell` into your
user cache (`~/.cache/mariadb/mariadb-shell/<version>/` on macOS/Linux,
`%LOCALAPPDATA%\mariadb\mariadb-shell\<version>\` on Windows) and starts it as the
MCP server. Subsequent runs reuse the cached binary.

## The MCP server

Configured in [.mcp.json](.mcp.json):

```json
{
  "mcpServers": {
    "mariadb": {
      "command": "${CLAUDE_PLUGIN_ROOT}/scripts/mariadb-mcp-launcher.sh",
      "args": [],
      "env": { "MARIADB_SHELL_VERSION": "9.7.0" }
    }
  }
}
```

The launcher ([scripts/mariadb-mcp-launcher.sh](scripts/mariadb-mcp-launcher.sh)):

- Resolves the version from `MARIADB_SHELL_VERSION` (default `9.7.0`).
- Detects OS (`darwin`/`linux`/`windows`) and arch (`amd64`/`arm64`).
- Downloads the matching release asset from
  `github.com/mariadb-corporation/mariadb-shell/releases`, verifies its checksum,
  caches it, and execs it as the MCP server over stdio.

**Windows:** `.mcp.json` cannot branch per OS. The `.sh` launcher works on
macOS/Linux and under Git-Bash; native Windows users should point the `command`
at [scripts/mariadb-mcp-launcher.cmd](scripts/mariadb-mcp-launcher.cmd).

**Private releases:** while the `mariadb-shell` repo is private, set `GH_TOKEN`
so the launcher can authenticate to the GitHub release download.

## Skills

Skills are vendored under [skills/](skills/), preserving the upstream layer
layout. They are kept in sync across all plugins by the repo-wide updater
[scripts/sync-skills.sh](../../scripts/sync-skills.sh) — to refresh from upstream,
edit its pinned `REF` and run it from the repo root; per-plugin provenance is
recorded in [skills-source.json](skills-source.json).

```text
skills/
├── granular/
│   ├── statements/   create-table, alter-table, select, insert, update, delete,
│   │                 replace, create-view, create-index, drop-table,
│   │                 create-database, load-data
│   ├── functions/    json, string, date-time, numeric, aggregate
│   └── tools/        dump, import
└── topical/          features, query-optimization, system-versioned-tables,
                      mysql-to-mariadb, vector
                      (LICENSE + VENDORED.md — MIT attribution)
```

## License

GPL-2.0 — see [LICENSE](LICENSE). The five topical skills are vendored from
[MariaDB/skills](https://github.com/MariaDB/skills) under the MIT license; their
original license/attribution is preserved within their skill directories.
