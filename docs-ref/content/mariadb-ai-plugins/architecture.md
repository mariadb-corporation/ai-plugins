---
description: >-
  How the skills, the mariadb-shell MCP server, and MariaDB Shell fit
  together, how the launcher resolves and installs MariaDB Shell, and how each
  harness packages a plugin.
---

# Architecture

A MariaDB AI Plugin consists of three separate parts. Knowing which part does what explains most of what happens when something doesn't work.

## Components

| Part | What it is | Needs |
| --- | --- | --- |
| Skills | Markdown documents vendored into the plugin. The agent reads the ones whose description matches the request. | Nothing; they work offline on a fresh install. |
| MCP server | 28 tools that talk to MariaDB Server, in three groups: `db.*`, `msm.*`, and `sandbox.*`, plus the optional `migrator.*` group. | A one-time `mcp setup`, and a server to talk to. |
| MariaDB Shell | MariaDB's command-line shell. The MCP server runs inside it as a plugin. | Installed automatically on first use. |

## Why the MCP Server Runs Inside MariaDB Shell

MariaDB Shell already provides high-performance database connections, a credential store backed by the platform's secret storage, sandbox deployment, and the schema management engine. Running the MCP server as a MariaDB Shell plugin reuses all of them. As a result:

* Passwords never appear in a configuration file. They live in MariaDB Shell's secret store, and the agent asks for a connection, not for credentials.
* MariaDB Shell is also available to you as a SQL client.
* The MariaDB Shell configuration directory, `~/.mariadb-shell`, holds the shell's plugins, the secret store, and the MCP server's settings.

## The Launcher

Every plugin ships a launcher script, `mariadb-mcp-launcher.sh` and its Windows counterpart `mariadb-mcp-launcher.cmd`. The harness starts the launcher, not MariaDB Shell. The launcher resolves a MariaDB Shell binary in this order:

1. `$MARIADB_SHELL_BIN`, if set.
2. A `mariadb-shell` on the `PATH` that meets the minimum version.
3. A local install at `$MARIADB_SHELL_BINDIR/mariadb-shell`. The default is `~/.local/bin`, or `%LOCALAPPDATA%\Programs\mariadb-shell\bin\` on Windows.
4. Otherwise, it downloads and runs the official MariaDB Shell installer, `install.sh` or `install.ps1`, and starts what it installed.

It then starts the binary as `mariadb-shell -- mcp start-server --transport=stdio`.

{% hint style="info" %}
`MARIADB_SHELL_VERSION` is a minimum, not a target. If a binary on disk meets it, the launcher starts that binary without any network access. A download happens only when nothing on disk meets the minimum. To upgrade, raise the minimum, remove the managed install, or run the installer yourself.
{% endhint %}

The launcher writes all of its messages to standard error, because standard output carries the MCP protocol.

See [Configuration Reference](configuration-reference.md) for all launcher environment variables.

## How the Harnesses Differ

The content is identical across harnesses; the packaging differs.

* **Claude Code** and **Codex** read a marketplace manifest and install a plugin directory.
* **OpenCode** has no marketplace. You merge an `mcp` block into your configuration, set an environment variable, and link the skills directory.
* **Pi** has neither a marketplace nor built-in MCP support. The repository-root `package.json` is the Pi package manifest, and MCP support comes from the separately installed `pi-mcp-adapter` package.

## Vendored Skills

The skills are copied into each plugin at release time rather than fetched at run time. A plugin release therefore pins the skill versions: what was tested is what ships, and an upstream edit never changes an agent's behavior mid-session. The skills come from the MariaDB documentation repository, the MariaDB Shell repository, and the MariaDB AI Plugins repository itself.
