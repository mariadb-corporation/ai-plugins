---
description: >-
  Reference for the tools of the mariadb-shell MCP server: db, msm, and
  sandbox, and the optional migrator group.
---

# MCP Tool Reference

The `mariadb-shell` MCP server exposes 28 tools in three groups, plus an optional fourth group that appears only when the migration tooling is installed.

| Group | Tools | What they do |
| --- | --- | --- |
| [`db.*`](db-tools.md) | 8 | List connections and schemas, describe objects, and run SQL. |
| [`msm.*`](msm-tools.md) | 12 | Versioned schema projects, releases, and deployments with MariaDB Schema Management. |
| [`sandbox.*`](sandbox-tools.md) | 8 | List deployable server versions; deploy, start, stop, and delete local instances. |
| [`migrator.*`](migrator-tools.md) | 4 | MySQL-to-MariaDB migration. Optional, and not counted in the 28. |

## Conventions

* Arguments are named as the tools take them.
* `connection_id` always comes from a prior `db.connect` call.
* Any argument that takes a file path is limited to the allowed-paths list. See [Security Model](../security-model.md#paths).

{% content-ref url="db-tools.md" %}
[db-tools.md](db-tools.md)
{% endcontent-ref %}

{% content-ref url="msm-tools.md" %}
[msm-tools.md](msm-tools.md)
{% endcontent-ref %}

{% content-ref url="sandbox-tools.md" %}
[sandbox-tools.md](sandbox-tools.md)
{% endcontent-ref %}

{% content-ref url="migrator-tools.md" %}
[migrator-tools.md](migrator-tools.md)
{% endcontent-ref %}
