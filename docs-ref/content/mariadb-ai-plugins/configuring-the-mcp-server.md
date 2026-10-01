---
description: >-
  Run mcp setup once per machine to choose the connections and local paths the
  mariadb-shell MCP server may use, and optionally install the migration
  tooling.
---

# Configuring the MCP Server

The MCP server starts out allowed to reach nothing. Installing a plugin registers the server with your harness, but doesn't tell it which databases and directories it may use. Configure that once per machine, for all harnesses, with MariaDB Shell:

```bash
mariadb-shell -- mcp setup
```

From an interactive MariaDB Shell session, run `mcp.setup()` instead.

{% hint style="info" %}
The MCP server is built as a MariaDB Shell plugin to use the shell's high-performance database connections, credential management, sandbox handling, and schema management.
{% endhint %}

## Locate MariaDB Shell

If `mariadb-shell` isn't on your `PATH`, use the copy the plugin's launcher installed:

{% tabs %}
{% tab title="Linux and macOS" %}
```bash
~/.local/bin/mariadb-shell -- mcp setup
```
{% endtab %}

{% tab title="Windows" %}
```
%LOCALAPPDATA%\Programs\mariadb-shell\bin\mariadb-shell.cmd -- mcp setup
```
{% endtab %}
{% endtabs %}

The installer prints a `PATH` hint but never edits your shell profile. The copy appears the first time a plugin starts the MCP server, so either let the agent start once first, or install MariaDB Shell yourself before configuring it.

## What the Setup Configures

### Connections

The database connection URIs the agent may connect to. For each one, the setup prompts for the password, verifies it, and stores it in MariaDB Shell's secret store, separately from your regular MariaDB Shell connections. Passwords never appear in a file the agent can read.

{% hint style="warning" %}
Give each connection a dedicated MariaDB account with only the privileges it needs, such as read-only access to specific schemas. The MCP server enforces which servers the agent can reach; the account's privileges decide what it can do there. See [Security Model](security-model.md).
{% endhint %}

### Allowed Paths

The local directories the MCP server may read from and write to. The setup suggests the current directory, shown as a full path. Every tool that touches a file is limited to these directories.

### Migration Tooling

Optional, on Linux and macOS only. Downloads the [MySQL-to-MariaDB migration tooling](https://github.com/mariadb-corporation/Mysql-to-MariaDB-Migration) and extracts it into `~/.local/share/mariadb-migrator/<version>`. The first-run walkthrough doesn't offer it; run the setup again and choose it from the menu, or run:

```bash
mariadb-shell -- mcp setup --installMigrator
```

Restart the MCP server afterward. The `migrator.*` tools appear on the next server start. See [migrator Tools](mcp-tool-reference/migrator-tools.md).

## Change the Configuration

Run `mariadb-shell -- mcp setup` again at any time to add or remove connections and paths. For the complete option reference, see the [MCP server documentation](https://github.com/mariadb-corporation/mariadb-shell-plugins/blob/main/mcp_plugin/README.md#configuration-mcpsetup).
