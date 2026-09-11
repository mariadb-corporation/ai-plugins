---
order: 2
slug: run-sql-and-scripts
title: "Run SQL and SQL scripts with the db.* tools"
description: >-
  Open a connection, run a single statement, run a whole script, and read a
  result set back. Covers the one distinction that causes most db.* surprises —
  execute_sql runs on your session, execute_sql_script does not.
level: beginner
duration: "15 min"
area: sql
tools: ["db.list_connections", "db.connect", "db.execute_sql", "db.execute_sql_script", "db.close"]
skills: ["mariadb-select", "mariadb-insert", "mariadb-transactions"]
path_label: "First Steps, Step 2"
prerequisites:
  - "[Tutorial 1](../notes-app-sandbox/), or any configured MariaDB connection."
  - "A sandbox on port 3310 with the `notes_app` schema, if you want to follow along exactly."
---

Six of the eight `db.*` tools exist to get SQL onto a server and results back.
This tutorial is about picking the right one, because the difference between two
of them is the single most common source of confusion — and it is not obvious
from their names.

## Find out what you are allowed to connect to

The agent cannot invent a host. Every connection has to already be on the MCP
server's allow-list, and the first call in almost every session is the one that
asks what is on it:

```text
db.list_connections()
  → ["root@127.0.0.1:3310", "app_ro@db.internal:3306"]
```

<div class="callout" markdown="1">
This list is **derived from the shell's secret store**, not from a registry of
its own — `db.list_connections` reports the connections whose passwords are
stored. Two consequences worth knowing: a connection registered by
`sandbox.deploy` shows up here without you configuring anything, and an
unreadable secret store makes *every* connection look unconfigured, which reads
like a broken install when it is really a credential-store problem.
</div>

## Open a connection

```text
db.connect(uri="root@127.0.0.1:3310")
  → connection_id
```

The URI is matched against the allow-list after normalization, so you have some
freedom in how you spell it. All of these open the same stored
`root@127.0.0.1:3310`:

| Spelling | Accepted |
| --- | --- |
| `root@127.0.0.1:3310` | yes — the canonical form |
| `mariadb://root@127.0.0.1:3310` | yes — the scheme is folded away |
| `mysql://root@127.0.0.1:3310` | yes |
| `root@127.0.0.1` | yes, if 3306 is the stored port |
| `root:secret@127.0.0.1:3310` | yes — an inline password is ignored, the stored one is used |
| `root@127.0.0.1:3310/notes_app` | **no** |
| `root@127.0.0.1:3310?ssl-mode=REQUIRED` | **no** |

The last two are refused **deliberately**. They ask for *more* than was
configured — a default schema, a TLS requirement — and rather than silently
handing back a connection that drops what you asked for, the server says no. If
you want a default schema, issue a `USE` statement on the open connection.

## Run one statement — `db.execute_sql`

Use this for anything whose result you want, and anything that depends on
session state.

```text
db.execute_sql(connection_id="…", sql="SELECT id, email FROM notes_app.`user` LIMIT 5")
```

Parameters are passed separately rather than formatted into the string, which is
both safer and faster on repeated calls:

```text
db.execute_sql(
  connection_id="…",
  sql="SELECT * FROM notes_app.note WHERE user_id = ? AND created_at > ?",
  params=["01920e5c-…", "2026-01-01"])
```

<div class="prompt" markdown="1">
*Insert three users into `notes_app.user`, then show me every user with the
number of notes they have written, highest first.*
</div>

The agent will reach for the `mariadb-select` and `mariadb-aggregate-functions`
skills here. Watch for `GROUP_CONCAT` if you ask for the note titles as well —
the skill knows it truncates silently at `group_concat_max_len`, which is the
kind of detail that produces a bug report six months later.

## Run a whole file — `db.execute_sql_script`

Use this for create scripts, seed data, migrations — anything multi-statement
where you do not need the results.

```text
db.execute_sql_script(connection_id="…", file_path="/abs/path/notes_app.sql")
db.execute_sql_script(connection_id="…", sql_script="CREATE …; INSERT …; …")
```

Either a `file_path` or an inline `sql_script`. Two constraints:

- **`file_path` must be inside an allowed path.** Outside it, the call is
  refused and the agent's natural fallback is to send the same SQL inline.
- **Each statement runs in a fresh session.** This is the important one.

<div class="callout callout--warn" markdown="1">
**The fresh-session rule, and what it breaks.**
`db.execute_sql_script` does not run your statements on one continuous session.
Anything that sets state in one statement and reads it in the next will not work:

- `SET @my_var = …;` then `… WHERE id = @my_var;`
- `USE notes_app;` then an unqualified `CREATE TABLE note …`
- `START TRANSACTION;` … `COMMIT;` as separate statements
- The MariaDB REST Service DDL, which is grammar-level session state

For all of those, run the statements **individually with `db.execute_sql`** on one
open connection. For an ordinary create script — fully qualified names, no session
variables — the script tool is the right choice and much faster.
</div>

The safest habit, and the one the `mariadb-schema-create-script` skill enforces,
is to fully qualify every object name in a script: `` `notes_app`.`note` ``
rather than `note` after a `USE`. That makes the fresh-session behaviour a
non-issue.

## Transactions

Because each script statement gets its own session, a transaction cannot span a
script. Run the whole transaction through `db.execute_sql` on one connection:

```text
db.execute_sql(connection_id="…", sql="START TRANSACTION")
db.execute_sql(connection_id="…", sql="UPDATE notes_app.note SET … WHERE …")
db.execute_sql(connection_id="…", sql="DELETE FROM notes_app.note_tag WHERE …")
db.execute_sql(connection_id="…", sql="COMMIT")
```

<div class="prompt" markdown="1">
*Move every note from the "Inbox" notebook to "Archive" and delete the Inbox
notebook — in a single transaction, and roll back if anything fails.*
</div>

The `mariadb-transactions` skill covers what MariaDB does around implicit
commits, which is what turns this from a two-line answer into a correct one:
**DDL commits the open transaction**, so an `ALTER TABLE` in the middle of your
transaction silently ends it.

## Close what you opened

```text
db.close(connection_id="…")
```

Connections are reaped automatically after an idle period, so forgetting this is
not fatal. Closing explicitly is still worth doing on a long session, and is
essential before deleting a sandbox — a server with an open connection will not
stop cleanly.

<h2 class="no-step" id="what-you-built">What you learned</h2>

- `db.list_connections` first, always — the agent cannot invent a host.
- `db.execute_sql` for results, parameters, session state and transactions.
- `db.execute_sql_script` for multi-statement files, with **one fresh session per
  statement** — so fully qualify names and never rely on `SET`, `USE` or an open
  transaction carrying across.

**Where to go next**

- [Explore an existing database](../browse-schema-objects/) — the read-only half
  of `db.*`, and how to get a schema summary without a hundred `SHOW` statements.
- [Diagnose a slow query](../diagnose-a-slow-query/) — `EXPLAIN` through the same
  `db.execute_sql` you just used.
