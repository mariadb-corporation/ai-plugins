---
description: >-
  Reference for the db tools of the mariadb-shell MCP server, which list connections and schemas, describe database objects, and run SQL.
---

# db Tools

<!--
  SYNCED: this page is maintained in mariadb-corporation/ai-plugins, under docs-ref/content/,
  and copied one way into mariadb-docs (tools/community/mariadb-ai-plugins/).
  Make every change in mariadb-corporation/ai-plugins. A change made in mariadb-docs or in the
  GitBook editor is overwritten by the next sync.
-->

The `db.*` tools open connections to configured MariaDB servers, describe their schemas, and run SQL.

## Overview

| Tool | Description |
| --- | --- |
| `db.list_connections` | Lists the configured connection URIs. |
| `db.connect` | Opens and caches a connection, and returns a `connection_id`. |
| `db.list_schemas` | Lists the schemas visible to the connection's account. |
| `db.list_objects` | Lists the objects of one type in a schema. |
| `db.get_object_details` | Returns structured details of an object, such as a table's columns, constraints, and foreign keys. |
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
| `uri` | A connection URI, as `db.list_connections` returns it. |

The URI is normalized before matching, so a URI that leaves out the `mariadb://` scheme or the default port names the same connection. A URI that asks for more than was configured, such as a default schema, a connection option, or another scheme, is refused. See [Security Model](../security-model.md#connections).

The connection is usable until `db.close` closes it, or until it expires a few hours after it was opened. After that, call `db.connect` again for a new `connection_id`. Over HTTP, only the client that opened a connection can use it. The number of connections that can be open at the same time is limited, so close the ones that are no longer needed.

The database session of a connection is closed after a period without use, and the next call opens a new one. Temporary tables, user variables, the current schema, and an open transaction don't survive this, and the result of the next call contains `session_restarted: true`.

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
| `object_type` | One of `table` (default), `view`, `function`, `procedure`, `sequence`, `trigger`, or `event`. |

The tool returns the name of each object, the comment of each table and view, and the data type of each sequence. It lists only the objects that the connection's account has access to. An unknown schema returns an empty list.

## db.get_object_details

Returns structured details of an object, such as a table's columns, constraints, and foreign keys.

| Argument | Description |
| --- | --- |
| `connection_id` | A connection ID returned by `db.connect`. |
| `schema_name` | The object's schema. |
| `object_name` | The object's name. |
| `object_type` | One of `table` (default), `view`, `function`, `procedure`, `sequence`, `trigger`, or `event`. |

The result always contains the object's schema, name, type, and comment. The rest depends on the object type:

* A table adds its columns, its constraints, and its foreign key relationships in both directions.
* A view adds its columns.
* A function or procedure adds its parameters, each with its name, mode, data type, and default. A function also adds the data type that it returns.
* A sequence, trigger, or event adds the properties of its type.

The result is returned as structured data rather than as a `CREATE` statement. The agent calls this tool before it proposes a schema change.

## db.execute_sql

Runs one statement on the connection's session.

| Argument | Description |
| --- | --- |
| `connection_id` | A connection ID returned by `db.connect`. |
| `sql` | One SQL statement. It can contain `?` placeholders. |
| `params` | Optional. The values to bind to the `?` placeholders, in order. |
| `limit` | Optional. The maximum number of rows to return. A `SELECT` without its own `LIMIT` gets one. A `SELECT` that has its own `LIMIT`, or a clause that a `LIMIT` would precede (`INTO`, `FOR UPDATE`, `FOR SHARE`, `LOCK IN SHARE MODE`, or `PROCEDURE`), and any other statement run as written. |
| `offset` | Optional. The number of rows to skip before the first row returned, to get the pages after the first. Requires `limit`. |
| `column_metadata` | Whether each result set also includes column metadata, with the type and flags of each column. Default: `False`. |
| `output_format` | `json` (default) returns the columns and rows as data. `table` returns the text grid that the `mariadb` client prints, and its `row_count`, to show a result to the user unchanged. |

Use it for a single statement, in particular one that takes parameters or whose result rows the agent needs.

The tool returns `result_sets`, one for each result set in order. A statement without rows has none, and a called procedure has one for each `SELECT` it runs. In `json` format, each result set has `columns` and `rows`, with each row keyed by the column labels. A repeated label is keyed `label_2`, `label_3`, and so on. Binary values are returned as hexadecimal text. In `table` format, each result set has `table` and `row_count` instead. The grid shows binary values as hexadecimal and escapes control characters, so that every row stays on one line.

`warnings_count` is the number of warnings that the statement produced, and `warnings` lists them with their level, code, and message. When `limit` added a `LIMIT` to the statement, `has_more_pages` is `true` if more rows follow, and `false` on the last page. To get the next page, pass `offset` plus `limit` as the new `offset`.

When the result contains `session_restarted: true`, the statement ran on a new session because the previous one was closed for being idle or lost. Temporary tables, user variables, the current schema, and an open transaction are gone, so a `COMMIT` or `ROLLBACK` reported with this flag did nothing.

## db.execute_sql_script

Runs a multi-statement script.

| Argument | Description |
| --- | --- |
| `connection_id` | A connection ID returned by `db.connect`. |
| `sql_script` | One or more SQL statements separated by semicolons. Pass either `sql_script` or `file_path`. |
| `file_path` | A `.sql` file to read the script from. Must be in an allowed path. |
| `stop_on_error` | Whether the script stops at the first failed statement. Default: `True`. With `False`, every statement runs and each failure is reported. |
| `limit` | Optional. The maximum number of rows that each `SELECT` returns, as for `db.execute_sql`. To get the pages after the first, use `db.execute_sql` with `offset`. |
| `column_metadata` | Whether each result set also includes column metadata, as for `db.execute_sql`. Default: `False`. |
| `ansi_quotes` | Whether the script is split with `"..."` read as a quoted identifier, as the server does when its `sql_mode` includes `ANSI_QUOTES`. This matters only where a backslash ends a double-quoted identifier. Default: `False`. |
| `report_sql_mode` | Whether the last entry also reports `ansi_quotes` and the session's `sql_mode` after the script. Default: `False`. |
| `output_format` | `json` (default) or `table`, as for `db.execute_sql`. |
| `source_dir` | Optional. The directory that relative `SOURCE` paths of an inline `sql_script` are resolved against. Must be in an allowed path. Can't be combined with `file_path`, whose own directory is used. |
| `rollback_on_error` | Whether a transaction that the script opened is rolled back when one of its statements fails. Default: `True`. With `False`, the transaction stays open, for a caller that manages its transactions itself. |

The statements run in order on the session of the connection, so session state carries over from one statement to the next. This includes user variables set with `SET @var`, the current schema set with `USE`, open transactions, and the current REST service and REST schema of MariaDB REST Service statements.

### SOURCE Directives

Before the script runs, the tool expands MariaDB Schema Management `SOURCE` directives, so a project's development script runs with its section files. A directive is a line of its own, with an optional comment:

```sql
SOURCE '<path>'[<start>:<end>];
```

The tool replaces the directive with the selected part of the file. Without a slice, it uses the whole file. A slice selects character offsets with Python slice semantics, such as `[100:200]` or `[-50:]`, or line numbers as `lnN`, counted from 1 with the end line included, where `ln-1` is the last line, such as `[ln3:ln10]`. A directive works anywhere in the script, also inside a procedure body, but an included file can't contain further directives.

A relative path is resolved against the directory of `file_path`, or against `source_dir` for an inline script. Without `source_dir`, an inline script can only use absolute paths. Every included file must be in an allowed path. A directive that can't be expanded fails the call before any statement runs.

### Results

The tool returns one entry for each statement that ran, with its `statement_index`, its `execution_time` in seconds, and `result_sets`, `warnings_count`, and `warnings` as `db.execute_sql` returns them. The `statement_index` counts the non-empty statements of the script from 0. Statements that a `SOURCE` directive included share the directive's `statement_index`, and their `source` names the included file and the line that the statement starts on. A statement that consists only of a `--` or `#` comment doesn't run and has no entry, but keeps its `statement_index`.

A failed statement doesn't raise an error. Its entry contains `error`, with the error message, and `statement`, with the failed statement text, instead of result sets, so the agent must check every entry. With `stop_on_error` set to `True`, the statements after the failure have no entries.

A script isn't a transaction, and statements that ran outside a transaction keep their effect. When a statement fails inside a transaction that the script opened, with `START TRANSACTION` or with any statement under `autocommit=0`, the tool rolls the transaction back if the script didn't end it. The last entry then contains `transaction_rolled_back: true`, or `rollback_error` if the rollback failed. A transaction that was already open before the script stays open, and the last entry contains `transaction_open: true`. With `rollback_on_error` set to `False`, the tool does none of this. Checking for an open transaction after a failure clears the session's warnings, so with `stop_on_error` set to `False`, a `SHOW WARNINGS` directly after a failed statement shows warnings only if `rollback_on_error` is `False`.

{% hint style="info" %}
If the connection's session was closed because it was idle or lost, the MCP server opens a new session before it runs the script, and the first entry contains `session_restarted: true`. In this case, state from earlier tool calls, such as temporary tables, user variables, the current schema, and an open transaction, no longer exists.
{% endhint %}

## db.close

Closes a connection.

| Argument | Description |
| --- | --- |
| `connection_id` | A connection ID returned by `db.connect`. |

A connection expires a few hours after it was opened, and only a limited number can be open at the same time, so close the connections that are no longer needed. Close a sandbox's connection before deleting the sandbox.

<sub>_This page is licensed: GPLv2_</sub>

{% @marketo/form formId="4316" %}
