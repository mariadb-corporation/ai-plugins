---
description: >-
  MariaDB AI Plugins add MariaDB agent skills and the native mariadb-shell MCP
  server to the Claude Code, Codex, OpenCode, and Pi AI coding agents.
icon: robot
---

# MariaDB AI Plugins

## MariaDB AI Plugins

MariaDB AI Plugins give AI coding agents first-class MariaDB support. Installing a plugin gives the agent MariaDB reference material in the form of skills, and a live connection to MariaDB Server through the native `mariadb-shell` MCP server.

{% hint style="info" %}
The skills work as soon as a plugin is installed, without a database or any configuration. The MCP server needs a one-time setup; see [Configuring the MCP Server](configuring-the-mcp-server.md).
{% endhint %}

{% columns %}
{% column %}
{% content-ref url="about-mariadb-ai-plugins.md" %}
[about-mariadb-ai-plugins.md](about-mariadb-ai-plugins.md)
{% endcontent-ref %}
{% endcolumn %}

{% column %}
Overview of MariaDB AI Plugins: agent skills for MariaDB, the `mariadb-shell` MCP server, and MariaDB Shell, packaged for Claude Code, Codex, OpenCode, and Pi.
{% endcolumn %}
{% endcolumns %}

{% columns %}
{% column %}
{% content-ref url="installation/" %}
[installation](installation/)
{% endcontent-ref %}
{% endcolumn %}

{% column %}
Install a plugin into Claude Code, Codex, OpenCode, or Pi. On first start, the plugin installs MariaDB Shell if no suitable version is present.
{% endcolumn %}
{% endcolumns %}

{% columns %}
{% column %}
{% content-ref url="configuring-the-mcp-server.md" %}
[configuring-the-mcp-server.md](configuring-the-mcp-server.md)
{% endcontent-ref %}
{% endcolumn %}

{% column %}
Run `mcp setup` once per machine to choose the connections and local paths the MCP server may use, and optionally install the migration tooling.
{% endcolumn %}
{% endcolumns %}

{% columns %}
{% column %}
{% content-ref url="basic-usage.md" %}
[basic-usage.md](basic-usage.md)
{% endcontent-ref %}
{% endcolumn %}

{% column %}
What you can ask an agent for with skills alone, with the MCP server connected to your database, and with a throwaway sandbox instance.
{% endcolumn %}
{% endcolumns %}

{% columns %}
{% column %}
{% content-ref url="plugin-variants.md" %}
[plugin-variants.md](plugin-variants.md)
{% endcontent-ref %}
{% endcolumn %}

{% column %}
The `dev`, `sql`, and `contributor` plugin variants: which skills each one ships and which ones include the MCP server.
{% endcolumn %}
{% endcolumns %}

{% columns %}
{% column %}
{% content-ref url="features/" %}
[features](features/)
{% endcontent-ref %}
{% endcolumn %}

{% column %}
Detailed discussions of the plugins' main features: sandbox instances, versioned schemas with Schema Management, REST endpoints with MariaDB REST Service, and migrating from MySQL.
{% endcolumn %}
{% endcolumns %}

{% columns %}
{% column %}
{% content-ref url="architecture.md" %}
[architecture.md](architecture.md)
{% endcontent-ref %}
{% endcolumn %}

{% column %}
How skills, the MCP server, and MariaDB Shell fit together, how the launcher resolves and installs MariaDB Shell, and how each harness packages a plugin.
{% endcolumn %}
{% endcolumns %}

{% columns %}
{% column %}
{% content-ref url="security-model.md" %}
[security-model.md](security-model.md)
{% endcontent-ref %}
{% endcolumn %}

{% column %}
The two allow-lists that bound what an agent can reach: configured connections and allowed paths, plus the account privileges you choose.
{% endcolumn %}
{% endcolumns %}

{% columns %}
{% column %}
{% content-ref url="skills-reference/" %}
[skills-reference](skills-reference/)
{% endcontent-ref %}
{% endcolumn %}

{% column %}
Reference for every skill the plugins ship: SQL statements, built-in functions, command-line tools, connectors, topical guides, and the repository's own skills.
{% endcolumn %}
{% endcolumns %}

{% columns %}
{% column %}
{% content-ref url="mcp-tool-reference/" %}
[mcp-tool-reference](mcp-tool-reference/)
{% endcontent-ref %}
{% endcolumn %}

{% column %}
Reference for the tools of the `mariadb-shell` MCP server: `db.*`, `msm.*`, `sandbox.*`, and the optional `migrator.*` group.
{% endcolumn %}
{% endcolumns %}

{% columns %}
{% column %}
{% content-ref url="configuration-reference.md" %}
[configuration-reference.md](configuration-reference.md)
{% endcontent-ref %}
{% endcolumn %}

{% column %}
Environment variables, file locations, and configuration files used by the plugins, the launcher, and the MCP server.
{% endcolumn %}
{% endcolumns %}

{% columns %}
{% column %}
{% content-ref url="troubleshooting.md" %}
[troubleshooting.md](troubleshooting.md)
{% endcontent-ref %}
{% endcolumn %}

{% column %}
Common error messages and symptoms, what causes them, and how to fix them.
{% endcolumn %}
{% endcolumns %}

{% columns %}
{% column %}
{% content-ref url="release-notes.md" %}
[release-notes.md](release-notes.md)
{% endcontent-ref %}
{% endcolumn %}

{% column %}
Where to find the changes in each MariaDB AI Plugins release, and how plugin versions relate to MariaDB Shell versions.
{% endcolumn %}
{% endcolumns %}

{% columns %}
{% column %}
{% content-ref url="license.md" %}
[license.md](license.md)
{% endcontent-ref %}
{% endcolumn %}

{% column %}
MariaDB AI Plugins are licensed under the GNU GPL v2; the bundled skills keep the licenses of their source repositories.
{% endcolumn %}
{% endcolumns %}

{% columns %}
{% column %}
{% content-ref url="bug-reports.md" %}
[bug-reports.md](bug-reports.md)
{% endcontent-ref %}
{% endcolumn %}

{% column %}
Report bugs and request features on GitHub, and report security vulnerabilities privately.
{% endcolumn %}
{% endcolumns %}
