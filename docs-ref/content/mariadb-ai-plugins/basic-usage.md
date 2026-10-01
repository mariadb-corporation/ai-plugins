---
description: >-
  What you can ask an AI coding agent for with MariaDB AI Plugins: with skills
  alone, with the MCP server connected to your database, and with a sandbox
  instance.
---

# Basic Usage

You use the plugins by asking the agent for what you want, in plain language. The agent decides which skills to read and which MCP tools to call.

## With Skills Alone

No database connection is needed:

* *Write a `CREATE TABLE` for a product catalog, MariaDB style.*
* *What changes if I move this application from MySQL to MariaDB?*
* *How do I do semantic search in MariaDB?*
* *Show me how to connect to MariaDB from Node.js.*

## With the MCP Server Connected

Against a database you configured with `mcp setup`:

* *What does the schema of my `orders` table look like?*
* *Why is this query slow? Run `EXPLAIN` on it.*
* *Which of my tables have no primary key?*
* *Deploy a test instance and try this migration on it first.*

## With a Sandbox Instance

Without any database, the MCP server can deploy a throwaway MariaDB Server instance locally:

* *Deploy a MariaDB sandbox on port 3310.*
* *Spin up a test instance, apply this schema to it, and show me the result.*
* *Try this migration on a sandbox before I run it for real.*
* *Stop and delete the sandbox, I'm done with it.*

See [Sandbox Instances](features/sandbox-instances.md).

## A Complete Example

This request uses both halves of the plugin. The skills design the schema the MariaDB way; the MCP tools deploy a server and run the script:

```
Create a MariaDB database schema for a note-taking app and store it in
notes_app.sql. Then spin up a sandbox instance on port 3310, connect to it,
and run the script. Finally, list the tables you created.
```

The agent calls `sandbox.deploy`, then `db.connect` on the connection the sandbox registered, then `db.execute_sql_script` with the file, and finally `db.list_objects`. The directory holding `notes_app.sql` must be on the [allowed-paths list](configuring-the-mcp-server.md#allowed-paths).

## Using MariaDB Shell Yourself

MariaDB Shell is also a SQL client you can use directly. Run `mariadb-shell` and type `\help`. Sandbox instances the agent creates are visible to it.
