---
order: 1
slug: notes-app-sandbox
title: "Build a Notes App schema and deploy it on a sandbox"
description: >-
  The complete round trip. The agent designs a MariaDB schema for a note-taking
  app using the bundled skills, deploys a throwaway MariaDB server, runs the
  schema on it, and reads the objects back to prove it worked.
level: beginner
duration: "20 min"
area: getting-started
tools: ["sandbox.deploy", "db.connect", "db.execute_sql_script", "db.list_objects"]
skills: ["mariadb-schema-create-script", "mariadb-create-table"]
path_label: "First Steps, Step 1 · Schema Lifecycle, Step 1"
prerequisites:
  - "A plugin installed in your harness — see [Get Started](../../get-started/)."
  - "`mariadb-shell -- mcp setup` run once, with the directory you will work in on the allowed-paths list."
  - "Nothing else — the sandbox brings its own MariaDB Server if the machine has none."
---

This is the tutorial everything else builds on. By the end you will have a
`notes_app.sql` script on disk, a running MariaDB server on port 3310 with that
schema in it, and a clear picture of which part of the work came from the
**skills** and which from the **MCP tools**.

Nothing here touches a database you care about. The sandbox is a throwaway
server that lives in one folder, and the last step deletes it.

## Ask for the whole thing at once

Open your agent in an empty directory — one that is on the MCP server's
allowed-paths list — and give it the whole task. Agents do this better as one
instruction than as four, because the later steps constrain the earlier ones:

<div class="prompt" markdown="1">
*Work in the current directory and complete every step in order.*

*1. Create a MariaDB database schema named `notes_app` for a note-taking app and
store it in a `notes_app.sql` file.*

*2. Spin up a sandbox instance on port 3310 with root password `demo-pw`,
connect to it and run `notes_app.sql` via the MCP server.*

*3. List the tables you created and show me the columns of the `note` table.*
</div>

Then read on to see what each step should look like — and what to do if it does
not.

## Watch the skills shape the schema

The agent writes `notes_app.sql` first. Before it writes a single `CREATE`, it
reads the `mariadb-schema-create-script` skill, and from there the
`mariadb-create-table` and `mariadb-create-index` skills. That is what makes the
output *MariaDB* SQL rather than generic SQL.

Three tells that the skills were actually used:

**The script opens and closes with a settings block.** Every script the skill
produces saves the session's checks and SQL mode, switches to `utf8mb4`, and
restores everything at the end:

```sql
-- Save current session settings and disable checks for faster, safer bulk import
SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO,STRICT_TRANS_TABLES';
SET @OLD_NOTE_VERBOSITY=@@NOTE_VERBOSITY, NOTE_VERBOSITY=0;

SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT, @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS;
SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION;
SET NAMES utf8mb4;
```

**Primary keys are native `UUID`, not `CHAR(36)`.** MariaDB has had a real
`UUID` column type since 10.7, and `UUID_v7()` generates time-ordered values, so
you get the index locality of an auto-increment without exposing a row count to
the outside world:

```sql
-- A person who writes notes.
CREATE OR REPLACE TABLE `notes_app`.`user` (
  `id`           UUID NOT NULL DEFAULT UUID_v7(),
  `email`        VARCHAR(255) NOT NULL,
  `display_name` VARCHAR(120) NOT NULL,
  `created_at`   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_user_email` (`email`)
) ENGINE=InnoDB;
```

**`CREATE SCHEMA IF NOT EXISTS`, and `CREATE OR REPLACE TABLE`.** The skill
prefers `SCHEMA` over `DATABASE`, and MariaDB's atomic `CREATE OR REPLACE` over
a `DROP`-then-`CREATE` pair — so re-running the script is safe and never leaves
you with the table gone and the create failed.

A reasonable Notes App comes out as five tables — `user`, `notebook`, `note`,
`tag` and the `note_tag` junction — plus a view or two. The exact shape will vary;
what should not vary is the MariaDB-specific detail above.

<div class="callout callout--tip" markdown="1">
**Push back and watch it use the skills again.** Ask *"make `note.body` full-text
searchable"* or *"add row history to `note` so I can see what it looked like last
week"*. The second one should produce a **system-versioned table**
(`WITH SYSTEM VERSIONING`) — a MariaDB feature with no MySQL equivalent, and one
the agent only reaches for because a skill told it about it.
</div>

## Deploy the sandbox

Now the MCP tools take over. The agent calls `sandbox.deploy`:

```text
sandbox.deploy(port=3310, password="demo-pw", ssl=False)
```

Three things happen that are worth knowing about:

- A real `mariadbd` starts, with its data directory under
  `~/.mariadb-shell/sandboxes/3310/`. No container runtime is involved. The
  server itself comes from your `PATH` if one there fits; otherwise the tool
  downloads a version, verifies its checksum and unpacks it — so this works on a
  machine with no MariaDB Server at all. The deploy's message says which of the
  two happened.
- The connection `root@127.0.0.1:3310` is **registered with the MCP server
  automatically**, password and all. You do not have to re-run `mcp setup` to
  let the agent connect to it.
- TLS is off (`ssl: False`), which is why a command-line client may need
  `--skip-ssl` later. Turning it on requires `openssl` on the machine.

<div class="callout callout--warn" markdown="1">
**The root password must not be blank.** `sandbox.deploy` will accept a blank
one, but the connection that gets registered then fails to open, and the failure
looks like an allow-list problem rather than a password problem. Always give a
password.
</div>

If the deploy *hangs* rather than failing, the sandbox directory is not on the
allowed-paths list — the path guard falls back to an interactive prompt that the
agent cannot answer. Run `mariadb-shell -- mcp setup` and add it.

## Connect and run the script

With the sandbox up, the agent opens the connection and runs the file:

```text
db.connect(uri="root@127.0.0.1:3310")
db.execute_sql_script(file_path="/abs/path/notes_app.sql", connection_id="…")
```

Two details about `db.execute_sql_script` that explain most of the surprises:

- **`file_path` must be inside an allowed path.** If it is not, the call is
  refused. The agent's fallback is to pass the script inline as `sql_script`
  instead, which works fine and is what it will usually do if your working
  directory was never allowed.
- **Each statement runs in a fresh session.** That is invisible for a normal
  create script, but it matters for anything that depends on session state
  carrying across statements — the MariaDB REST Service grammar, for instance,
  needs one continuous session, so those statements go through `db.execute_sql`
  one at a time instead. (That is [Tutorial 8](../rest-endpoints/).)

## Read the result back

The last step is the one that turns "the agent said it worked" into "it worked".
Ask it to inspect the server rather than to summarize its own output:

```text
db.list_schemas(connection_id="…")
db.list_objects(connection_id="…", schema_name="notes_app", object_type="table")
db.get_object_details(connection_id="…", schema_name="notes_app", object_name="note")
```

You should see `notes_app` in the schema list, your five tables in the object
list, and `note`'s columns — including the `UUID` primary key and the foreign
key to `user` — in the details.

<div class="prompt" markdown="1">
*Now insert three sample users and five notes, then show me each user with their
note count.*
</div>

That last query is a good sanity check on the foreign keys, and it is a job for
`db.execute_sql`, not the script tool — see [Tutorial 2](../run-sql-and-scripts/)
for when to use which.

## Clean up

The sandbox is a real server process. Stop it and delete it when you are done:

<div class="prompt" markdown="1">
*Stop and delete the sandbox on port 3310.*
</div>

```text
sandbox.stop(port=3310, password="demo-pw")
sandbox.delete(port=3310)
```

`sandbox.delete` **refuses to delete a running instance**, so the `stop` has to
land first. If a stop fails — a wedged server, a forgotten password —
`sandbox.kill` forces it down, and then `delete` will work.

<h2 class="no-step" id="what-you-built">What you built</h2>

A `notes_app.sql` script whose MariaDB-specific decisions came from the skills,
run against a real server that the agent created, verified and then removed —
without you ever typing a connection string or a password into a config file.

The two halves you just used are the whole product. Everything else on this site
is a deeper version of one of them.

**Where to go next**

- [Run SQL and SQL scripts](../run-sql-and-scripts/) — `db.execute_sql` vs.
  `db.execute_sql_script`, and why the distinction keeps biting people.
- [Explore an existing database](../browse-schema-objects/) — the same tools
  pointed at a schema you did *not* write.
- [Version the schema with MSM](../versioned-schema-with-msm/) — turn this
  one-off script into something you can ship version 2 of.
