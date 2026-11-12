---
name: mariadb-schema-management-create
description: "Scaffold a MariaDB Schema Management (MSM) project and author the initial schema in the development folder — create the project with msm.create_project, or import it from a MySQL Workbench model (msm.import_workbench_model) or a schema on a live server (msm.import_live_schema), and write the first version's tables, objects and grants into the MSM sections of <schema>_next.sql. Use when starting a new versioned/maintainable MariaDB schema, creating an MSM schema project, bringing an existing schema under MSM, or authoring the initial development script. Read mariadb-schema-management first for the section model."
---

# MSM — Creating the Initial Schema

This is step 1 of the MSM lifecycle (see `mariadb-schema-management` for the
overview and the full section model). Here you scaffold the project and author
the **first** version of the schema in the development folder. Driven by the
`msm.*` tools of the `mariadb-shell` MCP server. Assume MariaDB 11.8.

## 1. Scaffold the project

```text
msm.create_project(
    schema_name="notes-app",
    target_path="<parent dir>",
    copyright_holder="...",   # optional, written into notices as given
    license="MIT",            # optional: GPL-2.0 | MIT | BSD | None
    year_of_creation="2024",  # optional; defaults to the current year
)
```

This creates `<schema>.msm.project/` with `msm.project.json`, the
`development/<schema>_next.sql` working script (initial development version
`0.0.1`), and the empty `releases/{versions,updates,deployment}/` folders, and
adds the project to the project list (`msm.list_projects`). Several holders go
in `copyrights=[{holder, yearOfCreation, yearOfLastUpdate, tracksUpdates}]`
instead of `copyright_holder`. `msm.get_project_information` returns the schema
name, versions, paths and settings; change settings later (a `CUSTOM` license,
`maxInlineSectionSize`, ...) with `msm.set_project_settings`, never by editing
`msm.project.json`.

### Or import an existing schema

Both imports create a **new** project (like `msm.create_project`, same
`target_path`, copyright and license arguments), write the CREATE statements
into sections 140/150 (breakout files where a section is large) and make the
schema snapshot, so they need `mariadb-lsp`.

#### From a MySQL Workbench model

```text
msm.import_workbench_model(
    model_path="<path>/shop.mwb",
    target_path="<parent dir>",
    schema="shop",            # only needed when the model has several schemas
    copyright_holder="...",   # optional, as for msm.create_project
    license="MIT",            # optional
)
```

- There is no re-import into an existing project.
- Tables, keys and the model's rows go to section 140, the other objects to
  150, roles and grants to 170 (as breakout files where a section is large);
  the model's EER diagrams become the project's diagrams (section 160).
- SQL scripts attached to the model are listed in `scripts_not_imported`, never
  run or copied: read them and move what belongs into the right sections.

Read `warnings` in the result, then review the generated sections as if you had
written them (step 2's rules apply). A Workbench model is a MySQL model: check
collations (such as `utf8mb4_0900_ai_ci`), engines and defaults against the
target MariaDB version.

#### From a schema on a server

Needs a `db.connect` connection.

1. `msm.list_live_schema_objects(connection_id, schema)` lists the tables
   (with their triggers), views (with `reads`: what each view reads),
   procedures, functions, triggers, events and sequences, plus
   `schema_version` (the version msm deployed there, or null).
2. `msm.import_live_schema(connection_id, schema, target_path,
   objects=None)` imports all, or only the names in `objects` (`{tables,
   views, procedures, functions, triggers, events, sequences: [names]}`; a
   kind left out imports none; without `triggers` the selected tables bring
   theirs). It starts a task: follow it with `task.get`; a `task.cancel`
   leaves no project behind. Anything that would refuse the import (target
   path, selection, license, missing `mariadb-lsp`) refuses the call itself.

DEFINER clauses, the schema's own name and `AUTO_INCREMENT=N` are removed,
so the project deploys under any name. **Not imported:** data, users, roles,
grants and msm's own `msm_*` objects; add base data and authorization by
hand. A foreign key to a table left out is dropped with a warning; a view
reading an object left out gets a warning too. Refused: two names that differ
only in case (tables, views and sequences share one namespace), and any
selected view when the `mariadb-lsp` found cannot tell what views read (then
every view's `reads` is null). The
server's schema is not changed, and `msm.deploy_schema` refuses an existing
schema msm does not manage (no `msm_schema_version` view).

Do **not** add the standalone "Start Block" from `mariadb-schema-create-script`
here — sections 010/920 already save and restore the server variables.

## 2. Author the schema into the right sections

Edit `development/<schema>_next.sql` by section, using
`msm.set_section_sql_content(file_path, section_id, sql_content)` (and
`msm.get_sql_content_from_section` to read one) so the section banners stay
intact (it replaces the whole body, so the template's commented-out examples
go with it). Put each kind of object in the section that matches how MSM
deploys it:

- **Section 140 — tables, sequences and base data (non-idempotent).**
  `CREATE TABLE`, `CREATE SEQUENCE` and standard seed `INSERT`s only. This becomes a stored-procedure body in the
  deployment script, so write plain `;`-terminated statements with **no
  `DELIMITER`**.

  Unless told otherwise, use the MariaDB native UUID datatype for primary key columns for tables that will most likely be exposed directly to client applications. This is done in order to prevent enumeration attacks, hide business intelligence and prevent information leakage about record creation order.

  > **Important**: For UUIDs always use the native MariaDB UUID datatype, usage: `UUID NOT NULL DEFAULT UUID_v7()`. Never use `CHAR(36)`.

  ```sql
  CREATE TABLE `notes-app`.`note`(
      `id` UUID NOT NULL DEFAULT UUID_v7() PRIMARY KEY,
      `title` VARCHAR(255) NOT NULL,
      `body` MEDIUMTEXT
  );

  INSERT INTO `notes-app`.`note`(`title`) VALUES ('Welcome');
  ```

- **Section 150 — all other objects (idempotent).** VIEWs, PROCEDUREs,
  FUNCTIONs, TRIGGERs, EVENTs. This is emitted at top level with `DELIMITER %%`;
  every object must be safe to re-run, so use `CREATE OR REPLACE` or an explicit
  `DROP ... IF EXISTS` first. Create routines before views: a `CREATE VIEW`
  that calls a function not created yet fails (error 1305), while routine,
  trigger and event bodies are not checked at `CREATE`. A view on another view
  comes after it.

  ```sql
  DELIMITER %%

  DROP PROCEDURE IF EXISTS `notes-app`.`add_note`%%
  CREATE PROCEDURE `notes-app`.`add_note`(IN t VARCHAR(255))
  BEGIN
      INSERT INTO `notes-app`.`note`(`title`) VALUES (t);
  END%%

  CREATE OR REPLACE SQL SECURITY INVOKER VIEW `notes-app`.`note_titles` AS
      SELECT `id`, `title` FROM `notes-app`.`note`%%

  DELIMITER ;
  ```

- **Section 170 — authorization.** `CREATE ROLE IF NOT EXISTS` and `GRANT`.
  Also a stored-procedure body → plain `;`-terminated statements, no
  `DELIMITER`. It runs in full on every deployment, upgrades included, so it
  must be re-runnable; create every role before granting to it — a `GRANT` to a
  missing role fails the deployment (error 1133).
- **Section 180 — optional REST endpoints** (see `mariadb-rest-service-create`).
  Runs in full on every deployment: use `CREATE OR REPLACE REST ...`, which
  updates an endpoint in place and keeps its id. To remove an endpoint, just
  delete it from 180: on upgrades msm drops it (`msm.prepare_release` writes
  the drop into the update script's section 280). The server needs the REST
  metadata schema, and only MariaDB Shell (`msm.deploy_schema`) can run these
  statements.
- **Sections 130 / 190 — creation helpers.** Optional routines whose names must
  start `msm_`, defined in 130 and dropped in 190; use them for logic needed only while building the schema.

Instead of writing a section by hand, `msm.add_schema_object` adds a view,
procedure, function, trigger, event or sequence from a template, and
`msm.edit_schema` adds tables, columns, keys, views and routines; both put the
statement in the right section themselves (see
`mariadb-schema-management-develop`).

## 3. Set the initial version

The version lives in section 910 (the `msm_schema_version` view). Set it with:

```text
msm.set_development_version(version="0.1.0")
```

Use whatever development version you intend to release first; MSM starts a fresh project at `0.0.1`.

## Guidelines

- Only tables, sequences and data go in 140; **everything else** goes in 150 — mixing them
  breaks the deployment script's create/upgrade split.
- Idempotent objects (150) must use `CREATE OR REPLACE` / `DROP IF EXISTS`.
- Keep object definitions grouped and commented; once the file grows, split
  sections into SOURCE breakout files with `msm.split_sections` (see
  `mariadb-schema-management-develop`).
- For a picture of the schema, add a laid-out diagram with
  `msm.create_schema_diagram` (see `mariadb-schema-management-develop`).
- End the answer with the review link to the project and its diagram (see
  "Handing the project back" in `mariadb-schema-management`).
- When the first version is ready, prepare a release
  (`mariadb-schema-management-release`).

## See Also

- `mariadb-schema-management` — lifecycle overview and full section model.
- `mariadb-schema-management-develop` — evolving the schema and SOURCE breakout files.
- `mariadb-schema-management-release` — preparing the first release.
- `mariadb-create-table`, `mariadb-create-view`, `mariadb-create-procedure`, `mariadb-create-function`, `mariadb-grant` — the underlying DDL.
