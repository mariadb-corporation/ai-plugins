---
description: >-
  Detailed discussions of the main features of MariaDB AI Plugins: sandbox
  instances, versioned schemas with Schema Management, REST endpoints with
  MariaDB REST Service, and migrating from MySQL.
---

# Features

This section discusses the main features of MariaDB AI Plugins in detail. Each page explains what the feature does and what it requires, names the skills the agent reads and the MCP tools it calls, and describes how the feature behaves, including its limitations.

For a quick overview of what you can ask an agent, see [Basic Usage](../basic-usage.md). For the arguments of each tool, see the [MCP Tool Reference](../mcp-tool-reference/).

## Feature Overview

| Feature | What it does | Plugins | Requires |
| --- | --- | --- | --- |
| [Sandbox Instances](sandbox-instances.md) | Deploys local, throwaway MariaDB Server instances. | `dev`, `sql` | The MCP server |
| [Versioned Schemas with Schema Management](versioned-schemas-with-schema-management.md) | Keeps a schema in a versioned project, and creates or upgrades it on any server. | `dev` | The MCP server |
| [REST Endpoints with MariaDB REST Service](rest-endpoints-with-mariadb-rest-service.md) | Defines REST endpoints for schema objects with SQL statements. | `dev` | The MCP server and a server connection |
| [Migrating from MySQL](migrating-from-mysql.md) | Assesses MySQL compatibility and migrates a MySQL database to MariaDB. | `dev`; compatibility guidance also in `sql` | The migration tooling, on Linux and macOS |

{% content-ref url="sandbox-instances.md" %}
[sandbox-instances.md](sandbox-instances.md)
{% endcontent-ref %}

{% content-ref url="versioned-schemas-with-schema-management.md" %}
[versioned-schemas-with-schema-management.md](versioned-schemas-with-schema-management.md)
{% endcontent-ref %}

{% content-ref url="rest-endpoints-with-mariadb-rest-service.md" %}
[rest-endpoints-with-mariadb-rest-service.md](rest-endpoints-with-mariadb-rest-service.md)
{% endcontent-ref %}

{% content-ref url="migrating-from-mysql.md" %}
[migrating-from-mysql.md](migrating-from-mysql.md)
{% endcontent-ref %}

{% hint style="info" %}
For step-by-step tutorials with example prompts, see the [MariaDB AI Plugins DevHub](https://ai-plugins.mariadb.org/tutorials/).
{% endhint %}
