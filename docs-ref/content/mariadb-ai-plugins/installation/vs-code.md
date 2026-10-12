---
description: >-
  Use the MariaDB AI Plugins with GitHub Copilot in VS Code through the MariaDB
  extension for VS Code, which contributes the skills and the MCP server.
---

# VS Code

In VS Code, the MariaDB AI Plugins are part of the MariaDB extension for VS Code. The extension contributes the skills of the `dev` plugin to GitHub Copilot and registers the `mariadb-shell` MCP server with VS Code. There are no configuration files to edit. Only the `dev` plugin is available for VS Code.

## Prerequisites

* VS Code 1.138 or later.
* GitHub Copilot, with agent mode for the MCP server.

## Install the Extension

Install the MariaDB extension, `MariaDB.mariadb-dev`, from the Extensions view of VS Code, or from the command line:

```bash
code --install-extension MariaDB.mariadb-dev
```

The skills are available to Copilot as soon as the extension is installed. The MCP server is listed in VS Code as **MariaDB**. To see it, run this command from the Command Palette:

```text
MCP: List Servers
```

{% hint style="info" %}
The first time Copilot starts the MCP server, the extension downloads and installs MariaDB Shell, unless a suitable version is already installed. A notification shows the progress. The extension's own views use the same installation.
{% endhint %}

## Skills and Releases

Each release of the extension contains the skills of the newest MariaDB AI Plugins release at the time the extension was built. A new MariaDB AI Plugins release therefore reaches VS Code with the next release of the extension.

## Turn the Plugin Off

The `mariadb.copilot.enabled` setting controls both the skills and the MCP server. It is on by default. When you turn it off, Copilot no longer sees the skills, and VS Code no longer lists the MCP server. The rest of the extension is not affected.

## Configure the MCP Server

Before the agent can use the MCP server, you must configure the connections and directories it may access. In VS Code, you can allow a connection from the extension's **Connections** view: edit the connection and select **Allow MCP access to this connection**. Connections with MCP access show `MCP` in the view. You can also use the same setup as for every other harness; see [Configuring the MCP Server](../configuring-the-mcp-server/README.md).
