---
order: 6
slug: versioned-schema-with-msm
title: "Version a schema with MSM: create, release, deploy"
description: >-
  Turn the Notes App from a one-off create script into a versioned MariaDB
  Schema Management project — a schema you can ship version 2 of, to servers
  that are still running version 1.
level: intermediate
duration: "60 min"
area: schema-management
tools: ["msm.create_project", "msm.get_sql_content_from_section", "msm.set_section_sql_content", "msm.prepare_release", "msm.generate_deployment_script", "msm.deploy_schema"]
skills: ["mariadb-schema-management", "mariadb-schema-management-create", "mariadb-schema-management-release", "mariadb-schema-management-deploy"]
path_label: "Schema Lifecycle, Step 2"
prerequisites:
  - "[Tutorial 1](../notes-app-sandbox/) — you should have seen a plain create script first, to appreciate what this adds."
  - "The working directory on the MCP server's allowed-paths list. Every `msm.*` tool is path-gated."
---

A create script builds a schema once. The second time you need it, the schema is
already there and half-changed, and the script is useless. **MariaDB Schema
Management (MSM)** is the answer: a project on disk that tracks every version of
a schema, and generates a deployment script that either creates the schema fresh
*or* upgrades whatever older version it finds.

Prefer MSM over a one-off script whenever a schema will evolve and be deployed
somewhere that may hold an earlier version. This tutorial takes the Notes App
through its first release. [Tutorial 7](../ship-a-schema-upgrade/) ships the
second.

## Understand the shape before you start

Two ideas carry the whole system, and the `mariadb-schema-management` skill
teaches the agent both.

**A project directory**, scaffolded for you:

```text
notes_app.msm.project/
├── msm.project.json        # schemaName, license, copyrightHolder, dependencies
├── development/
│   ├── notes_app_next.sql  # the working script — no version in the name
│   └── sections/           # optional SOURCE breakout files
└── releases/
    ├── versions/    notes_app_1.0.0.sql                # full snapshot per release
    ├── updates/     notes_app_1.0.0_to_1.1.0.sql       # migration — you fill this
    └── deployment/  notes_app_deployment_1.0.0.sql     # generated; never edit
```

**A section model.** MSM scripts are plain SQL split by
`-- ##### … MSM Section NNN: Title` banners, and **which section a statement
lives in decides how the deployment script treats it**:

| Section | Contents |
| --- | --- |
| 110 / 120 | `CREATE SCHEMA`, version indicator (provided) |
| 130 | Helper routines used during creation — names must start `msm_` |
| **140** | **Non-idempotent: `CREATE TABLE` and base-data `INSERT`s** |
| **150** | **Idempotent: views, procedures, functions, triggers, events** |
| 170 | Authorization: `CREATE ROLE`, `GRANT` |
| 180 | Optional MariaDB REST Service endpoints |
| 190 | Removal of the `msm_` helpers |
| 910 / 920 | Final version, server-variable restore (provided) |

The split is **idempotent versus not**. Tables and data are state that cannot be
re-run, so they are version-guarded. Everything else is written with
`CREATE OR REPLACE` / `DROP … IF EXISTS` and can safely run every time.

<div class="callout callout--warn" markdown="1">
**Never edit section banners by hand.** Sections are read and written with
`msm.get_sql_content_from_section` and `msm.set_section_sql_content`, addressed
by `file_path` + `section_id`. Hand-editing a banner corrupts the file in a way
that only shows up at release time.
</div>

## Scaffold the project

<div class="prompt" markdown="1">
*Use the MariaDB Schema Management tools to manage a note-taking app as a
versioned schema project. Create an MSM schema project for a schema named
`notes_app` in the current directory.*
</div>

```text
msm.create_project(schema_name="notes_app", target_path="/abs/path",
                   copyright_holder="…")
```

<div class="callout" markdown="1">
`license` takes the *name* of a license the shell knows, and an unrecognized one
is rejected outright — `license="GPLv2"` fails, because there is no stored
license by that name. Omit the parameter, or pass your own license text.
</div>

## Author version 1.0.0 into the right sections

This is where the section model earns its keep. Tables go in **140**, the view
goes in **150**:

<div class="prompt" markdown="1">
*For the initial version 1.0.0, author two tables — `user` and `note` — plus a
view named `user_activity` that lists users ordered by how many notes they have.
Put the tables in the non-idempotent create section and the view in the
idempotent create section.*
</div>

```text
msm.set_section_sql_content(
  file_path=".../development/notes_app_next.sql",
  section_id="140",
  sql_content="CREATE TABLE `user` (…); CREATE TABLE `note` (…);")

msm.set_section_sql_content(
  file_path=".../development/notes_app_next.sql",
  section_id="150",
  sql_content="CREATE OR REPLACE VIEW `user_activity` AS SELECT …;")
```

<div class="callout callout--warn" markdown="1">
**The delimiter rule, and why it exists.** In the generated deployment script,
sections **140, 240, 170 and 270** become the *body of a stored procedure*. Write
them as plain `;`-terminated statements with **no `DELIMITER`**, and use dynamic
SQL for conditional DDL. Sections **130, 150, 230, 250, 190 and 290** are emitted
at top level and use `DELIMITER %%` for routine bodies.

Getting this backwards produces a deployment script that fails to parse, with an
error that points at a line you did not write.
</div>

Check what landed where before moving on:

```text
msm.get_sql_content_from_section(file_path="…", section_id="140")
msm.get_sql_content_from_section(file_path="…", section_id="150")
```

## Prepare the 1.0.0 release

<div class="prompt" markdown="1">
*Prepare the 1.0.0 release and generate its deployment script.*
</div>

```text
msm.prepare_release(version="1.0.0")
msm.generate_deployment_script(version="1.0.0")
```

`prepare_release` snapshots `development/notes_app_next.sql` into
`releases/versions/notes_app_1.0.0.sql`, bumps the development version, and —
for a first release — there is no previous version to migrate from, so no update
script is needed. `generate_deployment_script` then composes
`releases/deployment/notes_app_deployment_1.0.0.sql`.

**That deployment script is the artifact you ship.** It is a create-or-upgrade
script: given an empty server it creates the schema, given an older version it
migrates. It is generated, so never edit it — change the source and regenerate.

## Deploy onto a live server

`msm.deploy_schema` needs an open `db.connect` connection, so deploy a sandbox
first if you do not have a target:

<div class="prompt" markdown="1">
*Spin up a sandbox on port 3310 with root password `demo-pw`, connect to it, and
deploy version 1.0.0 of the schema.*
</div>

```text
sandbox.deploy(port=3310, password="demo-pw")
db.connect(uri="root@127.0.0.1:3310")
msm.deploy_schema(connection_id="…", version="1.0.0")
```

`backup=True` with a `backup_directory` takes a backup before applying — worth
it against anything you would miss.

## Verify on the server, not in the transcript

```text
db.list_objects(connection_id="…", schema_name="notes_app", object_type="table")
db.list_objects(connection_id="…", schema_name="notes_app", object_type="view")
db.execute_sql(connection_id="…", sql="SELECT * FROM notes_app.msm_schema_version")
```

That last query is the point of the whole exercise: the schema now carries its
own version number, in a `msm_schema_version` view defined by section 910. A
future deployment script reads it to decide whether to create or to upgrade, and
from which version.

## Check the project state

```text
msm.get_project_information()
msm.get_released_versions()        → ["1.0.0"]
msm.get_last_released_version()    → "1.0.0"
msm.get_deployment_script_versions()
msm.get_last_deployment_version()
```

Useful on their own, and essential when you come back to a project months later
and cannot remember what was released versus what was merely developed.

<h2 class="no-step" id="what-you-built">What you built</h2>

A versioned schema project with one release, a generated deployment script, and
a live server carrying a version number it can be upgraded from.

The distinction to hold onto: **the development script is where you work, the
release is a snapshot, the deployment script is the artifact.** You edit the
first, `prepare_release` makes the second, `generate_deployment_script` makes the
third, and you edit the third never.

**Where to go next**

- [Ship a schema upgrade](../ship-a-schema-upgrade/) — version 1.1.0, and the one
  rule everyone gets wrong the first time.
