---
order: 3
slug: browse-schema-objects
title: "Explore a database you did not design"
description: >-
  Point the agent at an existing MariaDB server and have it map the place out —
  schemas, tables, views, routines, columns, indexes and foreign keys — using
  the read-only db.* tools rather than a pile of SHOW statements.
level: beginner
duration: "15 min"
area: sql
tools: ["db.list_schemas", "db.list_objects", "db.get_object_details", "db.execute_sql"]
skills: ["mariadb-show", "mariadb-information-functions"]
path_label: "First Steps, Step 3 · Operate and Optimize, Step 2"
prerequisites:
  - "A configured connection to a MariaDB server with a schema in it — the `notes_app` sandbox from [Tutorial 1](../notes-app-sandbox/) works."
---

Inheriting a database is a normal Tuesday. The three read-only `db.*` tools are
built for exactly that: they return structured results the agent can reason over,
which is a different thing from dumping `SHOW CREATE TABLE` output into the
conversation and hoping.

<div class="prompt" markdown="1">
*Connect to the sandbox on port 3310 and give me a map of the `notes_app`
schema: every table with its columns, primary key and foreign keys, plus any
views or stored routines. Tell me which tables have no primary key.*
</div>

## Start at the top: `db.list_schemas`

```text
db.list_schemas(connection_id="…")
  → information_schema, mysql, performance_schema, sys, notes_app
```

The system schemas are always in the list. If a schema you expect is missing, it
is nearly always the account's privileges rather than the tool — MariaDB shows a
schema only to an account that has some privilege on it, so a read-only MCP
account scoped to one schema will see exactly one non-system schema. That is the
setup working as intended.

## List objects by type: `db.list_objects`

```text
db.list_objects(connection_id="…", schema_name="notes_app", object_type="table")
  → user, notebook, note, tag, note_tag
```

`object_type` accepts the usual kinds — `table`, `view`, `procedure`,
`function`, `trigger`, `event`. It defaults to `table`, so a call without it
lists tables.

<div class="callout callout--tip" markdown="1">
**Ask for all types in one go.** The agent will fan out across the types on its
own if you phrase the request as "everything in this schema" rather than naming
tables. That is four calls instead of one, but it catches the view nobody
mentioned and the trigger that explains the mystery column.
</div>

## Describe one object: `db.get_object_details`

```text
db.get_object_details(connection_id="…", schema_name="notes_app",
                      object_name="note", object_type="table")
```

For a table, that comes back as structured detail — columns with types,
nullability and defaults, the primary key, indexes, and foreign key constraints —
rather than as a `CREATE TABLE` string the agent has to re-parse. For a view or a
routine, you get its definition.

This is the tool to reach for before *any* schema change. An `ALTER TABLE`
proposed without reading the current definition is a guess.

## Ask the questions `INFORMATION_SCHEMA` answers better

The three tools above are the right shape for "show me this object". For
questions *about* the schema as a whole, one `db.execute_sql` against
`INFORMATION_SCHEMA` beats a hundred tool calls — and the agent knows it, because
that is what the `mariadb-show` and `mariadb-information-functions` skills teach.

**Tables with no primary key** — the classic one, because a table without a
primary key breaks row-based replication and makes InnoDB pick a hidden one:

```sql
SELECT t.TABLE_NAME
FROM information_schema.TABLES t
LEFT JOIN information_schema.TABLE_CONSTRAINTS c
       ON  c.TABLE_SCHEMA = t.TABLE_SCHEMA
       AND c.TABLE_NAME   = t.TABLE_NAME
       AND c.CONSTRAINT_TYPE = 'PRIMARY KEY'
WHERE t.TABLE_SCHEMA = 'notes_app'
  AND t.TABLE_TYPE   = 'BASE TABLE'
  AND c.CONSTRAINT_NAME IS NULL;
```

**The foreign key graph**, which is how you work out what depends on what before
dropping anything:

```sql
SELECT TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'notes_app'
  AND REFERENCED_TABLE_NAME IS NOT NULL
ORDER BY TABLE_NAME;
```

**Where the space actually went:**

```sql
SELECT TABLE_NAME,
       ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 1) AS size_mb,
       TABLE_ROWS
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'notes_app'
ORDER BY DATA_LENGTH + INDEX_LENGTH DESC;
```

<div class="callout callout--warn" markdown="1">
`TABLE_ROWS` is an **estimate** for InnoDB, sometimes off by a large factor. Use
it to rank tables by rough size, never to report a count. For a real count the
agent has to run `SELECT COUNT(*)`, and it should tell you it is doing so on a
big table.
</div>

## Two MariaDB-specific things to look for

When the agent maps a schema it did not write, two MariaDB features change what
the map *means*, and both are covered by skills:

- **System-versioned tables.** A table declared `WITH SYSTEM VERSIONING` keeps
  its own row history. `SELECT *` shows only current rows, so a table can be far
  larger on disk than its row count suggests, and `DELETE` does not actually
  remove anything. If `db.get_object_details` shows a table with system
  versioning, that is the explanation for both.
- **Invisible columns.** A column declared `INVISIBLE` is absent from
  `SELECT *` and from `INSERT` without a column list. It will show up in the
  object details and not in a query — which looks like a bug until you know.

<div class="prompt" markdown="1">
*Are any tables in this schema system-versioned? If so, show me what the `note`
table looked like a week ago.*
</div>

## Write it down

The most useful end to this exercise is a file, not a chat message:

<div class="prompt" markdown="1">
*Write everything you just found into `SCHEMA.md` — one section per table with
its columns and relationships, a diagram of the foreign keys, and a "things that
look wrong" section at the end.*
</div>

That needs the working directory on the allowed-paths list. It is also the point
at which the agent stops being a query runner and starts being useful on a
codebase you are new to.

<h2 class="no-step" id="what-you-built">What you learned</h2>

- `db.list_schemas` → `db.list_objects` → `db.get_object_details` is the drill-down,
  and the details call is mandatory before proposing any schema change.
- Schema-wide questions belong in one `INFORMATION_SCHEMA` query via
  `db.execute_sql`, not in a loop of tool calls.
- A missing schema is usually privileges; a surprising row count is usually
  system versioning or an estimate.

**Where to go next**

- [Diagnose a slow query](../diagnose-a-slow-query/) — now that you can read the
  schema, read the plan.
- [Version the schema with MSM](../versioned-schema-with-msm/) — put an inherited
  schema under version control before you change it.
