---
order: 7
slug: ship-a-schema-upgrade
title: "Ship a schema upgrade: version 1.1.0 in place"
description: >-
  Add notebooks and tags to the Notes App, fill the 1.0.0 → 1.1.0 update script,
  and upgrade a live install without dropping it. Includes the ordering mistake
  that silently produces a deployment script which cannot upgrade anything.
level: advanced
duration: "45 min"
area: schema-management
tools: ["msm.set_development_version", "msm.prepare_release", "msm.set_section_sql_content", "msm.generate_deployment_script", "msm.deploy_schema"]
skills: ["mariadb-schema-management-develop", "mariadb-schema-management-release", "mariadb-schema-management-deploy", "mariadb-alter-table"]
path_label: "Schema Lifecycle, Step 3"
prerequisites:
  - "[Tutorial 6](../versioned-schema-with-msm/) — you need a `notes_app.msm.project` with 1.0.0 released and deployed on a sandbox."
  - "The project directory on the MCP server's allowed-paths list."
---

Version one is the easy one. The interesting part of schema management is the
second release, because somewhere out there is a server holding version 1.0.0
with real data in it, and your job is to get it to 1.1.0 without dropping
anything.

<div class="callout callout--warn" markdown="1">
**The one rule everyone gets wrong.** `msm.prepare_release` creates an **empty**
update script. You must fill its migration sections **before** you generate the
deployment script — because the deployment script *embeds* them.

Generate first and you get a script that creates the schema perfectly on an empty
server and **silently fails to upgrade** an existing install. It does not error.
It just does not migrate. The order is:

`prepare_release` → **fill the update script** → `generate_deployment_script`
</div>

## Develop the next version

The development script `development/notes_app_next.sql` is already on 1.1.0 —
`prepare_release` bumped it when 1.0.0 was cut. Work in the same sections you
used before: new tables in **140**, new and changed views in **150**.

<div class="prompt" markdown="1">
*Develop the next version of the schema on top of 1.0.0: add support for
notebooks and tags with new `notebook` and `tag` tables, and add a view named
`notes_details` that joins notes with their notebook and their tags.*
</div>

```text
msm.get_sql_content_from_section(file_path=".../development/notes_app_next.sql", section_id="140")
msm.set_section_sql_content(file_path="…", section_id="140", sql_content="<existing + notebook + tag>")
msm.set_section_sql_content(file_path="…", section_id="150", sql_content="<existing views + notes_details>")
```

Note that section 140 gets the **whole** create story, old tables included. The
version script is a full snapshot of how to build the schema from nothing; it is
not a diff. The diff lives in the update script, which is the next step.

<div class="callout callout--tip" markdown="1">
**When a section grows past comfortable, break it out.** MSM supports
`SOURCE './sections/tables.sql'[53:];` inside a section — a **character-offset**
slice, relative to `development/`, used to strip each file's own copyright header
and footer. The files are inlined at `prepare_release`, so they are a development
convenience and never appear in a release. The
`mariadb-schema-management-develop` skill has the offset conventions.
</div>

## Prepare the release — and stop

```text
msm.prepare_release(version="1.1.0")
```

This does three things:

1. Snapshots the development script to `releases/versions/notes_app_1.1.0.sql`.
2. Creates **`releases/updates/notes_app_1.0.0_to_1.1.0.sql`** — an empty
   template with the update section banners in it.
3. Bumps the development version past 1.1.0.

**Do not generate the deployment script yet.** Step 2 is the thing you have to
fill in.

## Fill the update script

This is the actual work of the release: not "how do I build this schema" but
"how do I get a 1.0.0 database to 1.1.0 without losing its data". The update
script has its own section numbering:

| Section | Contents |
| --- | --- |
| 230 | Update helper routines (`msm_` prefix) |
| **240** | **Non-idempotent changes and ALL drops: `ALTER TABLE`, new tables, data backfill, `DROP`s that unblock table changes** |
| **250** | **Idempotent re-creation of changed views, routines, triggers, events** |
| 270 | Authorization changes: `GRANT` / `REVOKE` |
| 290 | Removal of the update helpers |

<div class="prompt" markdown="1">
*Fill the 1.0.0 → 1.1.0 update script with the migration: the new `notebook` and
`tag` tables in the non-idempotent update section, and the `notes_details` view
in the idempotent update section.*
</div>

```text
msm.set_section_sql_content(
  file_path=".../releases/updates/notes_app_1.0.0_to_1.1.0.sql",
  section_id="240",
  sql_content="CREATE TABLE `notebook` (…); CREATE TABLE `tag` (…); ALTER TABLE `note` ADD COLUMN `notebook_id` UUID NULL; …")

msm.set_section_sql_content(
  file_path="…",
  section_id="250",
  sql_content="CREATE OR REPLACE VIEW `notes_details` AS SELECT …;")
```

Three things to get right in section 240, all of them MariaDB-specific and all
of them taught by the `mariadb-alter-table` skill:

- **A new `NOT NULL` column on a populated table needs a default, or a
  backfill.** `ADD COLUMN … NOT NULL` with no default fails on a non-empty table
  in strict mode. Add it nullable, backfill, then tighten — three statements, all
  in 240.
- **Say which algorithm you expect.** `ALGORITHM=INSTANT` on a change that cannot
  be instant fails loudly, which is exactly what you want in a migration —
  better than discovering at deploy time that it silently chose `COPY` and locked
  the table for an hour. `ALGORITHM=NOCOPY` is the useful middle ground.
- **No `DELIMITER` in 240.** Section 240 becomes a stored-procedure body in the
  generated script. Plain `;`-terminated statements, dynamic SQL for anything
  conditional. Section 250 is top level and does use `DELIMITER %%`.

<div class="callout callout--warn" markdown="1">
**Drops go in 240, not 250** — including drops whose only purpose is to unblock a
table change. Section 250 is for *re-creating* things idempotently; anything
destructive is version-guarded state and belongs in 240.
</div>

Read it back and confirm it is not still the template. The generated template
contains `ToDo` comments; a script that still has them is one nobody filled:

```text
msm.get_sql_content_from_section(file_path=".../notes_app_1.0.0_to_1.1.0.sql", section_id="240")
```

## Now generate the deployment script

```text
msm.generate_deployment_script(version="1.1.0")
```

The result, `releases/deployment/notes_app_deployment_1.1.0.sql`, contains
**both** paths: the full create story for an empty server, and the embedded
1.0.0 → 1.1.0 migration for a server that already has the old version. It reads
`msm_schema_version` at run time to decide which one applies.

<div class="prompt" markdown="1">
*Show me that the 1.1.0 deployment script contains both the `notebook` and `tag`
tables and the `notes_details` view, and that it carries the 1.0.0 → 1.1.0
migration and not just the create path.*
</div>

## Upgrade the live 1.0.0 install

The sandbox from the previous tutorial is still on 1.0.0. Put some data in it
first, so the upgrade has something to preserve:

<div class="prompt" markdown="1">
*Insert a few users and notes into the sandbox, then deploy version 1.1.0 onto
it — take a backup first — and show me that the original rows survived and the
new tables exist.*
</div>

```text
db.connect(uri="root@127.0.0.1:3310")
msm.deploy_schema(connection_id="…", version="1.1.0",
                  backup=True, backup_directory="/abs/path/backups")
db.execute_sql(connection_id="…", sql="SELECT * FROM notes_app.msm_schema_version")
db.execute_sql(connection_id="…", sql="SELECT COUNT(*) FROM notes_app.note")
```

`msm_schema_version` should now read 1.1.0, `notebook` and `tag` should exist,
and the note count should be exactly what it was before. That last check is the
one that matters — it is the difference between an upgrade and a re-create.

## Prove the other path too

A deployment script that upgrades correctly can still be broken for fresh
installs, and you will not find out until someone provisions a new environment:

<div class="prompt" markdown="1">
*Deploy a second sandbox on port 3311 and apply the 1.1.0 deployment script to
it directly, with no 1.0.0 step. Confirm it produces the same schema as the
upgraded server.*
</div>

Both paths, every release. It costs one sandbox and catches the failure mode
that is otherwise found in production.

<h2 class="no-step" id="what-you-built">What you built</h2>

Two releases of one schema, and a deployment script that handles both a fresh
install and an in-place upgrade — verified on two servers rather than asserted.

The rule worth tattooing somewhere: **`prepare_release`, then fill the update
script, then generate.** Getting that order wrong produces an artifact that
passes every test you would think to run and fails on the only server that
matters.

**Where to go next**

- [Expose the schema over REST](../rest-endpoints/) — MSM section 180 exists for
  exactly this, so the endpoints ship with the release.
- [Diagnose a slow query](../diagnose-a-slow-query/) — the index that comes out
  of it belongs in a release, not in a hand-run `ALTER`.
