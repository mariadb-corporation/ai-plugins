---
description: >-
  Install MariaDB AI Plugins into Claude Code, Codex, OpenCode, or Pi. On first
  start, the plugin installs MariaDB Shell if no suitable version is present.
---

# Installation

MariaDB AI Plugins use the standard plugin system of each harness where one exists. Installation has two steps:

1. Install the plugin into your harness, using the page for your harness below.
2. Configure what the MCP server may access. This step is the same for every harness; see [Configuring the MCP Server](../configuring-the-mcp-server.md).

The skills work after step 1. The MCP server refuses every request until step 2 is done.

{% hint style="info" %}
On first start, the plugin downloads and extracts the MariaDB Shell package, unless a suitable version is already installed. Depending on your network connection, this can take a minute. It happens only once.
{% endhint %}

## Prerequisites

* A supported harness: Claude Code, Codex, OpenCode, or Pi.
* Linux, macOS, or Windows. The optional migration tooling is available on Linux and macOS only.
* Network access on first start, unless MariaDB Shell 26.9.5 or later is already installed.

MariaDB Server doesn't need to be installed. The MCP server can deploy local [sandbox instances](../features/sandbox-instances.md).

## Choose Your Harness

{% content-ref url="claude-code.md" %}
[claude-code.md](claude-code.md)
{% endcontent-ref %}

{% content-ref url="codex.md" %}
[codex.md](codex.md)
{% endcontent-ref %}

{% content-ref url="opencode.md" %}
[opencode.md](opencode.md)
{% endcontent-ref %}

{% content-ref url="pi.md" %}
[pi.md](pi.md)
{% endcontent-ref %}

## Verify the Skills Are Loaded

Ask the agent for something only a skill knows, for example:

```
Write a CREATE TABLE for a product catalog, MariaDB style.
```

If the answer uses the native `UUID` data type with `UUID_v7()` rather than `CHAR(36)`, the skills are loaded.
