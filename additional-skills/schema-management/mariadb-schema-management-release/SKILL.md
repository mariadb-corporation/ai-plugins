---
name: mariadb-schema-management-release
description: "Prepare a MariaDB Schema Management (MSM) version release — snapshot the development script with msm.prepare_release, FILL the generated previous→new update script (table changes and drops in section 240, removed procedures/functions in 260, revoked privileges in 270) with the actual migration, and only then generate the deployment script with msm.generate_deployment_script. Use when cutting/preparing an MSM schema release or version, writing the release-to-release migration, or generating a deployment script. Read mariadb-schema-management first for the section model."
---

# MSM — Preparing a Version Release

This step turns the current development script into a released version and, for
any release after the first, produces the migration from the previous release.
See `mariadb-schema-management` for the section model. Assume MariaDB 11.8.

**The order is mandatory:**

```text
1. msm.prepare_release          → version snapshot (+ update script)
2. FILL the update script       → sections 240 (+ 260, 270), check 280  ← do NOT skip
3. msm.generate_deployment_script  ← only after step 2
```

## 1. Prepare the release

```text
msm.prepare_release(version="1.1.0", next_version="1.2.0")
```

This:
- Makes the schema snapshot of the diagrams (section 160) again from the CREATE
  statements, with the MariaDB SQL language server's binary `mariadb-lsp`. **The
  release fails without the binary, or when a statement of the development
  script cannot be parsed** — fix the statement it names and try again.
- Inlines any `SOURCE` breakout files and writes the full snapshot
  `releases/versions/<schema>_1.1.0.sql`.
- If a previous release exists, creates the update script
  `releases/updates/<schema>_<prev>_to_1.1.0.sql` from the template, **empty**
  except for what `msm.edit_schema` / `msm.drop_schema_object` kept in the
  pending `development/<schema>_update_next.sql` (moved in; the pending script
  starts over).
- Fills the update script's section 280 with the drops of the REST endpoints,
  schemas, auth app links and services the previous release's section 180
  created and this one's does not. A REST schema moved to another database gets
  `DROP REST SCHEMA IF EXISTS ... FROM SERVICE ... FOR SCHEMA <old>`. When the
  previous release has REST statements this needs a current `mariadb-lsp`.
- Bumps the development version in `_next.sql` to `next_version` (1.2.0).

Semver validation: `version` must be ≥ the last released version, and
`next_version` must be greater than `version` (unless
`allow_to_stay_on_same_version` is set). The **first** release has no update
script.

## 2. FILL the update script — the step everyone forgets

`prepare_release` only creates the update script; it does **not** know how to
migrate data/structure. Even where `msm.edit_schema` filled it, check it: it
holds only the changes made through msm, never hand edits or data backfills.
Write the migration from the previous release to this one into its sections,
using `msm.set_section_sql_content(file_path, section_id, sql_content)`.
Statements already in 240/260 came from msm (each under a
`-- msm.editSchema: ...` comment): keep them, add the data steps they need
between them (a backfill before a foreign key on a new `NOT NULL` column), and
add the migration for every change made by hand, in the order the changes need.

- **Section 240 — non-idempotent changes + drops.** `ALTER TABLE`, new
  `CREATE TABLE` / `CREATE SEQUENCE`, data backfill (`UPDATE`/`INSERT`), any
  `DROP` of objects that would block a table change, and `DROP ... IF EXISTS`
  of every table, SEQUENCE, VIEW, TRIGGER and EVENT the new version no longer
  has — but **not** of a PROCEDURE or FUNCTION (that fails here, error 1357:
  use 260). Order matters — these are largely irreversible. This becomes a
  stored-procedure body in the deployment script, so write plain
  `;`-terminated statements, **no `DELIMITER`**; use dynamic SQL
  (`PREPARE`/`EXECUTE`) for conditional DDL. Do not re-create views, routines,
  triggers or events here.

  ```sql
  ALTER TABLE `notes-app`.`note` ADD COLUMN `created_at` DATETIME;
  UPDATE `notes-app`.`note` SET `created_at` = NOW() WHERE `created_at` IS NULL;
  ```

  `msm.deploy_schema` runs each **top-level** `ALTER TABLE` of 240 online (see
  `mariadb-schema-management-deploy`). So write plain ALTERs, one per table
  where you can, **without** `ALGORITHM` / `LOCK` / `ONLINE` / `IGNORE` /
  `IF EXISTS`: an ALTER with any of them, one that changes partitioning, one
  nested in `IF`/`BEGIN`, and every ALTER of a 240 body with a top-level
  `DECLARE` run as written, possibly blocking the table.

- **Section 260 — removed PROCEDUREs and FUNCTIONs only.** `DROP PROCEDURE IF
  EXISTS` / `DROP FUNCTION IF EXISTS` for each routine the new version no
  longer has. Emitted at top level, so plain `;`-terminated statements. It runs
  on **every** deployment of this or a later version, fresh installs too,
  after the table changes and before the target's section 150 — hence
  `IF EXISTS`, and a routine added again in a later version is re-created by
  that version's 150.

  ```sql
  DROP PROCEDURE IF EXISTS `notes-app`.`add_note`;
  ```

- **No section 250.** New and changed VIEWs / routines / triggers / events
  belong in the dev script's section 150. The deployment script runs the
  target version's full section 150 on every deployment, after all table
  changes, so they reach upgraded schemas without any per-version statement.
  A *removed* object is the one change 150 cannot express — drop it in 240, or
  in 260 for a routine. An update script made by an older msm still has a 250:
  leave it empty, it is never deployed.
- **Section 270 — revoked privileges and dropped roles only.** `REVOKE` /
  `DROP ROLE` for what the new version no longer has (stored-procedure body →
  plain `;`, no `DELIMITER`). New roles and `GRANT`s belong in the dev script's
  section 170, which also runs on every deployment, after the 270 steps.
  **Never `GRANT` in 270**: on an upgrade it runs before 170 creates a role that
  is new in this version, and the deployment fails with error 1133.
- **Section 280 — removed REST endpoints; check what msm wrote.**
  `msm.prepare_release` generates it (see above); review it alongside 240 and
  270 and edit it only if it is wrong. Top level, like 180.
- **Sections 230 / 290 — update helpers** (`msm_`-prefixed) if the migration
  needs temporary routines; drop them in 290, and put **nothing else** there.
  Every update script's 290 runs at the very end of every later deployment,
  after the target's 150, so a routine DROP in 290 would remove a routine a
  later version adds again. An update script made by an older msm (it has a
  250 and no 260) may hold such a DROP in 290; when a later version brings the
  routine back, move the DROP into a Section 260 by hand, banner included (copy
  it from a new update script: `msm.set_section_sql_content` refuses a section
  the file lacks).

Write the migration to match exactly what changed in the **tables** between the
previous version snapshot and this one: an upgraded schema must end with the
same tables as a fresh install of the new version. If a section has no changes,
leave it empty.

## 3. Generate the deployment script

Only after the update script is filled:

```text
msm.generate_deployment_script(version="1.1.0")
    → releases/deployment/<schema>_deployment_1.1.0.sql
```

What it produces:
- For the **first** release, the deployment script is just the version snapshot.
- Otherwise it is a self-contained script that **either creates fresh or upgrades
  any prior released version** to the target: it builds `msm_create_<target>()`
  from section 140, an `msm_update_<from>_to_<to>()` from **each** update script's
  section 240, an `msm_create_or_update()` dispatcher that reads
  `msm_schema_version` and applies the right path, then every update script's
  260 (removed routines), the target's idempotent objects (150) and diagrams
  (160), authorization (`msm_auth_*`: the 270 steps, then the target's 170),
  the REST drops of every update script's 280 (in the deployment script's
  section 380; a drop of something the target defines again is commented out,
  so its endpoints keep their ids), then the target's REST endpoints (180), and
  finally the 290 helper removals, drops all `msm_`
  procedures and stamps the new version. An update script's section 250, where
  an old one has it, is not included.

Because it embeds the update sections, generating **before** filling them yields
a script that can create fresh but cannot correctly upgrade older installs. Every
gap between consecutive released versions needs a filled update script for the
upgrade chain to be complete.

Deployment scripts are **generated artifacts** — never hand-edit; re-generate.

## Next

Deploy the release onto a server: `mariadb-schema-management-deploy`.

## See Also

- `mariadb-schema-management` — lifecycle overview and full section model.
- `mariadb-schema-management-develop` — the development script the snapshot comes from.
- `mariadb-schema-management-deploy` — running the deployment script on a server.
- `mariadb-alter-table` — the DDL for section 240.
- `mariadb-grant` — new grants, in the dev script's section 170; `mariadb-revoke` — revoked privileges, in section 270.
