---
order: 9
slug: mysql-to-mariadb-migration
title: "Migrate a MySQL database to MariaDB"
description: >-
  Drive the MySQL-to-MariaDB Migrator from the agent — choose a mode, write a
  configuration that will not be refused, plan it, run it, and verify the
  result. Rehearsed on two throwaway servers before it touches anything real.
level: advanced
duration: "60 min"
area: migration
tools: ["migrator.set_config", "migrator.plan", "migrator.run", "migrator.resume", "sandbox.deploy"]
skills: ["mariadb-migrator", "mysql-to-mariadb"]
path_label: "Build an API, Step 2"
prerequisites:
  - "**Linux or macOS.** The migration tooling is a POSIX shell program and is not available on Windows."
  - "The tooling installed: `mariadb-shell -- mcp setup --installMigrator`, then **restart the MCP server** — the tools only register on the next start."
  - "`mariadb` and `mariadb-dump` on the server's `PATH`. `pv` should be there too."
  - "Both the source and the target as **configured MCP connections**."
---

The MySQL-to-MariaDB Migrator is a standalone program — a Python orchestrator
driving a directory of shell scripts — that copies databases from a MySQL source
to a MariaDB target. The four `migrator.*` tools configure it and drive it.

Getting the *configuration* right is most of the work. A wrong one is refused
outright, which is good; a plausible-but-incomplete one fails deep inside the
dump step, which is not.

<div class="callout callout--warn" markdown="1">
**If you cannot see `migrator.set_config`, the tooling is not installed.** The
server advertises no `migrator.*` tools at all rather than four tools whose every
call would fail. Install with
`mariadb-shell -- mcp setup --installMigrator` and **restart the server** — the
change takes effect on the next start, not the current one.
</div>

## Rehearse on two sandboxes first

Never learn a migration tool on the database you need. The sandbox machinery can
stand up a **MySQL** instance as well as a MariaDB one, so the whole rehearsal
fits on one laptop:

<div class="prompt" markdown="1">
*Deploy a MySQL sandbox on port 3307 and a MariaDB sandbox on port 3308. Put a
small but realistic schema in the MySQL one — a few tables with foreign keys, a
view, a stored procedure and a trigger — and seed it with data. Then confirm both
show up in `db.list_connections`.*
</div>

`sandbox.vendor(port=3307)` will tell you which is which. Both are registered
with the MCP server automatically, which matters for the next step.

## Choose a mode

Pass the mode to `set_config` (as the file's default) **and** to `plan`/`run`.
The per-call one wins, so keep them the same.

| Mode | Type | What it does | Pick it when |
| --- | --- | --- | --- |
| `one_step` | offline | `mysqldump` piped straight into the target client, tables sequentially. | **The default choice.** Start here unless something below applies. |
| `two_step` | offline | Schema-only dump, then parallel data load via `mariadb-mtk`, then triggers, routines and events. | Large databases *and* `mariadb-mtk` installed — it is **not** bundled. |
| `staged` | offline | Per-database compressed dumps to disk with a SHA-256 manifest, then a separate load. | The dump must land on disk first, or you want checksums. **Needs bash 4.** |
| `binlog` | online | Consistent snapshot with binlog coordinates, then MariaDB replicates from the MySQL binary log. | Low-downtime cutover. Needs **MySQL 8.0+**, `binlog_format=ROW`, and **no JSON columns**. |

There are two further modes, `inplace` and `replace_slave`, that replace MySQL on
the source host itself over SSH. **Do not pick them.** They are excluded from the
tooling's own menu and documented for advanced scripting only.

## Write a configuration that will not be refused

`migrator.set_config` writes the tooling's `config/migration.yaml`. Two rules are
enforced by *refusing the configuration* rather than by failing later, and both
are there to stop an agent inventing infrastructure or leaking a secret.

**Rule 1 — every account you name must be a configured connection.** Each account
key is paired with its side's host and port to compose a URI, which then has to
resolve against `db.list_connections`:

| Account key | Resolved as |
| --- | --- |
| `SRC_ADMIN_USER`, `SRC_USER` | `<user>@<SRC_HOST>:<SRC_PORT>` |
| `TGT_ADMIN_USER`, `TGT_USER` | `<user>@<TGT_HOST>:<TGT_PORT>` |
| `REPL_USER` | `<user>@<SRC_HOST>:<SRC_PORT>` — the replication user lives on the **source** |

<div class="callout callout--warn" markdown="1">
**Always set `SRC_PORT` and `TGT_PORT` explicitly.** The port is half of the URI
the password is looked up under. Omit it and it reads as 3306 — so on any other
port the lookup silently finds nothing and the run fails much later, somewhere
that does not mention ports.
</div>

**Rule 2 — you can never set a password.** `SRC_PASS`, `SRC_ADMIN_PASS`,
`TGT_PASS`, `TGT_ADMIN_PASS` and `REPL_PASS` are **refused** if you give them a
value. Set the user, host and port; the password is read from the shell's secret
store at the moment the migration runs. The call returns a `passwords_from` map
telling you which connection each will come from — never the secret itself.

Values are strings; numbers and booleans are converted for you, and a list or a
dict is refused outright.

A complete `one_step` configuration:

{% raw %}
```text
migrator.set_config(
    mode="one_step",
    env={
        # Source — must resolve to the configured connection root@127.0.0.1:3307
        "SRC_HOST": "127.0.0.1",
        "SRC_PORT": "3307",
        "SRC_ADMIN_USER": "root",
        "SRC_USER": "root",
        "SRC_DBS": "shop,billing",
        "SRC_SSL_MODE": "DISABLED",

        # Target — root@127.0.0.1:3308
        "TGT_HOST": "127.0.0.1",
        "TGT_PORT": "3308",
        "TGT_ADMIN_USER": "root",
        "TGT_USER": "root",

        "MARIADB_DUMP_BIN": "/usr/local/mysql/bin/mysqldump",
        "ALLOW_ROOT_USERS": "1",
        "MIGRATE_APP_USERS": "0",
    })
```
{% endraw %}

Per-mode extras: `one_step`, `two_step` and `binlog` need `SRC_DB` (one database)
or `SRC_DBS` (comma-separated); `binlog` also needs `REPL_USER`; `staged` needs
`STAGED_PHASE` and, for `load_only`, `STAGED_DUMP_DIR`.

## Plan before you run

```text
migrator.plan(mode="one_step")
```

`plan` resolves the step list and validates the configuration. It **executes
nothing** and does not need a reachable server, which makes it free to run as
often as you like. Read the step list — it is the contract for what `run` will
do.

<div class="prompt" markdown="1">
*Plan the migration and walk me through what each step will do to the source and
to the target, before we run anything.*
</div>

## Run it

```text
migrator.run(mode="one_step")
```

<div class="callout callout--warn" markdown="1">
**The rule that silently produces a false success.** The orchestrator is
resume-safe: if `out` points at a directory that already holds a `state.json`
from an earlier run, the new run reports every step `SKIPPED`, **exits 0, and
migrates nothing**.

So: **omit `out` for every new migration.** A fresh
`artifacts/<command>_<mode>_<timestamp>` directory is chosen for you. Pass `out`
only to `migrator.resume`.

And **never trust `succeeded` on its own** — check that every step in the report
says `DONE`. A run of all-`SKIPPED` steps is a "success" that did nothing.
</div>

`out` is always relative to the install directory; an absolute path is refused.
Every invocation gets a closed stdin, so an incomplete configuration fails saying
what is missing rather than hanging on a prompt.

## Resume a failed run

```text
migrator.resume(mode="one_step", out="artifacts/migrate_one_step_20260911T101500")
```

`resume` continues from the `state.json` in that run's directory — the one case
where `out` is required. Steps already marked `DONE` are skipped, and the run
picks up at the first one that is not.

## Verify on the target

The migrator's report is a claim. Verification is a `db.execute_sql` against the
target — and this is where the agent earns its keep, because it can check
everything rather than the two tables you would have thought to check:

<div class="prompt" markdown="1">
*Connect to the target and verify the migration: every table from the source
exists with the same row count, every view, routine and trigger came across, the
foreign keys are all there, and no table lost its primary key. Show me a table of
source vs. target counts and flag any row that does not match.*
</div>

Things worth checking explicitly, because they are what actually differs:

- **Row counts per table**, source against target. `COUNT(*)`, not `TABLE_ROWS`.
- **Views, stored routines, triggers and events** — these travel separately from
  data in several modes, and are the usual casualty.
- **Character sets and collations.** MySQL's `utf8mb4_0900_ai_ci` does not exist
  in MariaDB; the closest equivalent is `utf8mb4_uca1400_ai_ci`. The
  `mysql-to-mariadb` skill covers the substitutions.
- **`JSON` columns.** MySQL's `JSON` is a native binary type; MariaDB's is a
  `LONGTEXT` alias with a check constraint. Data survives, but anything relying
  on MySQL's internal ordering does not — and the `binlog` mode refuses JSON
  columns entirely.
- **Accounts and grants**, if you set `MIGRATE_APP_USERS`.

## Then read the application side

The data being across is half the job. The `mysql-to-mariadb` skill is the other
half — what changes for the *application*: connector differences, SQL mode
defaults, functions that behave differently, and the features MariaDB has that
you can now use.

<div class="prompt" markdown="1">
*Now review this application's SQL and connector code against MariaDB. What will
break, what will behave differently, and what could be simplified using something
MariaDB has that MySQL does not?*
</div>

<h2 class="no-step" id="what-you-built">What you learned</h2>

- The tools only exist once the tooling is installed **and the server is
  restarted**. Linux and macOS only.
- Configuration is refused, not deferred: every account must be a configured
  connection, `SRC_PORT`/`TGT_PORT` must be explicit, and passwords can never be
  set by you.
- `plan` is free and executes nothing — run it first, every time.
- **Omit `out` on a new run.** Reusing a directory with a `state.json` skips
  everything and exits 0. Check every step says `DONE`, not just `succeeded`.
- Verify on the target with queries, not by reading the report.

**Where to go next**

- [Version the migrated schema with MSM](../versioned-schema-with-msm/) — put the
  schema you just inherited under version control before you change it.
- [Diagnose a slow query](../diagnose-a-slow-query/) — plans differ after a
  migration; this is when you find out.
