---
description: >-
  Reference for the msm tools of the mariadb-shell MCP server, which manage versioned schema projects, releases, and deployments with MariaDB Schema Management.
---

# msm Tools

<!--
  SYNCED: this page is maintained in mariadb-corporation/ai-plugins, under docs-ref/content/,
  and copied one way into mariadb-docs (tools/community/mariadb-ai-plugins/).
  Make every change in mariadb-corporation/ai-plugins. A change made in mariadb-docs or in the
  GitBook editor is overwritten by the next sync.
-->

The `msm.*` tools manage database schemas with MariaDB Schema Management (MSM). With these tools, the agent creates, imports, and edits versioned schema projects, prepares releases, and generates and deploys the scripts that create or upgrade a schema. See [Versioned Schemas with Schema Management](../features/versioned-schemas-with-schema-management.md) for the workflow.

## Overview

The MCP server serves the following 26 `msm.*` tools. The last three need a connection, so the server offers them only when it also serves the `db.*` group.

| Tool | Description |
| --- | --- |
| `msm.create_project` | Creates a schema project directory, `<schema>.msm.project/`. |
| `msm.list_projects` | Lists the schema projects of the project list. |
| `msm.get_project_information` | Returns the project's metadata. |
| `msm.set_development_version` | Sets the version in section 910 of the development script. |
| `msm.get_released_versions` | Lists every released version. |
| `msm.get_last_released_version` | Returns the most recent release. |
| `msm.get_last_deployment_version` | Returns the version of the most recent generated deployment script. |
| `msm.get_deployment_script_versions` | Lists the versions of all generated deployment scripts. |
| `msm.get_section_sql_content` | Reads one section of a script. |
| `msm.set_section_sql_content` | Writes one section of a script. |
| `msm.set_schema_statements` | Adds, replaces, or changes schema objects from their `CREATE` statements. |
| `msm.drop_schema_object` | Removes a schema object from the project. |
| `msm.set_rest_statements` | Adds or replaces MariaDB REST Service services, schemas, and objects in section 180. |
| `msm.drop_rest_object` | Removes a REST service, schema, or object from section 180. |
| `msm.list_schema_diagrams` | Lists the project's schema diagrams. |
| `msm.get_schema_diagrams` | Returns the schema snapshot and the diagrams. |
| `msm.create_schema_diagram` | Adds a diagram of the schema's objects, laid out. |
| `msm.layout_schema_diagram` | Adds objects to a diagram and lays its figures out. |
| `msm.set_schema_diagram` | Adds a diagram from a document, or replaces the one of that name. |
| `msm.rename_schema_diagram` | Renames a diagram. |
| `msm.remove_schema_diagram` | Removes a diagram. |
| `msm.prepare_release` | Takes a snapshot of the development script and creates the update script. |
| `msm.generate_deployment_script` | Creates the deployment script that creates or upgrades the schema. |
| `msm.deploy_schema` | Deploys a schema version to a server. |
| `msm.list_live_schema_objects` | Lists the objects of a schema on a server that `msm.import_live_schema` can import. |
| `msm.import_live_schema` | Creates a schema project from a schema on a server, as a background task. |

## msm.create_project

Creates a schema project directory, `<schema>.msm.project/`, and adds it to the project list.

| Argument | Description |
| --- | --- |
| `schema_name` | The schema's name. |
| `target_path` | Where to create the project. Must be in an allowed path. |
| `copyright_holder` | Optional. The copyright holder for the generated files. |
| `copyrights` | Optional. The copyright notices of a project with more than one holder, used instead of `copyright_holder`. Each entry has a `holder`, a `yearOfCreation`, an optional `yearOfLastUpdate`, and a `tracksUpdates` flag. |
| `year_of_creation` | Optional. The year of creation of the copyright. Default: the current year. |
| `license` | Optional. A license name. An unrecognized name is rejected. |
| `overwrite_existing` | Whether to replace an existing project. Default: `False`. |
| `allow_special_chars` | Whether to allow all characters in the schema name. Default: `False`. |
| `enforce_target_path` | Whether to create `target_path` if it doesn't exist. Default: `False`. |
| `folder`, `caption`, `color` | Optional. The folder of the project list to file the project in, such as `/Shop`, and the caption and color to show it with. |

## msm.list_projects

Lists the schema projects of the project list. The tool takes no arguments. Each entry has the project's `project_path`, its `schema_name`, whether the directory still `exists`, its `development_version` and `last_released_version`, and the `folder`, `caption`, and `color` it is listed with. The MCP server lists only the projects that agents may work on.

## msm.get_project_information

Returns the project's metadata.

| Argument | Description |
| --- | --- |
| `schema_project_path` | The path of the schema project directory. Default: the working directory. Must be in an allowed path. |

## msm.set_development_version

Sets the version in section 910 of the development script.

| Argument | Description |
| --- | --- |
| `version` | The development version, as `major.minor.patch`. |
| `schema_project_path` | The path of the schema project directory. Default: the working directory. Must be in an allowed path. |

## msm.get_released_versions

Lists every released version.

| Argument | Description |
| --- | --- |
| `schema_project_path` | The path of the schema project directory. Default: the working directory. Must be in an allowed path. |

## msm.get_last_released_version

Returns the most recent release.

| Argument | Description |
| --- | --- |
| `schema_project_path` | The path of the schema project directory. Default: the working directory. Must be in an allowed path. |

## msm.get_last_deployment_version

Returns the version of the most recent generated deployment script.

| Argument | Description |
| --- | --- |
| `schema_project_path` | The path of the schema project directory. Default: the working directory. Must be in an allowed path. |

## msm.get_deployment_script_versions

Lists the versions of all generated deployment scripts.

| Argument | Description |
| --- | --- |
| `schema_project_path` | The path of the schema project directory. Default: the working directory. Must be in an allowed path. |

## msm.get_section_sql_content

Reads one section of a script.

| Argument | Description |
| --- | --- |
| `file_path` | The script file. |
| `section_id` | The section number. |

## msm.set_section_sql_content

Writes one section of a script.

| Argument | Description |
| --- | --- |
| `file_path` | The script file. |
| `section_id` | The section number. |
| `sql_content` | The new section content. It replaces the whole body of the section. |

Always edit sections with `msm.get_section_sql_content` and `msm.set_section_sql_content`, so the section banners are never corrupted. To add or change a table, use `msm.set_schema_statements` instead. After the first release, a change made to section 140 with `msm.set_section_sql_content` gets no `ALTER TABLE` in the update script.

## msm.set_schema_statements

Puts the `CREATE` statements of schema objects into the project, in the section and the form that each needs. The tool handles tables, sequences, views, procedures, functions, triggers, and events.

| Argument | Description |
| --- | --- |
| `statements` | The `CREATE` statements, one object each, with names that aren't qualified with the schema. |
| `renames` | Optional. The columns renamed in the new definitions of existing tables, as `{"table": {"old column": "new column"}}`. A renamed column keeps its data. |
| `dropped_columns` | Optional. The columns whose drop is intended, as `{"table": ["column"]}`, after a call was refused because of a possible rename. |
| `expect` | Optional. One `{kind, name, table}` entry for each statement, with `table` for a trigger. A statement that creates another object is refused before anything is written. |
| `base_hash` | Optional. The `source_hash` of the schema snapshot that the caller knows. The call is refused if the snapshot was made again since. Omit it to work on the project as it is. |
| `schema_project_path` | The path of the schema project directory. Default: the working directory. Must be in an allowed path. |

The tool works as follows:

* An object that the project doesn't have is added. A table or sequence goes into section 140, and any other object goes into section 150 in a form that can run again.
* A view, procedure, function, trigger, or event that the project has is replaced where it stands. An unchanged definition is left as it is.
* A table that the project has is changed to the definition given. Its columns, keys, checks, and options change where the script defines them. Once the project has a release, the `ALTER TABLE` that a deployed server needs is kept for the next update script.
* A sequence that the project has is refused.
* All statements are one edit: either everything is written, or nothing is. Without `base_hash`, the tool first makes the schema snapshot again if the script was edited by hand.

The result lists each statement with its `kind`, `name`, `file`, `line`, and whether it `replaced` an object and `changed` anything. It also has the `files` written, the `migration` statements kept for the next update script, and `notes` on what couldn't be changed or should be checked.

{% hint style="warning" %}
A `CREATE TABLE` for an existing table must be the complete definition. A column that the definition leaves out is dropped, with its data on a deployed server, and a table option such as `ENGINE` or `DEFAULT CHARSET` that it leaves out is removed. `AUTO_INCREMENT=n` is kept. To rename a column, name it in `renames`. If a dropped column and an added column are alike apart from the name, the call is refused and nothing is written, until `renames` names the rename or `dropped_columns` confirms the drop.
{% endhint %}

## msm.drop_schema_object

Removes a table, sequence, view, procedure, function, trigger, or event from the project's SQL. Once the project has a release, the `DROP` is kept for the next update script. The tool refuses to drop an object that another object needs, such as a table that a foreign key references, a sequence that a table uses, or a trigger that another trigger follows or precedes.

| Argument | Description |
| --- | --- |
| `kind` | `table`, `sequence`, `view`, `procedure`, `function`, `trigger`, or `event`. |
| `name` | The object's name. |
| `base_hash` | Optional. As for `msm.set_schema_statements`. |
| `schema_project_path` | The path of the schema project directory. Default: the working directory. Must be in an allowed path. |

## msm.set_rest_statements

Writes MariaDB REST Service services, schemas, and objects into section 180 of the development script, which every deployment runs in full. Each statement is written as `CREATE OR REPLACE`. An item that section 180 already creates is replaced where it stands, and a new item goes after the statements of its service or schema. The tool checks that nothing but the given items changes, and either writes everything or nothing.

| Argument | Description |
| --- | --- |
| `statements` | The `CREATE REST SERVICE`, `SCHEMA`, `VIEW`, `PROCEDURE`, or `FUNCTION` statements, one item each, with a new schema before its objects. A schema names its service with `ON SERVICE`, and an object its service and schema with `ON SERVICE ... SCHEMA ...`. `IF NOT EXISTS` is refused. |
| `replaces` | Optional. The REST object that the one statement renames, as `{"kind": "object", "service": ..., "schema": ..., "object": ...}`. A service or schema can't be renamed this way. |
| `base_hash` | Optional. As for `msm.set_schema_statements`. |
| `schema_project_path` | The path of the schema project directory. Default: the working directory. Must be in an allowed path. |

## msm.drop_rest_object

Removes a REST service, schema, or object from section 180, with everything on it. The tool writes no `DROP`: the next `msm.prepare_release` writes the removal into the update script's section 280.

| Argument | Description |
| --- | --- |
| `kind` | `service`, `schema`, or `object`. |
| `service` | The service's path, as section 180 writes it. |
| `schema` | The REST schema's path, for a schema or an object. |
| `object` | The REST object's path, for an object. |
| `base_hash` | Optional. As for `msm.set_schema_statements`. |
| `schema_project_path` | The path of the schema project directory. Default: the working directory. Must be in an allowed path. |

## Schema Diagram Tools

Section 160 of the development script holds the `msm_schema_diagrams` view. It has one `schema_definition` row with a snapshot of the schema objects that the `CREATE` statements define, and one row for each diagram. The diagram tools make the snapshot again first where the development script changed.

| Tool | Arguments | Description |
| --- | --- | --- |
| `msm.list_schema_diagrams` | `schema_project_path` | Lists the diagrams with their figures and connections, and whether the snapshot is current. |
| `msm.get_schema_diagrams` | `schema_project_path`, `diagram` | Returns the rows of the view: the snapshot, with its `source_hash`, and the diagrams, or only the named diagram with the snapshot. The picture of an image figure is left out. |
| `msm.create_schema_diagram` | `diagram`, `tables`, `views`, `sequences`, `routines`, `events`, `schema_project_path` | Adds a diagram, laid out, of the given tables (default: all tables) and of the views, sequences, routines, and events named. Every foreign key between two tables shown gets a connection. |
| `msm.layout_schema_diagram` | `diagram`, `tables`, `views`, `sequences`, `routines`, `events`, `keep_placed`, `schema_project_path` | Adds the objects named to a diagram and lays out the figures without a position. With `keep_placed` set to `False`, the tool lays out every figure again. |
| `msm.set_schema_diagram` | `document`, `schema_project_path` | Adds a diagram from an `msm-diagram/1` document, or replaces the diagram of that name. A figure without a position is placed by `msm.layout_schema_diagram`. |
| `msm.rename_schema_diagram` | `diagram`, `new_name`, `schema_project_path` | Renames a diagram. A name that another diagram has, compared case-insensitively, is refused. |
| `msm.remove_schema_diagram` | `diagram`, `schema_project_path` | Removes a diagram. |

## msm.prepare_release

Takes a snapshot of the development script and, from the second release on, creates the update script from the previous release. The update script receives the migration statements that `msm.set_schema_statements` and `msm.drop_schema_object` kept, and section 280 receives the removal of every REST service, schema, object, and auth app link that the previous release's section 180 created and this release's doesn't. The release fails if the schema snapshot can't be made from the development script.

| Argument | Description |
| --- | --- |
| `version` | The version to release. |
| `next_version` | The next development version. |
| `schema_project_path` | The path of the schema project directory. Default: the working directory. Must be in an allowed path. |
| `allow_to_stay_on_same_version` | Whether to allow the development to stay on the same version. Default: `False`. |
| `overwrite_existing` | Whether to replace existing files. Default: `False`. |

## msm.generate_deployment_script

Creates the deployment script that creates or upgrades the schema.

| Argument | Description |
| --- | --- |
| `version` | The version to generate. |
| `schema_project_path` | The path of the schema project directory. Default: the working directory. Must be in an allowed path. |
| `overwrite_existing` | Whether to replace an existing script. Default: `False`. |

{% hint style="danger" %}
Run `msm.prepare_release`, then complete the update script, and only then run `msm.generate_deployment_script`. The update script holds only the changes made with `msm.set_schema_statements` and `msm.drop_schema_object`. Changes made by hand, data backfills, removed procedures and functions (section 260), and revoked privileges (section 270) must be added to it. A script generated before the update script is complete creates the schema correctly on an empty server but doesn't upgrade an existing installation correctly.
{% endhint %}

## msm.deploy_schema

Deploys a schema version to a server. If the schema exists, it is upgraded to the version.

| Argument | Description |
| --- | --- |
| `connection_id` | A connection ID returned by `db.connect`. |
| `version` | Optional. The version to deploy. Default: the latest version that has a deployment script. |
| `schema_project_path` | The path of the schema project directory. Default: the working directory. Must be in an allowed path. |
| `backup` | Whether to dump an existing schema before the upgrade, so it can be restored if the upgrade fails. Default: `False`. |
| `backup_directory` | Where to write the backup. |
| `online_alter` | Optional. The online `ALTER TABLE` limits for this deployment, which take precedence over the project's `onlineAlter` setting. The keys are `enabled`, `maxRebuildBytes`, `galeraMaxBytes`, `nboLock`, `maxLockedBytes`, `lockWait`, `maxRetries`, and `tables`. |

An upgrade runs each `ALTER TABLE` in the least disruptive way that the server accepts: `INSTANT`, then `NOCOPY`, `INPLACE`, and `COPY` with `LOCK=NONE`, and then with a lock.

## msm.list_live_schema_objects

Lists the objects of a schema on a server that `msm.import_live_schema` can import: tables with their triggers, views with the objects that each reads, procedures, functions, triggers, events, and sequences. The result also has `schema_version`, the version that MSM deployed of the schema, or `null`.

| Argument | Description |
| --- | --- |
| `connection_id` | A connection ID returned by `db.connect`. |
| `schema` | The schema on the server. |

## msm.import_live_schema

Creates a schema project from a schema on a server. The development script receives the `CREATE` statements of the schema's objects, without `DEFINER` clauses, the schema's name, and `AUTO_INCREMENT` counters. Data, users, roles, grants, and MSM's own objects aren't imported. The server isn't changed.

| Argument | Description |
| --- | --- |
| `connection_id` | A connection ID returned by `db.connect`. |
| `schema` | The schema on the server. The project gets its name. |
| `target_path` | Where to create the project. Must be in an allowed path. |
| `objects` | Optional. The objects to import, as `{tables, views, procedures, functions, triggers, events, sequences: [names]}`. A kind that is left out imports none. Default: all objects. |
| `copyright_holder`, `copyrights`, `year_of_creation`, `license`, `overwrite_existing`, `enforce_target_path`, `folder`, `caption`, `color` | Optional. As for `msm.create_project`. |

The import runs as a background task and returns a `task_id`. Follow it with `task.get` and stop it with `task.cancel`. A cancelled import leaves no project behind.

## Script Sections

| Create script | Update script | Contents |
| --- | --- | --- |
| 130 | 230 | Helper routines, with names prefixed `msm_`. |
| 140 | 240 | Non-idempotent statements: tables, sequences, and base data. In an update script, all `ALTER` statements, data backfills, and every `DROP` of a table, sequence, view, trigger, or event that the new version no longer has. |
| 150 | 260 | Idempotent statements: views, procedures, functions, triggers, and events. Section 260 holds only the `DROP PROCEDURE IF EXISTS` and `DROP FUNCTION IF EXISTS` of the routines that the new version no longer has. |
| 160 | — | The schema snapshot and diagrams. Written by MSM; never edit this section. |
| 170 | 270 | Authorization. Section 170: `CREATE ROLE IF NOT EXISTS` and `GRANT`. Section 270: only `REVOKE` and `DROP ROLE`. |
| 180 | 280 | Optional MariaDB REST Service endpoints, with `CREATE OR REPLACE REST` statements. Section 280 removes the endpoints that the new version no longer has, and `msm.prepare_release` fills it. |
| 190 | 290 | Removal of the `msm_` helpers. |

Sections 140, 240, 170, and 270 become the body of a stored procedure in the generated script. Write them as plain statements terminated by `;`, without `DELIMITER` or `USE`, and use dynamic SQL for conditional DDL. Sections 130, 150, 160, 180, 230, 260, 280, 190, and 290 are emitted at the top level and use `DELIMITER %%` for routine bodies.

The deployment script runs the target version's sections 150, 170, and 180 in full on every deployment, after the table changes. New and changed views, routines, roles, grants, and REST endpoints therefore reach upgraded schemas without any statement in the update script. The update script only needs what these sections can't express: table changes and the `DROP` of removed objects in section 240, the `DROP` of removed routines in section 260, and `REVOKE` or `DROP ROLE` in section 270. Update scripts created by an older version of MSM have a section 250, which isn't deployed. Leave it empty.

{% hint style="warning" %}
Don't grant privileges in section 270. On an upgrade, it runs before section 170, so a role that is new in the version doesn't exist yet, and the deployment fails with error 1133.
{% endhint %}

<sub>_This page is licensed: GPLv2_</sub>

{% @marketo/form formId="4316" %}
