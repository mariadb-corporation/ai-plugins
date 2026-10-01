---
description: >-
  Reference for the db tools of the mariadb-shell MCP server, which list connections and schemas, describe database objects, and run SQL.
---

# db Tools

The `db.*` tools open connections to configured MariaDB servers, describe their schemas, and run SQL.

## Overview

| Tool | Description |
| --- | --- |
| `db.list_connections` | Lists the configured connection URIs. |
| `db.connect` | Opens and caches a connection, and returns a `connection_id`. |
| `db.list_schemas` | Lists the schemas visible to the connection's account. |
| `db.list_objects` | Lists the objects of one type in a schema. |
| `db.get_object_details` | Returns structured details of an object: columns, keys, indexes, and constraints. |
| `db.execute_sql` | Runs one statement on the connection's session. |
| `db.execute_sql_script` | Runs a multi-statement script. |
| `db.close` | Closes a connection. |

## db.list_connections

Lists the configured connection URIs.

This tool takes no arguments.

The list is derived from MariaDB Shell's secret store, so a connection registered by a sandbox appears here too. Call it first.

## db.connect

Opens and caches a connection, and returns a `connection_id`.

| Argument | Description |
| --- | --- |
| `uri` | A configured connection URI. |

The URI is normalized before matching. A URI that asks for more than was configured, such as a default schema or an option, is refused. See [Security Model](../security-model.md#connections).

## db.list_schemas

Lists the schemas visible to the connection's account.

| Argument | Description |
| --- | --- |
| `connection_id` | A connection ID returned by `db.connect`. |

A missing schema usually means the account lacks privileges on it.

## db.list_objects

Lists the objects of one type in a schema.

| Argument | Description |
| --- | --- |
| `connection_id` | A connection ID returned by `db.connect`. |
| `schema_name` | The schema to list. |
| `object_type` | One of `table` (default), `view`, `procedure`, `function`, `trigger`, or `event`. |

## db.get_object_details

Returns structured details of an object: columns, keys, indexes, and constraints.

| Argument | Description |
| --- | --- |
| `connection_id` | A connection ID returned by `db.connect`. |
| `schema_name` | The object's schema. |
| `object_name` | The object's name. |
| `object_type` | The object type. Default: `table`. |

The result is structured data, not a `CREATE` statement. Agents call this before proposing a schema change.

## db.execute_sql

Runs one statement on the connection's session.

| Argument | Description |
| --- | --- |
| `connection_id` | A connection ID returned by `db.connect`. |
| `sql` | One SQL statement. |
| `params` | Optional values for the statement's placeholders. |

Use it for statements that return results, take parameters, or depend on session state or transactions.

## db.execute_sql_script

Runs a multi-statement script.

| Argument | Description |
| --- | --- |
| `connection_id` | A connection ID returned by `db.connect`. |
| `sql_script` | The script text. |
| `file_path` | A script file. Must be in an allowed path. |

{% hint style="warning" %}
`db.execute_sql_script` runs each statement in a new session. Anything that sets state in one statement and reads it in the next doesn't work: `SET @var`, `USE`, a `START TRANSACTION` and `COMMIT` pair, or MariaDB REST Service statements. Run those individually with `db.execute_sql` on one connection. For a create script with fully qualified object names, `db.execute_sql_script` is the right tool, and much faster.
{% endhint %}

## db.close

Closes a connection.

| Argument | Description |
| --- | --- |
| `connection_id` | A connection ID returned by `db.connect`. |

Idle connections are closed automatically, but close a sandbox's connection before deleting the sandbox.
