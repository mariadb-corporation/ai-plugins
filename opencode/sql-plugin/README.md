# MariaDB SQL plugin for OpenCode

Version **26.7.0**

This plugin gives [OpenCode](https://opencode.ai) first-class MariaDB SQL support
through two parts:

1. **Skills** — MariaDB agent skills (SQL statements, functions, and topical
   deep-dives) vendored from
   [`mariadb-corporation/mariadb-docs/agent-skills`](https://github.com/mariadb-corporation/mariadb-docs/tree/main/agent-skills),
   baseline **MariaDB 11.8 LTS**. They follow the open `SKILL.md` standard, so
   OpenCode loads them contextually and you can invoke them via `/skills`.
2. **A native MCP server** — the [`mariadb-shell`](https://github.com/mariadb-corporation/mariadb-shell)
   binary, started automatically by a launcher that downloads the right build for
   your OS and CPU architecture.

## Installation

OpenCode has no central plugin marketplace; you wire the two parts into your
OpenCode config and skills directories. Clone this repo (or copy this
`sql-plugin/` directory) somewhere stable, then:

**1. Register the MCP server.** Merge the `mcp` block from this plugin's
[opencode.json](opencode.json) into your project `opencode.json` (or global
`~/.config/opencode/opencode.json`), and point `MARIADB_SQL_PLUGIN` at this
directory:

```sh
export MARIADB_SQL_PLUGIN=/path/to/ai-plugins/opencode/sql-plugin
```

**2. Make the skills discoverable.** OpenCode loads skills one directory deep from
`.opencode/skills/`, `~/.config/opencode/skills/`, `.claude/skills/`, and
`.agents/skills/`. Symlink (or copy) the flat `skills/` dir into one of those:

```sh
ln -s "$MARIADB_SQL_PLUGIN/skills" ~/.config/opencode/skills/mariadb
# …or per-project:
ln -s "$MARIADB_SQL_PLUGIN/skills" .opencode/skills/mariadb
```

On first use of a MariaDB tool, the launcher downloads `mariadb-shell` into your
user cache (`~/.cache/mariadb/mariadb-shell/<version>/` on macOS/Linux,
`%LOCALAPPDATA%\mariadb\mariadb-shell\<version>\` on Windows) and starts it as the
MCP server. Subsequent runs reuse the cached binary.

## The MCP server

Configured in [opencode.json](opencode.json):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "mariadb": {
      "type": "local",
      "command": ["{env:MARIADB_SQL_PLUGIN}/scripts/mariadb-mcp-launcher.sh"],
      "environment": { "MARIADB_SHELL_VERSION": "9.7.0" },
      "enabled": true
    }
  }
}
```

OpenCode substitutes `{env:MARIADB_SQL_PLUGIN}` from the environment (its documented
variable-substitution syntax), so the launcher resolves regardless of where OpenCode
is started.

The launcher ([scripts/mariadb-mcp-launcher.sh](scripts/mariadb-mcp-launcher.sh)):

- Resolves the version from `MARIADB_SHELL_VERSION` (default `9.7.0`).
- Detects OS (`darwin`/`linux`/`windows`) and arch (`amd64`/`arm64`).
- Downloads the matching release asset from
  `github.com/mariadb-corporation/mariadb-shell/releases`, verifies its checksum,
  caches it, and execs it as the MCP server over stdio.

**Windows:** the `.sh` launcher works on macOS/Linux and under Git-Bash; native
Windows users should point the `command` at
[scripts/mariadb-mcp-launcher.cmd](scripts/mariadb-mcp-launcher.cmd).

**Private releases:** while the `mariadb-shell` repo is private, set `GH_TOKEN`
so the launcher can authenticate to the GitHub release download.

## Skills

Skills are vendored under [skills/](skills/) in a **flat** layout — one directory
per skill, directly under `skills/` — because OpenCode discovers skills only one
directory deep. They are kept in sync across all plugins by the repo-wide updater
[scripts/sync-skills.sh](../../scripts/sync-skills.sh) (which flattens this target
automatically) — to refresh from upstream, run it from the repo root (it syncs
the latest upstream by default; pass a ref to sync a specific version); per-plugin
provenance is recorded in [skills-source.json](skills-source.json).

```text
skills/
├── statements   create-table, alter-table, select, insert, update, delete,
│                replace, create-view, create-index, drop-table,
│                create-database, load-data
├── functions    json, string, date-time, numeric, aggregate
└── topical      features, query-optimization, system-versioned-tables,
                 mysql-to-mariadb, vector
```

## License

Plugin code is **GPL-2.0** — see [LICENSE](LICENSE). The bundled skills are
vendored from several source repositories and retain their original licenses;
see [additional-skills/README.md](../../additional-skills/README.md) for the full list of sources and their
licensing.
