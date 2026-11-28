---
layout: page
title: MCP Tool Reference
subtitle: >-
  Every tool the mariadb-shell MCP server exposes, what it takes, and the
  behaviour that is not obvious from the name.
permalink: /mcp-tools/
description: Reference for the mariadb-shell MCP server tools — db.*, msm.*, sandbox.*, util.*, task.*, sql.* and the optional migrator.* group.
---

The server exposes **{{ site.tool_count }} tools in six groups**, plus an optional seventh
that only appears when the migration tooling is installed.

<div class="table-wrap" markdown="1">

| Group | Tools | What they do |
| --- | --- | --- |
| [`db.*`](#db--connections-and-sql) | 8 | List connections and schemas, describe objects, run SQL |
| [`msm.*`](#msm--schema-management) | 23 | Versioned schema projects, releases, deployments |
| [`sandbox.*`](#sandbox--throwaway-servers) | 9 | List deployable server versions; deploy, start, stop and delete local instances |
| [`util.*`](#util--dumps-loads-and-copies) | 10 | Dump, load, export, import and copy data between servers, as background tasks; inspect a dump |
| [`task.*`](#util--dumps-loads-and-copies) | 3 | Follow, list and cancel those background tasks |
| [`sql.*`](#sql--check-outline-and-format-sql) | 3 | Check, outline and format SQL text with MariaDB's grammar — no server needed |
| [`migrator.*`](#migrator--mysql-to-mariadb) | 4 | MySQL-to-MariaDB migration — **optional, not counted above** |

</div>

A server in **multi-tenant mode** (`mcp setup --multiTenant=true`, mariadb-shell
26.10.0 and later) serves only the `db.*` group — 26.10.0 and 26.10.1 served
`msm.*` too. The other groups run local servers and long jobs, or read and write
files, on the server's own machine and are not offered to tenants.
The plugins' launchers start a single-tenant server, which serves every group.

<div class="callout" markdown="1">
Arguments below are named as the tools take them. `connection_id` always comes
from a prior `db.connect`. Anything taking a file path is subject to the
allowed-paths list — see [How It Works]({{ '/how-it-works/#paths' | relative_url }}).
</div>

## `db.*` — connections and SQL

<div class="table-wrap" markdown="1">

| Tool | Arguments | Notes |
| --- | --- | --- |
| `db.list_connections` | — | The configured connection URIs. Derived from the shell's secret store, so a sandbox's auto-registered connection appears here too. Call it first. |
| `db.connect` | `uri` | Opens and caches a connection, returns a `connection_id`. The URI is normalized before matching; a URI asking for *more* than was configured (a default schema, an option) is refused. |
| `db.list_schemas` | `connection_id` | Schemas visible to the account. A missing schema is usually privileges. |
| `db.list_objects` | `connection_id`, `schema_name`, `object_type="table"` | `table`, `view`, `procedure`, `function`, `trigger`, `event`. |
| `db.get_object_details` | `connection_id`, `schema_name`, `object_name`, `object_type="table"` | Structured detail — columns, keys, indexes, constraints — not a `CREATE` string. Call this before proposing any schema change. |
| `db.execute_sql` | `connection_id`, `sql`, `params=None` | One statement. Use it when you want rows back or need parameters. |
| `db.execute_sql_script` | `connection_id`, `sql_script=None`, `file_path=None`, `stop_on_error=True`, `limit=None`, `column_metadata=False` | Multi-statement, in order, on the connection's session. **Not a transaction, and a failed statement does not raise** — see the warning below. |
| `db.close` | `connection_id` | Closes it. Idle connections are reaped anyway, but close before deleting a sandbox. |

</div>

<div class="callout callout--warn" markdown="1">
**`db.execute_sql_script` runs the whole script on the connection's session,
but it is not a transaction.** State carries from one statement to the next —
`SET @var`, `USE`, a `START TRANSACTION` / `COMMIT` pair, the MariaDB REST
Service's `USE REST SERVICE` — just as it would typed into a client.

What it does not do is undo itself or raise. A failed statement comes back as an
entry with an `error` key, the script stops there (`stop_on_error=True`), and
everything before it has already taken effect. Check every entry before calling
a script done.

State is lost in one case only: a connection that sat idle long enough to be
closed is reopened before the script runs, and the first entry then carries
`session_restarted: true`. Whatever earlier calls left in the session —
variables, the current schema, an open transaction — is gone.
</div>

## `msm.*` — schema management

MariaDB Schema Management. See
[Tutorial 6]({{ '/tutorials/versioned-schema-with-msm/' | relative_url }}) for the
workflow and the section model. These are the 23 tools an agent gets; msm's
other tools (project settings, schema rename, online `ALTER TABLE`, structured
edits, …) serve the MariaDB VS Code extension only, which keeps clients with a tool limit (GitHub
Copilot takes 128) within it.

<div class="table-wrap" markdown="1">

| Tool | Arguments | Notes |
| --- | --- | --- |
| `msm.create_project` | `schema_name`, `target_path`, `copyright_holder`, `license`, `overwrite_existing`, … | Scaffolds `<schema>.msm.project/` and adds it to the project list. An unrecognized `license` name is rejected. |
| `msm.list_projects` | — | The projects of the project list an agent may work on, with each one's `development_version` and `last_released_version`. |
| `msm.get_project_information` | `schema_project_path` | Project metadata. |
| `msm.set_development_version` | `version`, `schema_project_path` | Sets the version in section 910 of the development script. |
| `msm.get_released_versions` | `schema_project_path` | Every released version. |
| `msm.get_last_released_version` | `schema_project_path` | The most recent release. |
| `msm.get_last_deployment_version` | `schema_project_path` | The most recent generated deployment script. |
| `msm.get_deployment_script_versions` | `schema_project_path` | All generated deployment scripts. |
| `msm.get_section_sql_content` | `file_path`, `section_id` | Read one section. |
| `msm.set_section_sql_content` | `file_path`, `section_id`, `sql_content` | Write one section. **Always edit sections through these two** so the banners are never corrupted — but change tables with `set_schema_statements`: a hand edit of section 140 after a release gets no `ALTER`. |
| `msm.set_schema_statements` | `statements`, `renames`, `dropped_columns`, `expect`, `replaces`, `base_hash`, `schema_project_path` | Takes plain SQL, one statement per item, no `DELIMITER` lines: `CREATE` and `DROP` of tables, sequences, views, routines, triggers and events (named without the schema) and of REST services, schemas, views, procedures and functions, mixed in one call and written all or nothing. `ALTER` and `RENAME` are refused. Adds, replaces or **changes** objects, each in the right section. A changed `CREATE TABLE` must be complete (a left-out column is dropped, a left-out table option removed; `AUTO_INCREMENT=n` is kept); after a release its `ALTER TABLE` is kept for the next update script. `renames` (`{table: {old: new}}`) keeps a renamed column's data; a drop that looks like a rename is refused until `renames` or `dropped_columns` (`{table: [column]}`) says which it is. `base_hash` is optional. An existing sequence is refused. A `DROP` (`DROP TABLE t, u` drops both; `IF EXISTS` skips what the project lacks) is kept for the next update script after a release; it is refused for an object another one needs. REST statements go into section 180 as `CREATE OR REPLACE` (`IF NOT EXISTS` is refused) and must name their service and schema (`ON SERVICE /svc SCHEMA /p`, `FROM SERVICE /svc SCHEMA /p`; relying on `USE REST` is refused); a REST `DROP` removes the item and what is on it, and the next release's section 280 drops it on servers. `replaces` renames a REST object. Each entry of the answer's `statements` has an `action`: `added`, `replaced`, `unchanged`, `dropped` or `skipped`; a refusal names the statement (`Statement 2 ...`). |
| `msm.list_schema_diagrams` | `schema_project_path` | The diagrams, and whether the schema snapshot is current. |
| `msm.get_schema_diagrams` | `schema_project_path`, `diagram` | The snapshot (with `source_hash`) and the diagram documents. |
| `msm.create_schema_diagram` | `diagram`, `tables`, `views`, `sequences`, `routines`, `events`, … | A new diagram, laid out: all tables by default, other objects when named. |
| `msm.layout_schema_diagram` | `diagram`, `tables`, …, `keep_placed=True` | Adds objects to a diagram and lays out the unplaced figures (`keep_placed=False`: all). |
| `msm.set_schema_diagram` | `document`, `schema_project_path` | Adds or replaces a diagram from an `msm-diagram/1` document. |
| `msm.rename_schema_diagram` | `diagram`, `new_name`, `schema_project_path` | Renames a diagram. |
| `msm.remove_schema_diagram` | `diagram`, `schema_project_path` | Removes a diagram. |
| `msm.prepare_release` | `version`, `next_version`, `schema_project_path`, … | Snapshots the development script and creates the update script, holding the statements `set_schema_statements` kept, plus the REST removals in section 280. |
| `msm.generate_deployment_script` | `version`, `schema_project_path`, `overwrite_existing` | Composes the create-or-upgrade artifact. Run **after** completing the update script. |
| `msm.deploy_schema` | `connection_id`, `version`, `schema_project_path`, `backup`, `backup_directory`, `online_alter` | Applies a version to a live server, running each upgrade `ALTER TABLE` online where the server allows. Needs an open `db.connect` connection. |
| `msm.list_live_schema_objects` | `connection_id`, `schema` | The objects of a schema on a server that `import_live_schema` can import, and the version msm deployed there. |
| `msm.import_live_schema` | `connection_id`, `schema`, `target_path`, `objects`, … | Creates a project from a schema on a server (no data, users or grants), as a background task — follow it with `task.get`. |

</div>

<div class="callout callout--warn" markdown="1">
**The ordering rule.** `prepare_release` → **complete the update script** (hand
edits and data backfills in section 240, removed routines in 260, revoked
privileges in 270; msm has already put in what `set_schema_statements`
kept) → `generate_deployment_script`. Generating before
that produces a script that creates the schema perfectly on an empty server and
**silently fails to upgrade** an existing install.
</div>

### The section model, in brief

<div class="table-wrap" markdown="1">

| Create script | Update script | Contents |
| --- | --- | --- |
| 130 | 230 | Helper routines, names prefixed `msm_` |
| **140** | **240** | **Non-idempotent: tables, base data — and in an update, all `ALTER`s, backfills and drops of removed objects** |
| **150** | 260 | **Idempotent: views, procedures, functions, triggers, events.** 260: only `DROP PROCEDURE/FUNCTION IF EXISTS` of removed routines |
| 160 | — | Schema snapshot and diagrams — written by msm, never by hand |
| 170 | 270 | Authorization — 170: `CREATE ROLE IF NOT EXISTS`, `GRANT`; 270: only `REVOKE`, `DROP ROLE` |
| 180 | 280 | Optional MariaDB REST Service endpoints (`CREATE OR REPLACE REST …`); 280 removes dropped ones and is filled by `prepare_release` |
| 190 | 290 | Removal of the `msm_` helpers |

</div>

Sections **140, 240, 170, 270** become the body of a stored procedure in the
generated script: plain `;`-terminated statements, **no `DELIMITER`**, dynamic SQL
for conditional DDL. Sections **130, 150, 160, 180, 230, 260, 280, 190, 290** are
emitted at top level and use `DELIMITER %%` for routine bodies.

The deployment script runs the target version's **150, 170 and 180 in full on
every deployment**, after the table changes, so new and changed views, routines,
roles, grants and endpoints reach upgraded schemas on their own. The update
script only carries what those can't express: table changes and drops (240),
removed routines (260), and `REVOKE` / `DROP ROLE` (270). Update scripts from an
older msm still have a 250; it is not deployed — leave it empty. Never `GRANT` in 270 — on an upgrade it runs before
170 creates a new role, and the deployment fails.

## `sandbox.*` — throwaway servers

See [Tutorial 4]({{ '/tutorials/sandbox-lifecycle/' | relative_url }}).

<div class="table-wrap" markdown="1">

| Tool | Arguments | Notes |
| --- | --- | --- |
| `sandbox.list_available_versions` | `series` | Versions `deploy` can be asked for. No argument: the newest patch of each series. `series="11.8"` or `"11"`: every release below it. Only packages built for this platform are listed, and anything listed can be deployed. |
| `sandbox.deploy` | `port`, `password`, `sandbox_dir`, `allow_root_from`, `server_id`, `ssl=False`, `server_version`, `mariadbd_path`, `mariadbd_options`, `timeout` | Creates and starts an instance, and **registers its connection with the MCP server**. Resolves a server from the `PATH`, then already-downloaded versions, then the published index — **no MariaDB Server need be installed**. `server_version` accepts `11.8.9`, `11.8` or `11`, and is refused together with `mariadbd_path`. |
| `sandbox.list_instances` | `port` | The instances in the default sandbox location, with `version` and `status` (`running` or `stopped`). Pass a `port` to check one instance cheaply. |
| `sandbox.start` | `port`, `sandbox_dir`, `mariadbd_path`, `timeout` | Restarts an existing instance with its data intact. |
| `sandbox.stop` | `port`, `sandbox_dir`, `password`, `timeout` | Graceful shutdown. Leave `password` empty: the root password stored at deploy time is used. |
| `sandbox.kill` | `port`, `sandbox_dir` | Forceful. The fallback when `stop` will not. |
| `sandbox.delete` | `port`, `sandbox_dir` | Removes the instance. **Refuses a running one** — stop or kill first. |
| `sandbox.vendor` | `port`, `sandbox_dir`, `mariadbd_path` | `MariaDB` or `MySQL`. The sandbox machinery can stand up either. |
| `sandbox.version` | `port`, `sandbox_dir`, `mariadbd_path` | The instance's server version. |

</div>

<div class="callout callout--warn" markdown="1">
**Three failure modes worth memorizing.** A deploy that **hangs** means the
sandbox directory is not on the allowed-paths list. A deploy that succeeds but
whose connection is refused means the **password was blank**. A deploy that fails
on TLS means `ssl: True` without `openssl` — the default of `False` is what you
want.
</div>

<div class="callout callout--warn" markdown="1">
**A downloaded server changes how you stop and restart it.** It is not on the
`PATH`, so `sandbox.start` needs the `mariadbd_path` the deploy reported, and
shutdown needs **`sandbox.kill`** — `sandbox.stop` takes no `mariadbdPath` and
cannot find the binary. The deploy message says so at the time.
</div>

Instances live in `~/.mariadb-shell/sandboxes/<port>/` on macOS and Linux, and
`%USERPROFILE%\MariaDB\mariadb-shell\sandboxes\<port>\` on Windows. Downloaded
servers live separately, one directory per version, under
`~/.local/share/mariadb-sandbox-server/` (`%LOCALAPPDATA%\Programs\mariadb-sandbox-server`
on Windows). Instances create a `root@'%'` account and listen on all interfaces,
so they are a development tool and not something to leave running on an untrusted
network.

## `util.*` — dumps, loads and copies

The shell's dump, load, export, import and copy utilities, as tools. **Use them
instead of piping `mariadb-dump` into another client** — the plugins' CLI guard
blocks that and points here. Offered only together with the `db.*` group, since
every one of them works on a connection from `db.connect`.

<div class="table-wrap" markdown="1">

| Tool | Arguments | Notes |
| --- | --- | --- |
| `util.dump_instance` | `connection_id`, `output_url`, `options=None` | The whole server. `output_url` is a directory that must not exist or be empty — or a file ending in `.mariadb.dump.zip`, for the dump as one ZIP file. |
| `util.dump_schemas` | `connection_id`, `schemas`, `output_url`, `options=None` | The named schemas. |
| `util.dump_tables` | `connection_id`, `schema`, `tables`, `output_url`, `options=None` | Tables and views of one schema. `tables=[]` with `{"all": true}` dumps every one. |
| `util.export_table` | `connection_id`, `table`, `output_url`, `options=None` | One table's rows to one file. `table` is `t` or `schema.t`. |
| `util.load_dump` | `connection_id`, `url`, `options=None`, `extraction_budget_mb` | Loads a dump made by any of the three dump tools, a directory or a `.mariadb.dump.zip`. **The server needs `local_infile` on.** |
| `util.inspect_dump` | `url`, `schema=None` | What a dump holds — kind, completeness, source, schemas and objects — without loading it. Local dumps only; answers directly, no task. |
| `util.import_table` | `connection_id`, `urls`, `options=None` | A file, or a list of files, into a table that **must already exist**. Wildcards `*` and `?` work. Needs `local_infile`. |
| `util.copy_instance` | `connection_id`, `target_connection_id`, `options=None` | Dumps from the source and loads into the target at once, **no files written**. The target must be another server with `local_infile` on. |
| `util.copy_schemas` | `connection_id`, `schemas`, `target_connection_id`, `options=None` | The same, for the named schemas. |
| `util.copy_tables` | `connection_id`, `schema`, `tables`, `target_connection_id`, `options=None` | The same, for tables of one schema. `{"schema": "other"}` loads them into another schema. |
| `task.get` | `task_id`, `since=0`, `wait_ms=0` | A task's `status`, stages, current `progress` (with `percent`, `throughput`, `eta_seconds`), the messages after `since`, `next_since`, and its `result` or `error` once it ended. `wait_ms` (at most 30000) waits for news instead of answering at once. |
| `task.list` | `task_type=None` | This client's tasks, oldest first, without their messages. |
| `task.cancel` | `task_id` | Interrupts the utility as Ctrl+C would; the task ends `cancelled`. |

</div>

**Every utility runs as a background task.** The tool returns a `task_id` at
once, with `status` `pending` or `running`; follow it with `task.get`,
passing the last `next_since` back as `since` to get only new messages, and
`wait_ms` to avoid a tight polling loop. A task ends `completed`, `failed` or
`cancelled`, and is kept for an hour after that (at most 100 of them). A client
can have **at most four tasks running** at once — a dump opens a session per
thread.

`options` takes the utility's own options with their camelCase names —
`{"threads": 8}`, `{"ddlOnly": true}`, `{"loadUsers": false}`. `session`,
`progressCallback` and `showProgress` are set by the tool and refused, and so is
`outputUrl` for `dump_schemas` and `dump_tables`: use `output_url`.

<div class="callout" markdown="1">
**Each task runs in a mariadb-shell process of its own**, logged in with the
URI and stored password of the `db.connect` connection. The password goes to
the process on stdin, never on its command line. The connection itself is not
locked, so the agent can keep running SQL on it while a dump runs. A load whose
process crashes is **resumed from its progress file**, up to three more times;
`task.cancel` on a load leaves that file too, so loading the same dump again
picks up where it stopped. Tasks are stopped when the MCP server ends.
</div>

Local paths in `output_url`, `url` and `urls`, and in file options such as
`progressFile`, must be on the allowed-paths list. A URL with another scheme
(`https://…`), or a prefix in an object storage bucket (`s3BucketName`,
`osBucketName`, `azureContainerName`), is not a local path and goes to the
utility unchecked.

## `sql.*` — check, outline and format SQL

The core of the [SQL language server]({{ '/how-it-works/#the-sql-language-server' | relative_url }}),
as tools: they run `mariadb-lsp` on SQL text with the MariaDB server's own
grammar. **Nothing is executed and no connection is needed**, so the agent can
check a script before it runs it — and this works in **every** harness, including
Codex and Pi, which have no language-server support of their own. mariadb-shell
26.10.3 and later.

<div class="table-wrap" markdown="1">

| Tool | Arguments | Notes |
| --- | --- | --- |
| `sql.check` | `sql` or `file_path`, `source_dir=None`, `sql_mode=None`, `delimiter=None`, `version_id=None`, `max_errors=100` | `valid`, `statements`, and per error its `start` (line, column), `message`, the failing `token` and the tokens the grammar `expected` there. |
| `sql.outline` | `sql` or `file_path`, `source_dir=None`, `sql_mode=None`, `delimiter=None`, `version_id=None` | Applies the `CREATE`/`ALTER`/`DROP`/`RENAME`/`USE` statements in order and lists what results: schemas, tables with columns, indexes, keys and checks, views, routines, triggers, events, sequences, REST objects. |
| `sql.format` | `sql` or `file_path`, `line_width=80`, `keyword_case="upper"`, `indent="2"`, `sql_mode=None`, `delimiter=None`, `version_id=None` | Returns the laid-out `sql`; **a file is not changed**. Statements that don't parse are left as they are, comments kept. |

</div>

Pass the SQL inline (`sql`) **or** as a `.sql` file (`file_path`, on the
allowed-paths list) — exactly one, at most 10 MB. `check` and `outline` follow
Schema Management's `SOURCE '<path>'[<start>:<end>];` directives, expanded by
the server with the same path checks as `db.execute_sql_script`, so an error in
an included section is reported in that file, at its line. Lines and columns
count from 1, as an editor shows them.

<div class="callout" markdown="1">
**The group appears only where `mariadb-lsp` is found** — the one
`mcp setup --lspPath=PATH` names, else the one next to the running
`mariadb-shell` (the release packages install it there), else the `PATH`, else
`~/.local/bin`. A shell from the native `.deb`/`.rpm` packages has none, and a
multi-tenant server never offers the group.
</div>

## `migrator.*` — MySQL to MariaDB

**Optional and not part of the {{ site.tool_count }}.** These four tools are registered only when
the migration tooling is installed
(`mariadb-shell -- mcp setup --installMigrator`, then restart the server). A
server with no install advertises none of them, rather than four tools whose
every call would fail. Linux and macOS only. See
[Tutorial 9]({{ '/tutorials/mysql-to-mariadb-migration/' | relative_url }}).

<div class="table-wrap" markdown="1">

| Tool | Arguments | Notes |
| --- | --- | --- |
| `migrator.set_config` | `mode`, `env`, `merge=False` | Writes `config/migration.yaml`. Only configured connections may be named; **passwords are refused**. |
| `migrator.plan` | `mode`, `out=None`, `timeout=3600` | Resolves the step list and validates the config. **Executes nothing.** |
| `migrator.run` | `mode`, `out=None`, `timeout=3600` | Performs the migration. **Omit `out`** on a new run. |
| `migrator.resume` | `mode`, `out`, `timeout=3600` | Continues a failed run from its `state.json`. `out` is required here. |

</div>

<div class="callout callout--warn" markdown="1">
**The false success.** The orchestrator is resume-safe. Point `out` at a
directory that already holds a `state.json` and the run reports every step
`SKIPPED`, **exits 0, and migrates nothing**. Omit `out` for every new migration,
pass it only to `resume`, and check that every step says `DONE` — never trust
`succeeded` on its own.
</div>

## Error messages you will meet

<div class="table-wrap" markdown="1">

| Message | Cause | Fix |
| --- | --- | --- |
| *not a configured connection* | The URI is not on the allow-list, or asks for more than was configured (a schema, an option). | `mariadb-shell -- mcp setup`, or drop the extra part from the URI. |
| A call that never returns | A path is not on the allowed-paths list, and the guard fell back to a prompt nothing can answer. | Add the directory with `mcp setup`. |
| *There is no object registered under name 'mcp'* | The shell cannot find its plugins — usually a relocated or broken config home. | Check `~/.mariadb-shell/plugins/`. |
| No `sql.*` tools at all | The server found no `mariadb-lsp`, runs in multi-tenant mode, or is older than 26.10.3. | Use a shell from the release packages, or point `mcp setup --lspPath` at a `mariadb-lsp`. |
| No `util.*` tools at all | The server does not serve the `db.*` group, or runs in multi-tenant mode. | Serve `db` too; a multi-tenant server never offers them. |
| *The MariaDB Shell binary to run the utility in was not found* | A `util.*` tool could not find `mariadb-shell` to run the task in. | Put `mariadb-shell` on the `PATH`. |
| *Already 4 tasks are running* | The client's limit of running `util.*` tasks. | Wait for one with `task.get`, or `task.cancel` one. |
| A load or copy fails on `local_infile` | The target server has `local_infile` off. | `SET GLOBAL local_infile = ON` on the target. |
| No `migrator.*` tools at all | The migration tooling is not installed, or the server has not been restarted since it was. | `mcp setup --installMigrator`, then restart. |
| *No module named 'pywintypes'* (Windows) | The Windows shell packages do not yet bundle pywin32. | `pip install pywin32` into the shell's bundled Python. |

</div>
