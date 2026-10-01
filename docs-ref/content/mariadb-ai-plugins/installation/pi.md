---
description: >-
  Install the MariaDB AI Plugins into Pi as a Pi package, with the
  pi-mcp-adapter extension for MCP support.
---

# Pi

Pi has no plugin marketplace and no built-in MCP support. The MariaDB AI Plugins repository is itself a Pi package, and MCP support comes from the community [`pi-mcp-adapter`](https://pi.dev/packages/pi-mcp-adapter) extension, which you install alongside it. Pi ships the `dev` plugin only.

## Install the MCP Adapter

Install the adapter once, if you don't have it yet:

```bash
pi install npm:pi-mcp-adapter
```

## Install the Plugin

Install the plugin from GitHub:

```bash
pi install git:github.com/mariadb/ai-plugins
```

Alternatively, from a local checkout of the repository, run this at the repository root:

```bash
pi install .
```

Restart Pi, or run `/reload`, to load the skills and the extension.

## Register the MCP Server

Register the MariaDB MCP server with the adapter from inside Pi:

```
/mariadb-mcp-setup
```

This writes the global `~/.config/mcp/mcp.json`. To register the server for the current project only, in `./.mcp.json`, add `--project`.

Then run `/mcp reconnect mariadb`, or restart Pi. While the server isn't registered, the extension prints a reminder at the start of each session.

## Configure the MCP Server

Registering the server with Pi and configuring what it may access are separate steps. See [Configuring the MCP Server](../configuring-the-mcp-server.md).

{% hint style="warning" %}
A project-local Pi package must be approved at run time with `--approve`. Without it, the package is configured but never loaded.
{% endhint %}
