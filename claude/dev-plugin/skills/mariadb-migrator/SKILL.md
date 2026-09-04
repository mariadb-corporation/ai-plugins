---
name: mariadb-migrator
description: "Migrate a MySQL database to MariaDB with the migrator.* tools of the mariadb-shell MCP server — choosing the execution mode, writing config/migration.yaml correctly with migrator.set_config (only configured connections may be named, and passwords are never written), then migrator.plan, migrator.run and migrator.resume, and verifying the result on the target. Use when asked to migrate/move/port a MySQL database or schema to MariaDB, to configure or run the MySQL-to-MariaDB migration tooling, or when a migration run failed and has to be diagnosed or resumed."
---

# MySQL → MariaDB Migration

The **MySQL-to-MariaDB Migrator** is a standalone program (a Python orchestrator
driving a directory of POSIX shell scripts) that copies databases from a MySQL
source to a MariaDB target. The `migrator.*` tools of the **`mariadb-shell` MCP
server** configure and drive it: you write its `config/migration.yaml`, then run
one of its modes and read its report.

**Two things are deliberately NOT yours to choose**, and both are enforced by
refusing the configuration rather than by failing later:

1. **Only servers that are already configured MCP connections may be named.**
2. **You can never set a password.** Each is read from the shell's secret store
   at the moment a migration runs.

Get the configuration right first — a wrong one is refused, and a *plausible but
incomplete* one produces a failed run deep in the dump step.

> **The one rule that silently produces a false success:** the orchestrator is
> **resume-safe**. If you point `out` at a directory that already holds a
> `state.json` from an earlier run, the new run reports every step `SKIPPED`,
> **exits 0, and migrates nothing**. Omit `out` for every new migration (a fresh
> `artifacts/<command>_<mode>_<timestamp>` is chosen for you) and pass it only to
> `migrator.resume`. And never trust `succeeded` alone — check that every step in
> the report says `DONE`.

## Preconditions

- **The tooling must be installed**, or the `migrator.*` tools are not registered
  at all — a server with no install advertises none of them rather than four
  tools whose every call would fail. Install with
  `mariadb-shell -- mcp setup --installMigrator`. **This takes effect on the next
  server start, not the current one**; if you cannot see `migrator.set_config`,
  that is why.
- **Not available on Windows.** The tooling is a POSIX shell program.
- **Both servers must be configured connections.** Start by calling
  `db.list_connections` and build the configuration out of what it returns. Do
  not invent a host: it will be refused.
- The `mariadb` client and `mariadb-dump` must be on the server's `PATH`, and
  **`pv` should be** (see Known defects).

## The four tools

| Tool | Purpose |
| --- | --- |
| `migrator.set_config(mode, env, merge=False)` | Write `config/migration.yaml`. Returns the path, the keys, the example's path, and which connection each account resolved to. |
| `migrator.plan(mode, out=None, timeout=3600)` | Resolve the step list for a mode and validate the configuration. **Executes nothing** and needs no reachable server. |
| `migrator.run(mode, out=None, timeout=3600)` | Perform the migration. **Changes the target**, and in some modes the source. |
| `migrator.resume(mode, out, timeout=3600)` | Continue a failed run from the `state.json` in that run's `out` directory. `out` is required here. |

`out` is always **relative to the install directory** (an absolute path is
refused). Every invocation gets a closed stdin, so an incomplete configuration
fails saying what is missing instead of hanging on a prompt.

## Step 1 — choose the mode

Pass the mode to `set_config` (as the file's default) **and** to `plan`/`run`;
the per-call one wins, so keep them the same.

| # | Mode id | Type | What it does | Pick it when |
| --- | --- | --- | --- | --- |
| 1 | `one_step` | offline | `mysqldump` piped straight into the target `mariadb` client, tables sequentially. | **The default choice.** Simplest and most predictable; start here unless something below applies. |
| 2 | `two_step` | offline | Schema-only dump, then parallel data load via `mariadb-mtk`, then triggers/routines/events. | Large databases *and* `mariadb-mtk` is installed. It is **not** bundled — without it this mode cannot run. |
| 3 | `staged` | offline | Per-database compressed dumps to disk with a SHA-256 manifest, then a separate load. Sub-phases `dump_and_load` / `dump_only` / `load_only`. | The dump must land on disk first — a network-restricted or deferred-load migration — or you want checksums. **Needs bash 4** (see Known defects). |
| 4 | `binlog` | online | Consistent snapshot with binlog coordinates, then MariaDB replicates from the MySQL binary log. | Low-downtime cutover. Requires a **MySQL 8.0+** source with `binlog_format=ROW` and **no JSON columns**. |
| — | `inplace`, `replace_slave` | — | Replace MySQL with MariaDB on the source host itself, over SSH. | **Do not pick these.** They are excluded from the tooling's own menu, need SSH access to the target host, and are documented for advanced scripting only. |

## Step 2 — write the configuration

`migrator.set_config` writes the tooling's `config/migration.yaml`, following its
own `config/migration.yaml.example` (the returned `example_path` is the full key
reference — read it when you need a key not listed here).

### The rules that get configurations refused

**Every account you name must be a configured connection.** The tooling's
accounts are paired with a side's host and port to compose a URI, and each has to
resolve against `db.list_connections`:

| Account key | Resolved as |
| --- | --- |
| `SRC_ADMIN_USER` | `<user>@<SRC_HOST>:<SRC_PORT>` |
| `SRC_USER` | `<user>@<SRC_HOST>:<SRC_PORT>` |
| `TGT_ADMIN_USER` | `<user>@<TGT_HOST>:<TGT_PORT>` |
| `TGT_USER` | `<user>@<TGT_HOST>:<TGT_PORT>` |
| `REPL_USER` | `<user>@<SRC_HOST>:<SRC_PORT>` — the replication user lives on the **source** |

- **Always set `SRC_PORT` and `TGT_PORT` explicitly.** They are half of the URI
  the password is looked up under. An omitted port is read as 3306, so on any
  other port the lookup silently finds nothing.
- **Naming a host with no account is refused too** (`SRC_HOST` with neither
  `SRC_ADMIN_USER` nor `SRC_USER`). There would be nothing to check.
- Validated on the **merged** result, so two `merge=True` calls cannot assemble a
  forbidden connection between them — and **validated again when a run starts**,
  so a connection removed with `mcp.setup` stops migrations already configured
  against it.

**Never set a password.** `SRC_PASS`, `SRC_ADMIN_PASS`, `TGT_PASS`,
`TGT_ADMIN_PASS` and `REPL_PASS` are **refused** if you give them a value. Set
the matching user/host/port fields and the password follows on its own. The
returned `passwords_from` tells you which connection each will be read from, and
never the secret itself.

**Values are strings.** Numbers and booleans are converted for you (a boolean
becomes the `"1"`/`"0"` the tooling reads). A list or a dict is refused — there
is no string it should silently become.

### Keys each mode requires

Beyond the connection fields above:

| Mode | Also required |
| --- | --- |
| `one_step`, `two_step`, `binlog` | `SRC_DB` (one database) **or** `SRC_DBS` (comma-separated) |
| `binlog` | `REPL_USER` (and its configured connection on the source) |
| `staged` | `STAGED_PHASE` (`dump_and_load` default / `dump_only` / `load_only`); `SRC_DB`/`SRC_DBS` unless `load_only`; `STAGED_DUMP_DIR` when `load_only` |

Useful optional keys: `SRC_SSL_MODE` (`DISABLED` | `REQUIRED` | `VERIFY_CA` |
`VERIFY_IDENTITY`), `ANALYZE_TARGET` (refresh optimizer statistics after the
load, default on), `MIGRATE_APP_USERS` + `APP_USER_DEFAULT_PASSWORD` +
`APP_USER_PWD_EXPIRE`, `ALLOW_TARGET_DB_OVERWRITE`, and the `STAGED_*` family
(`STAGED_COMPRESS`, `STAGED_PARALLEL`, `STAGED_LOAD_PARALLEL`, `STAGED_PV`).

### A complete mode 1 configuration

```text
migrator.set_config(
    mode="one_step",
    env={
        # Source — a configured connection: root@127.0.0.1:3307
        "SRC_HOST": "127.0.0.1",
        "SRC_PORT": "3307",
        "SRC_ADMIN_USER": "root",
        "SRC_USER": "root",
        "SRC_DBS": "shop,billing",
        "SRC_SSL_MODE": "DISABLED",
        # Target — a configured connection: root@127.0.0.1:3308
        "TGT_HOST": "127.0.0.1",
        "TGT_PORT": "3308",
        "TGT_ADMIN_USER": "root",
        "TGT_USER": "root",
        # See Known defects — both are needed far more often than not.
        "MARIADB_DUMP_BIN": "/usr/local/mysql/bin/mysqldump",
        "ALLOW_ROOT_USERS": "1",
        "MIGRATE_APP_USERS": "0",
        "ANALYZE_TARGET": "1",
    },
)
```

No `*_PASS` key appears. Check the returned `connections` mapping: every account
you named must be there, pointing at the connection you expected.

## Step 3 — plan, then run

```text
1. db.list_connections()                    # what may be named at all
2. migrator.set_config(mode=..., env=...)   # refused unless it is right
3. migrator.plan(mode=...)                  # executes nothing; validates
4. migrator.run(mode=...)                   # omit `out` — fresh directory
5. verify on the target with the db.* tools
```

**Always `plan` first.** It costs nothing, reaches no server, and tells you
whether the mode and the configuration are complete — including which steps the
run will perform.

**Then check a run three ways**, because any one of them can pass while the
migration did nothing:

1. `succeeded is True` and `exit_code == 0`;
2. **every step in `report` has `status: "DONE"`** — all `SKIPPED` means a reused
   `out` directory, and the run exited 0;
3. the data is actually on the target — query it.

The run returns `out_dir`, `install_dir` and the parsed `report`; the run's own
`report.json` and `run.log` live in `<install_dir>/<out_dir>` and are the real
diagnosis when a step fails. `stdout`/`stderr` are only the tail.

The default timeout is one hour. A large migration can outrun it; the artifacts
directory is returned either way, so a run that is stopped can be picked up with
`migrator.resume(mode=..., out=<the same out_dir>)`.

## Step 4 — verify on the target

Open the target with `db.connect` and confirm what arrived — do not report a
migration as successful on the tooling's exit code alone:

- `db.list_schemas` — the migrated schemas are present.
- `db.list_objects(schema_name=..., object_type=...)` for `table`, `view`,
  `trigger`, `procedure`, `function`, `event` — every object type the dump
  carries, not just the tables.
- `db.get_object_details` — foreign keys survived (the constraint name is inside
  `reference_mapping["constraint"]`, as `<schema>.<name>`).
- `db.execute_sql` — row counts, and spot-check real values.

## Known defects to configure around

These are defects in the tooling as released, not in your configuration. Each has
a configuration answer; set it up front rather than discovering it from a failed
run.

| Symptom | Cause | What to set |
| --- | --- | --- |
| `mariadb-dump: Couldn't execute 'SHOW PACKAGE STATUS ...' (1064)` at the dump step | The default `mariadb-dump` cannot dump a MySQL 8.4+ source — it issues a MariaDB-only statement. The preflight **warns and then fails anyway**, so heed its warning. | `MARIADB_DUMP_BIN` = an upstream `mysqldump` (the one beside the source's own `mysqld`) |
| `line 226: SRC_SSL_ARGS[@]: unbound variable` | Expanding an empty array under `set -u` errors on bash before 4.4 (macOS ships 3.2). Hit whenever the SSL args come out empty. | `MARIADB_DUMP_BIN` as above — the upstream branch always composes `--ssl-mode=<value>`, so the array is never empty |
| The run copied everything correctly but reports `FAILED` with exit **143**, after a 60-second stall | With no `pv`, mode 1 falls back to a heartbeat it kills from an `EXIT` trap; on bash 3.2 the trap's status becomes the script's. | Install `pv` (`brew install pv` / `apt-get install pv`). It is documented as optional, but the fallback is broken |
| `declare: -A: invalid option` in `25_staged_dump.sh` | Mode 3 needs bash 4.0 (`declare -A`) and 4.3 (`wait -n`). `STAGED_PARALLEL=1` does not help. | Nothing — **mode 3 cannot run on bash 3.2.** Install bash 4+, or use mode 1 |
| `SRC/TGT admin and migration users must not be root` | A deliberate safety policy, not a bug. | `ALLOW_ROOT_USERS` = `"1"`, only when migrating as `root` is genuinely intended |
| `ERROR: Target DB already exists` (exit 8) | The target already holds a database of that name — a re-run, or a real collision. | Drop it on the target, or `ALLOW_TARGET_DB_OVERWRITE` = `"1"` if overwriting is intended |
| Mode 2 fails looking for a data-transfer engine | `mariadb-mtk` is not bundled with the tooling. | Install it and put it on `PATH`, or set `SQLINESDATA_BIN` — otherwise use mode 1 |

## Failure playbook

| Message | Meaning | Fix |
| --- | --- | --- |
| `... is not a connection configured with mcp.setup` | An account you named is not a configured connection. | `db.list_connections`, then name one of those — or have the connection added with `mcp.setup --addConnection`. |
| `source names SRC_HOST but none of SRC_ADMIN_USER, SRC_USER` | A host with no account to check it by. | Add the account key for that side. |
| `SRC_ADMIN_PASS cannot be set here` | You tried to write a password. | Remove it; set user/host/port and let it resolve. |
| `The MySQL-to-MariaDB migration tooling is not installed` | No install, or the server started before one. | `mcp setup --installMigrator`, then **restart the server**. |
| `Missing required env vars for mode '<mode>': ...` | The configuration is incomplete for that mode. | Add the keys; re-read the mode table above. |
| `'out' must be relative to the install directory` | An absolute `out`. | Omit `out`, or pass a relative path. |
| `migrator.<command> did not finish within <n>s` | The invocation was stopped at its timeout. | Read the artifacts directory, then `migrator.resume` with that same `out`. |
| Every step `SKIPPED`, exit 0 | A reused `out` directory holding an old `state.json`. | Re-run with `out` omitted. |

## Guidelines

- **Build the configuration from `db.list_connections`, never from what the user
  typed.** A host they name that is not configured cannot be migrated to or
  from, and saying so early is more useful than a refused `set_config`.
- **`plan` before every `run`**, including after a `merge=True` edit.
- **Use `merge=True` for a correction**, not a fresh full write — you keep the
  keys you got right, and the merged result is validated as a whole anyway.
- **Report what the report says.** If a step failed, name the step and quote from
  its `output_tail`; the tooling's own diagnosis is almost always the answer.
- Modes 1, 2 and 3 are **offline**: the source is read, not changed, but the
  target is written. Mode 4 leaves replication running. Never run any of them
  against a production target without the user's explicit go-ahead.

## See Also

- `mariadb-schema-management` — versioned schema lifecycle, for a schema that
  will keep evolving after it has been migrated.
- `mariadb-schema-create-script` — authoring a single MariaDB create script.
- `mysql-to-mariadb` — MySQL/MariaDB dialect and feature differences, for fixing
  up SQL that the migration carried across verbatim.
