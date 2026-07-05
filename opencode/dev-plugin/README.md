# MariaDB plugin for OpenCode

Version **0.0.2**

This plugin gives [OpenCode](https://opencode.ai) first-class MariaDB support
through two parts:

1. **Skills** — 24 MariaDB agent skills (SQL statements, functions, client tools,
   and topical deep-dives) vendored from
   [`mariadb-corporation/mariadb-docs/agent-skills`](https://github.com/mariadb-corporation/mariadb-docs/tree/main/agent-skills),
   baseline **MariaDB 11.8 LTS**. They follow the open `SKILL.md` standard, so
   OpenCode loads them contextually and you can invoke them via `/skills`.
2. **A native MCP server** — the [`mariadb-shell`](https://github.com/mariadb-corporation/mariadb-shell)
   binary, started automatically by a launcher that downloads the right build for
   your OS and CPU architecture.

## Installation

OpenCode has no central plugin marketplace; you wire the two parts into your
OpenCode config and skills directories. Clone this repo (or copy this
`dev-plugin/` directory) somewhere stable, then:

**1. Register the MCP server.** Merge the `mcp` block from this plugin's
[opencode.json](opencode.json) into your project `opencode.json` (or global
`~/.config/opencode/opencode.json`), and point `MARIADB_DEV_PLUGIN` at this
directory:

```sh
export MARIADB_DEV_PLUGIN=/path/to/ai-plugins/opencode/dev-plugin
```

**2. Make the skills discoverable.** OpenCode loads skills one directory deep from
`.opencode/skills/`, `~/.config/opencode/skills/`, `.claude/skills/`, and
`.agents/skills/`. Symlink (or copy) the flat `skills/` dir into one of those:

```sh
ln -s "$MARIADB_DEV_PLUGIN/skills" ~/.config/opencode/skills/mariadb
# …or per-project:
ln -s "$MARIADB_DEV_PLUGIN/skills" .opencode/skills/mariadb
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
      "command": ["{env:MARIADB_DEV_PLUGIN}/scripts/mariadb-mcp-launcher.sh", "mcp"],
      "environment": { "MARIADB_SHELL_VERSION": "2026.7.0" },
      "enabled": true
    }
  }
}
```

OpenCode substitutes `{env:MARIADB_DEV_PLUGIN}` from the environment (its documented
variable-substitution syntax), so the launcher resolves regardless of where OpenCode
is started.

The launcher ([scripts/mariadb-mcp-launcher.sh](scripts/mariadb-mcp-launcher.sh)):

- Resolves the version from `MARIADB_SHELL_VERSION` (default `2026.7.0`).
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
automatically) — to refresh from upstream, edit its pinned `REF` and run it from
the repo root; per-plugin provenance is recorded in
[skills-source.json](skills-source.json).

```text
skills/
├── statements   create-table, alter-table, select, insert, update, delete,
│                replace, create-view, create-index, drop-table,
│                create-database, load-data                      (12)
├── functions    json, string, date-time, numeric, aggregate      (5)
├── tools        dump, import                                      (2)
├── topical      features, query-optimization, system-versioned-tables,
│                mysql-to-mariadb, vector                          (5)
└── topical/     LICENSE + VENDORED.md (MIT attribution; not a skill)
```

## License

GPL-2.0 — see [LICENSE](LICENSE). The five topical skills are vendored from
[MariaDB/skills](https://github.com/MariaDB/skills) under the MIT license; their
original license/attribution is preserved in [skills/topical/](skills/topical/).
