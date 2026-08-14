# MariaDB SQL plugin for Codex

Version **26.8.0**

This plugin gives [OpenAI Codex](https://developers.openai.com/codex/) first-class
MariaDB SQL support through two parts:

1. **Skills** — MariaDB agent skills (SQL statements, functions, and topical
   deep-dives) vendored from
   [`mariadb-corporation/mariadb-docs/agent-skills`](https://github.com/mariadb-corporation/mariadb-docs/tree/main/agent-skills),
   baseline **MariaDB 11.8 LTS**. They follow the open
   [agent-skills](https://developers.openai.com/codex/skills) standard (`SKILL.md`),
   so Codex loads them contextually and can invoke them via `/skills` or `$`.
2. **A native MCP server** — the [`mariadb-shell`](https://github.com/mariadb-corporation/mariadb-shell)
   binary, started automatically by a launcher that finds a suitable install or,
   failing that, runs the shell's own installer to get one.

## Installation

```text
/plugin marketplace add mariadb/ai-plugins
/plugin install sql@mariadb
```

Then register the MCP server — installing the plugin gives Codex the skills, but
Codex 0.147 cannot start a server a plugin declares (see below), so this step is
required:

```sh
codex/sql-plugin/scripts/setup-codex-mcp.sh     # --remove to unregister
```

Then reload (`/reload-plugins`) if Codex doesn't pick it up automatically. On first
use of a MariaDB tool, the launcher looks for a `mariadb-shell` it can run —
`$MARIADB_SHELL_BIN`, one on `PATH`, or an existing install in `~/.local/bin`
(`%LOCALAPPDATA%\Programs\mariadb-shell\bin` on Windows) — and otherwise installs
the newest release there with the shell's own installer. Then it starts that
binary as the MCP server. Later runs reuse the install.

## The MCP server

Declared in [.mcp.json](.mcp.json):

```json
{
  "mcpServers": {
    "mariadb": {
      "command": "${CLAUDE_PLUGIN_ROOT}/scripts/mariadb-mcp-launcher.sh",
      "args": [],
      "env": { "MARIADB_SHELL_VERSION": "26.8.0" }
    }
  }
}
```

The key is `mcpServers` (camelCase) because that is the only one Codex reads — a
`mcp_servers` key registers nothing at all — and `${CLAUDE_PLUGIN_ROOT}` because
that is the only placeholder name Codex knows.

**Codex 0.147 still cannot start this server, which is why the installation above
has a second step.** Codex stores the `command` verbatim and expands nothing when
it spawns the process, so the placeholder — which a plugin has no way to avoid, as
it cannot know the content-addressed directory Codex will install it into — is
exec'd literally and the first tool call fails with `MCP startup failed: No such
file or directory`. [scripts/setup-codex-mcp.sh](scripts/setup-codex-mcp.sh) works
around that with `codex mcp add`, writing an `[mcp_servers.mariadb]` entry into
`$CODEX_HOME/config.toml` with the absolute path resolved on your machine; that
entry takes precedence over the plugin's. The declaration above is kept so the
plugin works unchanged once Codex expands it.

The launcher ([scripts/mariadb-mcp-launcher.sh](scripts/mariadb-mcp-launcher.sh)):

- Resolves the minimum version from `MARIADB_SHELL_VERSION` (default `26.8.0`).
- Runs the first `mariadb-shell` that meets it: `$MARIADB_SHELL_BIN`, then one on
  `PATH`, then a local install at `~/.local/bin/mariadb-shell`
  (`%LOCALAPPDATA%\Programs\mariadb-shell\bin\mariadb-shell.cmd` on Windows).
- Failing all three, runs the shell's own installer — `install.sh`, or
  `install.ps1` on Windows, fetched from
  `raw.githubusercontent.com/mariadb-corporation/mariadb-shell/main/`. It picks
  the package matching this OS, CPU and glibc version, verifies it against the
  release's `SHA256SUMS`, unpacks it under `~/.local/share/mariadb-shell/` and
  links the binary into `~/.local/bin`. Later starts reuse that install.
- Execs whichever binary it settled on as
  `mariadb-shell -- mcp start-server --transport=stdio`. stdout belongs to the
  MCP transport alone, so the launcher's own messages — and the installer's — go
  to stderr.

**Windows:** `.mcp.json` cannot branch per OS. The `.sh` launcher works on
macOS/Linux and under Git-Bash; native Windows users should point the `command`
at [scripts/mariadb-mcp-launcher.cmd](scripts/mariadb-mcp-launcher.cmd).

**Private repository:** while `mariadb-shell` is private, set `GH_TOKEN` (or
`MARIADB_SHELL_TOKEN`, or simply run `gh auth login`). The token is needed twice:
to fetch the installer, and for the installer to download the release.

**Prereleases:** the installer skips prereleases, as `releases/latest` does. Set
`MARIADB_SHELL_PRERELEASE=1` to let it pick one — necessary until a stable
`mariadb-shell` release is published.

### Configure what the server may access

The skills work on their own. The MCP server, however, starts out allowed to reach
nothing — installing this plugin wires it up, but does not tell it what it may
touch. Run this once per machine:

```sh
mariadb-shell -- mcp setup     # or mcp.setup() from an interactive shell
```

If `mariadb-shell` isn't on your `PATH`, use the copy the launcher installed —
`~/.local/bin/mariadb-shell`, or
`%LOCALAPPDATA%\Programs\mariadb-shell\bin\mariadb-shell.cmd` on Windows. The
installer only prints a `PATH` hint; it never edits your shell profile. That copy
appears the first time this plugin starts the MCP server, so either let the agent
run once first, or install the shell yourself before configuring it.

## Skills

Skills are vendored under [skills/](skills/), preserving the upstream layer
layout. They are kept in sync across all plugins by the repo-wide updater
[scripts/sync-skills.sh](../../scripts/sync-skills.sh) — to refresh from upstream,
run it from the repo root (it syncs the latest upstream by default; pass a ref to
sync a specific version); per-plugin provenance is recorded in
[skills-source.json](skills-source.json).

```text
skills/
├── granular/
│   ├── statements/   create-table, alter-table, select, insert, update, delete,
│   │                 replace, create-view, create-index, drop-table,
│   │                 create-database, load-data
│   └── functions/    json, string, date-time, numeric, aggregate
└── topical/          features, query-optimization, system-versioned-tables,
                      mysql-to-mariadb, vector
```

## License

Plugin code is **GPL-2.0** — see [LICENSE](LICENSE). The bundled skills are
vendored from several source repositories and retain their original licenses;
see [additional-skills/README.md](../../additional-skills/README.md) for the full list of sources and their
licensing.
