---
description: >-
  How the components of MariaDB AI Plugins work together, how the launcher
  installs MariaDB Shell, and how the plugins are packaged for each harness.
---

# Architecture

A MariaDB AI Plugin consists of three components: the skills, the MCP server, and MariaDB Shell. This page describes how they work together, how MariaDB Shell is installed, and how the plugins are packaged for each harness.

## Components

| Part | What it is | Needs |
| --- | --- | --- |
| Skills | Markdown documents vendored into the plugin. The agent reads the ones whose description matches the request. | Nothing; they work offline on a fresh install. |
| MCP server | 28 tools that talk to MariaDB Server, in three groups: `db.*`, `msm.*`, and `sandbox.*`, plus the optional `migrator.*` group. | A one-time `mcp setup`, and a server to talk to. |
| MariaDB Shell | MariaDB's command-line shell. The MCP server runs inside it as a plugin. | Installed automatically on first use. |

## Why the MCP Server Runs Inside MariaDB Shell

MariaDB Shell provides database connections, a credential store that uses the secret storage of the operating system, sandbox deployment, and the schema management engine. The MCP server runs as a MariaDB Shell plugin so that it can use these functions. This has the following consequences:

* Passwords aren't stored in configuration files but in the MariaDB Shell secret store. The agent requests a connection and never sees the credentials.
* You can use the same MariaDB Shell installation as a SQL client.
* The MariaDB Shell configuration directory, `~/.mariadb-shell`, holds the shell's plugins, the secret store, and the MCP server's settings.

## The Launcher

Every plugin ships a launcher script, `mariadb-mcp-launcher.sh` and its Windows counterpart `mariadb-mcp-launcher.cmd`. The harness doesn't start MariaDB Shell directly but runs the launcher, which looks for a MariaDB Shell binary in the following order:

1. `$MARIADB_SHELL_BIN`, if set.
2. A `mariadb-shell` on the `PATH` that meets the minimum version.
3. A local install at `$MARIADB_SHELL_BINDIR/mariadb-shell`. The default is `~/.local/bin`, or `%LOCALAPPDATA%\Programs\mariadb-shell\bin\` on Windows.
4. If none of these is found, the launcher downloads and runs the official MariaDB Shell installer, `install.sh` or `install.ps1`, and uses the installed binary.

The launcher then starts the binary as `mariadb-shell -- mcp start-server --transport=stdio`.

{% hint style="info" %}
`MARIADB_SHELL_VERSION` specifies the minimum version. If an installed binary meets this version, the launcher uses it and doesn't access the network. The launcher downloads MariaDB Shell only if no installed binary meets the minimum version. To upgrade MariaDB Shell, raise the minimum version, remove the installation that the launcher manages, or run the installer yourself.
{% endhint %}

The launcher writes all of its messages to standard error, because standard output carries the MCP protocol.

See [Configuration Reference](configuration-reference.md) for all launcher environment variables.

## How the Harnesses Differ

All harnesses get the same skills and the same MCP server, but the plugins are packaged differently:

* **Claude Code** and **Codex** read a marketplace manifest and install a plugin directory.
* **OpenCode** has no marketplace. You merge an `mcp` block into your configuration, set an environment variable, and link the skills directory.
* **Pi** has neither a marketplace nor built-in MCP support. The repository-root `package.json` is the Pi package manifest, and MCP support comes from the separately installed `pi-mcp-adapter` package.

## Vendored Skills

The skills are copied into each plugin when a release is built, rather than downloaded at run time. Each plugin release therefore contains a fixed version of the skills, tested with that release. Changes in the source repositories don't affect installed plugins until the next release. The skills come from the MariaDB documentation repository, the MariaDB Shell repository, and the MariaDB AI Plugins repository.
