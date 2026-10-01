---
description: >-
  Overview of MariaDB AI Plugins: agent skills for MariaDB, the mariadb-shell
  MCP server, and MariaDB Shell, packaged for Claude Code, Codex, OpenCode, and
  Pi.
---

# About MariaDB AI Plugins

MariaDB AI Plugins package MariaDB support for AI coding agents. A plugin installs into the agent's own plugin system, which the documentation calls the *harness*, and gives the agent three things.

## What a Plugin Provides

| Part | What it is | What it needs |
| --- | --- | --- |
| Skills | MariaDB reference material the agent reads when it becomes relevant: how `ALTER TABLE` behaves in MariaDB, how vector indexes work, which connector to use from Python or Java, or how to move an application from MySQL to MariaDB. | Nothing. Skills work on a fresh install, offline. |
| MCP server | A live connection to MariaDB Server, so the agent can read your schema, run queries, analyze a slow query with `EXPLAIN`, or start a throwaway test instance. | A one-time `mcp setup`, and a server to connect to. |
| MariaDB Shell | MariaDB's command-line shell, a port of MySQL Shell. The MCP server runs inside it as a plugin. You can also use it as a SQL client. | Installed automatically the first time an agent starts the MCP server. |

{% hint style="info" %}
The Model Context Protocol (MCP) is a standard interface that lets AI agents call tools. Here, the tools are the ones that talk to MariaDB. You don't need to understand the protocol to use the plugins.
{% endhint %}

## Supported Harnesses

| Harness | Plugin variants | Installation |
| --- | --- | --- |
| [Claude Code](https://claude.com/claude-code) | `dev`, `sql`, `contributor` | Plugin marketplace |
| [Codex](https://openai.com/codex) | `dev`, `sql`, `contributor` | Plugin marketplace |
| [OpenCode](https://opencode.ai) | `dev`, `sql`, `contributor` | Manual configuration |
| [Pi](https://pi.dev) | `dev` | Pi package |

See [Plugin Variants](plugin-variants.md) for what each variant contains.

## MariaDB Version Baseline

The skills are written and verified against MariaDB 11.8 LTS.

## Plugin and MariaDB Shell Versions

Plugin releases follow the MariaDB Shell release they require. A plugin at version 26.9.5 requires MariaDB Shell 26.9.5 or later, and installs the newest MariaDB Shell release when no suitable version is installed. See [Release Notes](release-notes.md).

## Next Steps

{% content-ref url="installation/" %}
[installation](installation/)
{% endcontent-ref %}
