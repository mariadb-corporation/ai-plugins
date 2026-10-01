---
description: >-
  Install the MariaDB AI Plugins into Codex from the MariaDB plugin
  marketplace.
---

# Codex

## Install the Plugin

Add the MariaDB marketplace and install the `dev` plugin with the Codex CLI:

```bash
codex plugin marketplace add mariadb/ai-plugins
codex plugin add dev@mariadb
```

To install a different variant, replace `dev` with `sql` or `contributor`. See [Plugin Variants](../plugin-variants.md).

Codex's `/plugins` command browses and enables plugins interactively. It takes no arguments, so add the marketplace with the CLI.

## Configure the MCP Server

The plugin declares its MCP server in a form Codex starts directly, so no separate registration is needed. Before the agent can use the server, choose the connections and paths it may access. See [Configuring the MCP Server](../configuring-the-mcp-server.md).

## Register the MCP Server Manually

If the MCP server doesn't start, register it explicitly with the script shipped in the plugin:

{% tabs %}
{% tab title="Linux and macOS" %}
```bash
codex/dev-plugin/scripts/setup-codex-mcp.sh
```

To unregister the server, add `--remove`.
{% endtab %}

{% tab title="Windows" %}
```
codex\dev-plugin\scripts\setup-codex-mcp.cmd
```

To unregister the server, add `--remove`.
{% endtab %}
{% endtabs %}

## Verify the Installation

Run `/plugins` in Codex to check that the plugin is enabled.
