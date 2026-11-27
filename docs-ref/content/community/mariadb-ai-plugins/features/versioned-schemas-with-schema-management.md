---
description: >-
  Manage a database schema as a versioned project with MariaDB Schema
  Management and the msm tools of the mariadb-shell MCP server.
---

# Versioned Schemas with Schema Management

<!--
  SYNCED: this page is maintained in mariadb-corporation/ai-plugins, under docs-ref/content/,
  and copied one way into mariadb-docs (tools/community/mariadb-ai-plugins/).
  Make every change in mariadb-corporation/ai-plugins. A change made in mariadb-docs or in the
  GitBook editor is overwritten by the next sync.
-->

MariaDB Schema Management (MSM) manages a database schema as a versioned project. A project contains a development script, a snapshot of each released version, an update script for each release, and generated deployment scripts. A deployment script creates the schema on a new server, or upgrades an existing schema to the version of the release.

## Requirements

* The `dev` plugin. The schema management skills aren't part of the `sql` plugin.
* The project directory on the [allowed-paths list](../configuring-the-mcp-server/README.md#allowed-paths).
* For deployment, a connection to the target server, or a [sandbox](sandbox-instances.md).

## Skills and Tools

| Skills | Tools |
| --- | --- |
| `mariadb-schema-management`, `mariadb-schema-management-create`, `mariadb-schema-management-develop`, `mariadb-schema-management-release`, `mariadb-schema-management-deploy` | [`msm.*`](../mcp-tool-reference/msm-tools.md), `db.connect` |

## Create a Project

Ask the agent to create a schema project. It calls `msm.create_project`, which creates a `<schema>.msm.project/` directory. To bring a schema that already exists on a server under version control, the agent lists its objects with `msm.list_live_schema_objects` and creates the project from them with `msm.import_live_schema`.

## Develop the Schema

The agent adds, replaces, and changes tables, sequences, views, routines, triggers, and events with `msm.set_schema_statements`, which takes their `CREATE` statements and puts each into the right section of the development script. It removes them with `msm.drop_schema_object`. Once the project has a release, both tools keep the `ALTER TABLE` and `DROP` statements that a deployed server needs for the next update script. A changed `CREATE TABLE` must be the complete definition of the table, and a renamed column is named in the `renames` argument so that its data is kept.

The agent writes MariaDB REST Service endpoints into section 180 with `msm.set_rest_statements` and removes them with `msm.drop_rest_object`. It adds a laid-out schema diagram with `msm.create_schema_diagram`, and keeps it current with `msm.layout_schema_diagram`.

The agent edits the other sections, such as base data and grants, one section at a time with `msm.get_section_sql_content` and `msm.set_section_sql_content`. See [Script Sections](../mcp-tool-reference/msm-tools.md#script-sections) for what belongs in each section.

## Release a Version

1. `msm.prepare_release` takes a snapshot of the development script and creates the update script, with the statements that `msm.set_schema_statements` and `msm.drop_schema_object` kept.
2. The agent completes the update script with the changes made by hand and the data backfills, in section 240, with the removed procedures and functions, in section 260, and with revoked privileges, in section 270. New and changed views, routines, roles, grants, and REST endpoints stay in the development script, because the deployment script runs them in full on every deployment.
3. `msm.generate_deployment_script` generates the deployment script.

{% hint style="danger" %}
Complete the update script before generating the deployment script. A script generated too early creates the schema correctly on an empty server but doesn't upgrade an existing installation correctly.
{% endhint %}

## Deploy a Version

`msm.deploy_schema` applies a version to a server through an open `db.connect` connection, optionally taking a backup first.

<sub>_This page is licensed: GPLv2_</sub>

{% @marketo/form formId="4316" %}
