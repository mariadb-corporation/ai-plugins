---
name: mariadb-schema-management-deploy
description: "Deploy a MariaDB Schema Management (MSM) schema version onto a live server with msm.deploy_schema — running the generated deployment script over an open db.connect connection to create the schema fresh or upgrade any prior released version to the target, optionally taking a backup first, with the ALTER TABLE statements of an upgrade run online within the project's onlineAlter limits. Use when installing or upgrading an MSM-managed schema on a MariaDB server, applying a schema deployment/migration, tuning online ALTER TABLE for a deployment, or checking which versions are deployable. Read mariadb-schema-management first for the section model."
---

# MSM — Deploying a Schema Version

The final lifecycle step: apply a generated deployment script to a MariaDB
server. One script both **creates a fresh schema** and **upgrades any older
released version** to the target. Driven by `msm.*` + `db.*` tools of the
`mariadb-shell` MCP server. See `mariadb-schema-management` for the model.
Assume MariaDB 11.8.

## Prerequisite

The deployment script for the target version must already exist
(`releases/deployment/<schema>_deployment_<version>.sql`), i.e. the release was
prepared, its update script filled, and the deployment script generated — see
`mariadb-schema-management-release`. Check what is deployable with
`msm.get_deployment_script_versions`.

## Deploy

```text
1. conn = db.connect(uri="root@host:port")        # open a connection first
2. msm.deploy_schema(
       connection_id=conn,
       version="1.1.0",        # optional; defaults to the latest generated script
       backup=True,            # optional; dump an existing schema before upgrading
       backup_directory="...", # optional; where the backup is written
       online_alter={...},     # optional; this deployment's online ALTER limits
   )
```

`msm.deploy_schema` runs the deployment script on that connection. It requires an
open connection (that is why the tool is only available alongside the `db.*`
group). With `backup=True`, an existing schema is dumped first so a failed
upgrade can be restored.

## Create-or-upgrade semantics

The deployment script decides what to do from the target schema's state:

- **Empty / absent schema →** created fresh at the target version.
- **Existing MSM schema at an older released version →** upgraded by running each
  update step (the update scripts' 240) in sequence up to the target, then
  dropping the routines the update scripts' 260 remove, then applying the
  target's idempotent objects (150), authorization (the 270 steps, then 170) and
  REST endpoints (180).
- **Already at the target version →** nothing to change.

The `msm_schema_version` view is the source of truth for the installed version;
it is set to `0,0,0` while a create/upgrade is in progress. The script aborts
with a clear `SIGNAL` error when it cannot safely proceed:

- a non-MSM schema of the same name exists (no `msm_schema_version` view);
- the schema is stuck at `0,0,0` (a previous run failed or was interrupted;
  `msm.deploy_schema` reports that version `0.0.0` cannot be updated) — without
  `backup=True`, a failed upgrade leaves the schema in that state;
- the current version has no update path in this deployment script.

Inspect the project with `msm.get_last_released_version` /
`msm.get_released_versions` and `msm.get_deployment_script_versions` /
`msm.get_last_deployment_version` — all four read the project folder, not the
server. To see what a server has, query the view through the connection:
``db.execute_sql(connection_id=conn, sql="SELECT * FROM `<schema>`.`msm_schema_version`")``.

## Online ALTER TABLE

For an upgrade, `msm.deploy_schema` runs the update steps itself and each
top-level `ALTER TABLE` of a 240 the least disruptive way the server accepts:
`ALGORITHM=INSTANT`, then `NOCOPY`, `INPLACE` and `COPY` with `LOCK=NONE`, then
a Galera NBO where allowed, then `LOCK=SHARED` and `LOCK=EXCLUSIVE`. A step the
server refuses changes nothing; lock wait timeouts are retried. The scripts
keep plain ALTERs, so the same deployment script run without msm (e.g. the
`mariadb` client) runs them as plain, possibly blocking ALTERs, and a fresh
install is unaffected.

- **On by default.** The limits come from `onlineAlter` in `msm.project.json`
  — `enabled`, `maxRebuildBytes` (largest table for an INPLACE or COPY
  rebuild; default 10 GiB, `0` = never, `null` = no limit), `galeraMaxBytes`
  (default 256 MiB), `nboLock` (`SHARED` or `EXCLUSIVE` to allow a Galera NBO;
  off by default), `maxLockedBytes` (largest table for a step that blocks
  writes; default no limit), `lockWait` (seconds per attempt, default 5),
  `maxRetries` (default 10), and `tables: {<table>: {the same keys}}`. Read the
  defaults and what a table gets with `msm.get_online_alter_settings(table=)`
  (`msm.get_online_alter_defaults` without a project); change them with
  `msm.set_project_settings({"onlineAlter": {...}})`, which replaces the whole
  setting.
- **Per deployment:** `online_alter=` takes the same keys. The most specific
  value wins, and the deployment's over the project's at the same level, so
  `{"enabled": false}` runs every ALTER as written except of the tables the
  project's `tables` entries turn on.
- **When no allowed step can run an ALTER**, the deployment stops with
  `NeedsExternalToolError`: the statements before it have run and the schema
  stays at `0.0.0`. Use `backup=True` so it can be restored. On Galera an ALTER
  of a table over `galeraMaxBytes` that is not INSTANT stops this way unless
  `nboLock` is set, `galeraMaxBytes` raised or online ALTER turned off for it.

`msm.online_alter_table(connection_id, schema, table, spec, options=None)`
runs one such ALTER on a live table outside any deployment (`spec` is
everything after `ALTER TABLE <table>`, without `ALGORITHM`/`LOCK`). It starts
a task: follow it with `task.get` (a stage per step; `skipped` for refused or
limited steps), stop it with `task.cancel`. Its result's `method` is the step
that applied, or `NEEDS_EXTERNAL` with `applied: false` and nothing changed.
A change made this way is not in the project: an MSM-managed schema still
needs it in the development script and the next update script.

## Guidelines

- Deploy the **generated** script only; never a hand-edited deployment file.
- Use `backup=True` for production upgrades so a failure is recoverable.
- On large tables or Galera, check `msm.get_online_alter_settings` before an
  upgrade; set the limits that depend on the environment with `online_alter=`.
- Upgrades are only possible along the released-version chain — if a server is on
  a version with no update script leading toward the target, the deployment will
  refuse it. Ensure every release was prepared with its update script filled.
- Re-running the same version is safe (idempotent objects re-create cleanly; the
  create/upgrade dispatcher is version-guarded).

## See Also

- `mariadb-schema-management` — lifecycle overview and full section model.
- `mariadb-schema-management-release` — generating the deployment script this step runs.
- `mariadb-schema-management-develop` — the development script releases are cut from.
