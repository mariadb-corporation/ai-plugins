---
name: mariadb-schema-management
description: "Overview of managing a MariaDB database schema across its whole lifecycle with the MariaDB Schema Management (MSM) plugin via the mariadb-shell MCP server — the versioned schema project, the MSM section model, and the create → develop → release → deploy workflow. Use when asked to create a maintainable/versioned MariaDB schema, put an existing schema or MySQL Workbench model under version control, manage schema migrations/upgrades/releases, or deploy/update a schema on a server; then read the focused sub-skill for the specific step."
---

# MariaDB Schema Management (MSM) — Overview

The MariaDB Schema Management (MSM) plugin manages a database schema across its
**whole lifecycle** — first creation, every versioned release, and in-place
upgrades — as a **schema project** on disk, driven by the `msm.*` tools of the
**`mariadb-shell` MCP server**. Prefer MSM over a one-off create script whenever
a schema will evolve and be deployed to servers that may hold an older version.
(For a single, non-versioned create script, use `mariadb-schema-create-script`
instead.)

Assume MariaDB 11.8 if not told otherwise. This skill is the map; read the
focused sub-skill for the step you are on.

## The lifecycle

```text
create project + author initial schema   →  mariadb-schema-management-create
  (or import a Workbench model / a live schema)
        │
        ▼
develop the next version in _next.sql     →  mariadb-schema-management-develop
        │
        ▼
prepare release vX  +  FILL update script  →  mariadb-schema-management-release
   +  generate deployment script
        │
        ▼
deploy vX (create fresh OR upgrade)        →  mariadb-schema-management-deploy
        │
        └──────────────► back to develop (dev version already bumped)
```

> **The one rule everyone gets wrong:** `prepare_release` creates the update
> script (`releases/updates/<schema>_<prev>_to_<vX>.sql`) empty, holding only
> what `msm.edit_schema` kept. You MUST fill its table-migration section 240
> (260 for removed procedures/functions, 270 for revoked privileges) **before**
> generating the deployment script — the deployment script embeds them to
> upgrade existing installs. See `mariadb-schema-management-release`.

## Project layout

`msm.create_project` scaffolds:

```text
<schema>.msm.project/
├── msm.project.json     # settings (below)
├── development/
│   ├── <schema>_next.sql            # the working script; version lives in section 910
│   ├── <schema>_update_next.sql     # pending update script: msm.edit_schema's migration
│   └── sections/                    # optional SOURCE breakout files (see -develop)
└── releases/
    ├── versions/    <schema>_<x.y.z>.sql              # full CREATE snapshot per release
    ├── updates/     <schema>_<x.y.z>_to_<a.b.c>.sql   # per-release migration (fill by hand)
    └── deployment/  <schema>_deployment_<x.y.z>.sql   # generated; create-or-upgrade; never edit
```

`msm.project.json` holds `schemaName` (fixed), `copyrights` (holder,
`yearOfCreation`, `yearOfLastUpdate`, `tracksUpdates`), `license` (`BSD`,
`GPL-2.0`, `MIT`, `None` or `CUSTOM` with a `customLicense` text),
`onlineAlter` (see `-deploy`), `maxInlineSectionSize`, `substitutions` and
`schemaDependencies`. Read them with `msm.get_project_information`; change them
**only** with `msm.set_project_settings(settings)`: only the keys given change,
each value replaces the stored one whole (`null` removes an optional key),
nothing is written when a value is refused, and the notices and license blocks
of the development files follow (released files stay as released).

Versions use **semantic versioning** (`major.minor.patch`). The development file
carries the `_next` suffix (no version in the name); the version is stored in the
`msm_schema_version` view defined in section 910.

## The MSM section model (shared reference)

MSM scripts are plain SQL split into numbered sections marked by
`-- ##### ... MSM Section NNN: Title` banners. **The section a statement lives in
determines how the deployment script treats it.** Always edit sections with
`msm.get_sql_content_from_section` / `msm.set_section_sql_content` (by
`file_path` + `section_id`) so the banners are never corrupted.

**Create / version script** (author with `-create`, evolve with `-develop`):

| Section | Contents |
| --- | --- |
| 010 | Server-variable save (provided) |
| 110 | `CREATE SCHEMA IF NOT EXISTS` (provided) |
| 120 | Version-creation indicator: `msm_schema_version` = `0,0,0` (provided) |
| 130 | Helper routines used during creation — names must start `msm_` |
| **140** | **Non-idempotent: `CREATE TABLE`, `CREATE SEQUENCE` + base-data `INSERT`s** |
| **150** | **Idempotent: VIEWs / PROCEDUREs / FUNCTIONs / TRIGGERs / EVENTs** — run in full on every deployment |
| 160 | Schema diagrams: the `msm_schema_diagrams` VIEW — **written by msm, never by hand** (see below) |
| 170 | Authorization: `CREATE ROLE IF NOT EXISTS` / `GRANT` — run in full on every deployment |
| 180 | Optional MariaDB REST Service endpoints (`CREATE OR REPLACE REST ...`) — run in full on every deployment |
| 190 | Removal of the `msm_` helpers |
| 910 | Final schema version — set via `msm.set_development_version` |
| 920 | Server-variable restore (provided) |

**Update script** (fill during `-release`):

| Section | Contents |
| --- | --- |
| 010 / 220 | Server vars + update indicator `0,0,0` (provided) |
| 230 | Update helper routines (`msm_`) |
| **240** | **Non-idempotent changes + drops: `ALTER TABLE`, new tables/sequences, data backfill, and `DROP ... IF EXISTS` of every table / SEQUENCE / VIEW / TRIGGER / EVENT the new version no longer has** |
| **260** | **Removal of PROCEDUREs and FUNCTIONs: `DROP PROCEDURE/FUNCTION IF EXISTS`** of every routine the new version no longer has (a routine DROP fails inside 240, error 1357) |
| 270 | `REVOKE` / `DROP ROLE` only. New roles and grants go in the dev script's section 170 |
| 290 | Removal of the 230 update helpers — **nothing else** |
| 910 / 920 | New version + server-variable restore (provided) |

There is **no section 250**: new and changed VIEWs / routines / triggers /
events go in the dev script's section 150. Update scripts made by an older msm
still have a 250; it is ignored, leave it empty (and see `-release` for the
routine DROPs such scripts keep in 290).

**Idempotent vs. non-idempotent** — the core distinction:
- **Non-idempotent** (140 create / 240 update): `TABLE` structure and data —
  state that cannot be trivially re-run, so it is version-guarded. The
  deployment script runs 140 on a fresh install, or each 240 step in turn on an
  upgrade.
- **Idempotent** (150): everything else — always written with
  `CREATE OR REPLACE` / `DROP ... IF EXISTS` so re-running is safe. The
  deployment script runs the **target version's full section 150 on every
  deployment, after the table changes**, so the objects always end in the target
  state whatever version the server started from. They therefore never need
  per-version update statements — which is why update scripts have no section
  for them. Only a *removed* object needs a `DROP ... IF EXISTS`: in 240, or in
  260 for a procedure or function. Every update script's 260 runs on **every**
  deployment of a later version (fresh installs too), after the table changes
  and before the target's 150 re-creates every routine it has — so a routine
  removed in one release and added again later survives.
- **Authorization and REST work the same way:** the target's sections 170 and
  180 also run on every deployment (170 after the 270 steps), so new roles,
  grants and endpoints reach upgraded schemas through them. Section 270 is only
  for what 170 cannot express: `REVOKE` and `DROP ROLE`. Never `GRANT` in 270 —
  on an upgrade it runs before 170 creates a new role, and the deployment fails
  (error 1133, because the scripts set `NO_AUTO_CREATE_USER`).

**Schema diagrams (section 160).** The `msm_schema_diagrams` VIEW (`name`,
`format`, `document`) holds one row `schema_definition` (format `msm-schema/1`):
a snapshot of the schema objects the CREATE statements define, as the MariaDB SQL
language server (`mariadb-lsp`) outlines them; and one row per EER diagram
(format `msm-diagram/1`: layers, figures, connections). **The CREATE statements
are the source of truth** — never edit the snapshot; change the SQL and run
`msm.update_schema_definition`, or use `msm.edit_schema` (see `-develop`).
`msm.prepare_release` makes the snapshot again
itself and **fails without `mariadb-lsp`, or when a statement of the
development script cannot be parsed** (the snapshot would miss its objects). Once
the VIEW is larger than the project's `maxInlineSectionSize` (default 16 KB, in
`msm.project.json`) msm keeps it in `development/sections/160_schema_diagrams.sql`,
included with SOURCE.

**Delimiter/placement rule** (why the split exists): in the generated deployment
script, sections **140, 240, 170, 270** become the *body of a stored procedure*
— write them as plain `;`-terminated statements, **no `DELIMITER`**, no `USE`
(qualify names with the schema), use dynamic SQL for conditional DDL. Sections
**130, 150, 160, 180, 230, 260, 190, 290** are emitted at top level; use
`DELIMITER %%` for routine bodies.

## The `msm.*` MCP tools

- **Project:** `msm.create_project`, `msm.import_workbench_model` (from a MySQL
  Workbench `.mwb`), `msm.get_project_information`, `msm.set_project_settings`.
- **Project list:** `msm.list_projects`, `msm.add_project`,
  `msm.update_project`, `msm.remove_project` (the list only; folders stay).
- **Sections:** `msm.get_sql_content_from_section`, `msm.set_section_sql_content`,
  `msm.split_sections` (into breakout files).
- **Objects:** `msm.edit_schema` (rename/add/change/drop tables, columns,
  indexes, keys, views, routines), `msm.get_object_templates`,
  `msm.add_schema_object` (view, procedure, function, trigger, event, sequence).
- **Versions:** `msm.set_development_version`, `msm.get_released_versions`,
  `msm.get_last_released_version`, `msm.get_last_deployment_version`,
  `msm.get_deployment_script_versions`.
- **Diagrams:** `msm.list_schema_diagrams`, `msm.get_schema_diagrams`,
  `msm.get_schema_diagram_image`, `msm.update_schema_definition` (after
  changing CREATE statements), `msm.create_schema_diagram`,
  `msm.layout_schema_diagram`, `msm.set_schema_diagram`,
  `msm.rename_schema_diagram`, `msm.remove_schema_diagram`.
- **Release:** `msm.prepare_release`, `msm.generate_deployment_script`.
- **Online ALTER TABLE settings:** `msm.get_online_alter_settings`,
  `msm.get_online_alter_defaults`.
- **Need an open `db.connect` connection** (served only with the `db` group):
  `msm.deploy_schema`, `msm.online_alter_table`, `msm.list_live_schema_objects`,
  `msm.import_live_schema`. `msm.online_alter_table` and
  `msm.import_live_schema` start a task: follow it with `task.get`, stop it
  with `task.cancel`.

Every tool that reads the structure of the SQL — the snapshot, diagram creation
and layout, `edit_schema`, `split_sections`, the Workbench import and
`prepare_release` — needs the MariaDB SQL language server's binary
`mariadb-lsp`, installed with the MariaDB Shell; without it the call fails.

## See Also

- `mariadb-schema-management-create` — scaffold or import the project and author the initial schema.
- `mariadb-schema-management-develop` — evolve `_next.sql` for the next version, incl. SOURCE breakout files.
- `mariadb-schema-management-release` — prepare a release, fill the update script, generate the deployment script.
- `mariadb-schema-management-deploy` — create or upgrade a schema on a live server.
- `mariadb-schema-create-script` — the standalone (non-MSM) single create script.
