---
description: >-
  Reference for the util tools of the mariadb-shell MCP server, which dump, load, export, import, and copy data as background tasks, and the task tools that follow them.
---

# util Tools

<!--
  SYNCED: this page is maintained in mariadb-corporation/ai-plugins, under docs-ref/content/,
  and copied one way into mariadb-docs (tools/community/mariadb-ai-plugins/).
  Make every change in mariadb-corporation/ai-plugins. A change made in mariadb-docs or in the
  GitBook editor is overwritten by the next sync.
-->

The `util.*` tools run MariaDB Shell's dump, load, export, import, and copy utilities, and inspect dumps. Each utility runs as a background task, and the `task.get`, `task.list`, and `task.cancel` tools follow the tasks and stop them. See [task Tools](#task-tools).

{% hint style="info" %}
The `util.*` tools are available in MariaDB Shell 26.10.2 and later.
{% endhint %}

## Overview

| Tool | Description |
| --- | --- |
| `util.dump_instance` | Dumps the whole server to a directory or a single file. |
| `util.dump_schemas` | Dumps schemas to a directory or a single file. |
| `util.dump_tables` | Dumps tables and views of a schema to a directory or a single file. |
| `util.export_table` | Exports the rows of a table to a file. |
| `util.load_dump` | Loads a dump into a server. |
| `util.inspect_dump` | Reports what a dump holds, without loading it. |
| `util.import_table` | Imports files into a table. |
| `util.copy_instance` | Copies the whole server to another server. |
| `util.copy_schemas` | Copies schemas to another server. |
| `util.copy_tables` | Copies tables of a schema to another server. |
| `task.get` | Returns the state of a task. |
| `task.list` | Lists the tasks of the client. |
| `task.cancel` | Stops a running task. |

The `util.*` tools are offered only together with the `db.*` group, because every utility works on a connection from `db.connect`. A server in multi-tenant mode never offers them. The `task.*` tools are offered whenever the server offers a tool that starts tasks.

The agent uses these tools instead of running `mariadb-dump` or piping its output into another client. The plugins' CLI guard blocks a `mariadb-dump` command that is piped into a client, and names the `util.copy_*` tools instead.

## Background Tasks

The dump, load, export, import, and copy tools start the utility and return immediately, with the following fields:

| Field | Description |
| --- | --- |
| `task_id` | The ID to pass to `task.get` and `task.cancel`. |
| `status` | The task's status when the call returns. |

A task's status is `pending`, `running`, `completed`, `failed`, or `cancelled`. A finished task is kept for one hour, and the server keeps at most 100 finished tasks. A client can run at most four `util` tasks at once, because a dump or load opens a session for each of its threads.

Each task runs the utility in a MariaDB Shell process of its own. That process logs in with the URI and the stored password of the connection that `connection_id` names, and receives the password on standard input, not on its command line. The task doesn't use the connection itself, so the connection stays available for other tools while the task runs. The MCP server runs the task with the MariaDB Shell binary that it runs in itself or, failing that, with `mariadb-shell` on the `PATH`.

When the MCP server ends, it stops the tasks that are still running.

## Options and Paths

Each tool takes an `options` argument with the options of the shell utility, named in camelCase, for example `{"threads": 8, "ddlOnly": true}`. For the options of each utility, see the MariaDB Shell documentation.

The tools set the following options themselves and refuse them in `options`:

* `session`
* `progressCallback`
* `showProgress`
* `outputUrl`, for `util.dump_schemas` and `util.dump_tables` only. Use the `output_url` argument.
* `waitDumpTimeout`, for `util.load_dump` of a `.mariadb.dump.zip` file only.

A load of a `.mariadb.dump.zip` file also refuses an empty `progressFile`, and a `progressFile` that isn't a local file.

A local path in `output_url`, `url`, or `urls`, and in the `progressFile`, `ociConfigFile`, `s3ConfigFile`, `s3CredentialsFile`, and `azureConfigFile` options, must be in an allowed path. See [Security Model](../security-model.md#paths). A path with wildcards is checked at its directory. A URL with a scheme other than `file://`, such as an `https://` URL, isn't a local path and isn't checked. When the `s3BucketName`, `osBucketName`, or `azureContainerName` option is set, `output_url`, `url`, and `urls` are prefixes in object storage and aren't checked either. A `.mariadb.dump.zip` file must be a local file, and its directory is checked. `util.inspect_dump` reads only a local dump.

## Dumps in a Single File

When `output_url` ends in `.mariadb.dump.zip`, a dump tool writes the dump as a single ZIP file. `util.load_dump` and `util.inspect_dump` take such a file as well as a dump directory.

A dump to a ZIP file first runs into a directory next to the file, named like the file with `.tmp` in place of `.zip`, and then packs that directory into the file. The directory is removed whether or not the dump succeeds, so a dump to a ZIP file can't be resumed. The file must not exist, and its directory must exist. A directory or `.part` file that is left over from a dump that didn't finish makes the tool refuse the dump until you remove it. A dry run dumps nothing and writes no file.

A load of a ZIP file extracts it into a directory next to the file, named like the file with `.extracted` in place of `.zip`, while the load runs. The extraction keeps at most `extraction_budget_mb` of data on disk that is extracted but not yet loaded, and empties each data file once it is loaded, so the load needs disk space for the file and that budget rather than twice the dump. The directory is removed once the load completes. If the load fails, the directory is kept, and a load of the same file resumes there. The load always uses a progress file, which is the `progressFile` option or a file in that directory. MariaDB Shell refuses a progress file that was written for another server, so a directory with loaded data files emptied can't be loaded into another server.

## util.dump_instance

Dumps the whole server to a directory or a single file.

| Argument | Description |
| --- | --- |
| `connection_id` | A connection ID returned by `db.connect`, for the server to dump. |
| `output_url` | The directory to write the dump to, which must not exist or must be empty. Or a file ending in `.mariadb.dump.zip`, which must not exist, to write the dump as a single ZIP file. See [Dumps in a Single File](#dumps-in-a-single-file). |
| `options` | Optional. The options of the utility, such as `{"threads": 8, "users": false, "excludeSchemas": ["test"]}`. |

When the task completes, its `result` holds `output_url`. For a ZIP file, it also holds the number of `files` packed and their size in `bytes`.

## util.dump_schemas

Dumps schemas to a directory or a single file.

| Argument | Description |
| --- | --- |
| `connection_id` | A connection ID returned by `db.connect`. |
| `schemas` | The names of the schemas to dump. |
| `output_url` | The directory to write the dump to, which must not exist or must be empty. Or a file ending in `.mariadb.dump.zip`, which must not exist, to write the dump as a single ZIP file. See [Dumps in a Single File](#dumps-in-a-single-file). |
| `options` | Optional. The options of the utility, such as `{"threads": 8, "ddlOnly": true}`. |

When the task completes, its `result` holds `output_url`. For a ZIP file, it also holds the number of `files` packed and their size in `bytes`.

## util.dump_tables

Dumps tables and views of a schema to a directory or a single file.

| Argument | Description |
| --- | --- |
| `connection_id` | A connection ID returned by `db.connect`. |
| `schema` | The schema that the tables are in. |
| `tables` | The names of the tables and views to dump. To dump all of them, pass an empty list and `{"all": true}` in `options`. |
| `output_url` | The directory to write the dump to, which must not exist or must be empty. Or a file ending in `.mariadb.dump.zip`, which must not exist, to write the dump as a single ZIP file. See [Dumps in a Single File](#dumps-in-a-single-file). |
| `options` | Optional. The options of the utility, such as `{"where": {"shop.orders": "id > 1000"}}`. |

When the task completes, its `result` holds `output_url`. For a ZIP file, it also holds the number of `files` packed and their size in `bytes`.

## util.export_table

Exports the rows of a table to a file.

| Argument | Description |
| --- | --- |
| `connection_id` | A connection ID returned by `db.connect`. |
| `table` | The table, as `table` or `schema.table`. |
| `output_url` | The file to write. |
| `options` | Optional. The options of the utility, such as `{"dialect": "csv", "where": "id > 10"}`. |

When the task completes, its `result` holds `output_url`.

## util.load_dump

Loads a dump into a server. The server must have `local_infile` enabled. The tool loads only dumps that the `util.dump_*` tools made. For CSV, TSV, JSON, and other data files, use `util.import_table`.

| Argument | Description |
| --- | --- |
| `connection_id` | A connection ID returned by `db.connect`, for the server to load into. |
| `url` | The directory of a dump made with `util.dump_instance`, `util.dump_schemas`, or `util.dump_tables`, or its `.mariadb.dump.zip` file. |
| `options` | Optional. The options of the utility, such as `{"schema": "copy_of_shop", "loadUsers": false, "dropExistingObjects": true}`. |
| `extraction_budget_mb` | Optional, and for a `.mariadb.dump.zip` file only. The maximum number of megabytes of data that is extracted and not yet loaded at the same time. Default: `1024`, or more for large data files. |

The load records its progress in a progress file, which is kept with the dump by default. If the shell process of the task crashes, the MCP server starts the load again from the progress file, up to three more times. A load that is stopped with `task.cancel` resumes where it stopped when the same dump is loaded again. A load from an `https://` URL, or with `progressFile` set to an empty string, has no progress file and isn't resumed. For a load of a ZIP file, see [Dumps in a Single File](#dumps-in-a-single-file).

When the task completes, its `result` holds `url`.

## util.inspect_dump

Reports what a dump holds, from its metadata, without loading it. The tool works on a dump directory and on a `.mariadb.dump.zip` file, and also on a dump that is still being written. It returns the result directly, not as a task.

| Argument | Description |
| --- | --- |
| `url` | The directory of the dump, or its `.mariadb.dump.zip` file. Must be a local path in an allowed path. |
| `schema` | Optional. A single schema to report, with every name of its objects. Without it, the tool lists at most 100 names of each kind, with counts. |

The result holds the dump's kind (`dumpInstance`, `dumpSchemas`, or `dumpTables`), whether the dump is complete, the source server, when the dump began and ended, the dump's options, its users, and its schemas with their tables, views, functions, procedures, and events. Row counts and data sizes are exact for a complete dump, and estimates otherwise. Only a dump of a single schema can be loaded into another schema with the `schema` option of `util.load_dump`.

## util.import_table

Imports files into a table. The table must exist, and the server must have `local_infile` enabled.

| Argument | Description |
| --- | --- |
| `connection_id` | A connection ID returned by `db.connect`. |
| `urls` | A file, or a list of files, to import. File names can contain the wildcards `*` and `?`. |
| `options` | Optional. The options of the utility, such as `{"schema": "shop", "table": "orders", "dialect": "csv-unix", "skipRows": 1}`. |

When the task completes, its `result` holds `urls`, as a list.

## util.copy_instance

Copies the whole server to another server. The copy dumps from the source and loads into the target at the same time, and writes no files. The target must have `local_infile` enabled.

| Argument | Description |
| --- | --- |
| `connection_id` | A connection ID returned by `db.connect`, for the source server. |
| `target_connection_id` | A connection ID returned by `db.connect`, for the target server. It must be a different server. |
| `options` | Optional. The options of the utility, such as `{"users": false, "threads": 8}`. |

When the task completes, its `result` holds `target_connection_id`.

## util.copy_schemas

Copies schemas to another server. The copy dumps from the source and loads into the target at the same time, and writes no files. The target must have `local_infile` enabled.

| Argument | Description |
| --- | --- |
| `connection_id` | A connection ID returned by `db.connect`, for the source server. |
| `schemas` | The names of the schemas to copy. |
| `target_connection_id` | A connection ID returned by `db.connect`, for the target server. It must be a different server. |
| `options` | Optional. The options of the utility, such as `{"ddlOnly": true}`. |

When the task completes, its `result` holds `target_connection_id`.

## util.copy_tables

Copies tables of a schema to another server. The copy dumps from the source and loads into the target at the same time, and writes no files. The target must have `local_infile` enabled.

| Argument | Description |
| --- | --- |
| `connection_id` | A connection ID returned by `db.connect`, for the source server. |
| `schema` | The schema that the tables are in. |
| `tables` | The names of the tables and views to copy. |
| `target_connection_id` | A connection ID returned by `db.connect`, for the target server. It must be a different server. |
| `options` | Optional. The options of the utility. To load the tables into another schema, pass `{"schema": "<name>"}`. |

When the task completes, its `result` holds `target_connection_id`.

## task Tools

The `task.*` tools follow the background tasks that a client started, and stop them. A client sees only its own tasks: the task of another client is reported as if it doesn't exist. Besides `util` tasks, the tools also follow the cloud deployments of the `dba.*` tools, which have the task type `dba`.

### task.get

Returns the state of a task.

| Argument | Description |
| --- | --- |
| `task_id` | The task ID that the tool that started the task returned. |
| `since` | Optional. The `next_since` value of the previous call, to get only the messages reported after it. Default: `0`, which returns all the messages that are kept. |
| `wait_ms` | Optional. The number of milliseconds to wait for a change before the tool returns, at most 30000. The tool returns early when a message arrives or the task finishes. Default: `0`, which returns immediately. |

Returns the following fields.

| Field | Description |
| --- | --- |
| `task_id` | The task ID. |
| `task_type` | The type of the task, `util` or `dba`. |
| `kind` | What the task does, such as `dump_schemas`. |
| `title` | A short description of the task, such as `Dump shop to /backups/shop`. |
| `connection_id` | For a `util` task, the connection that the task runs on. |
| `status` | `pending`, `running`, `completed`, `failed`, or `cancelled`. |
| `cancel_requested` | Whether `task.cancel` was called for the task. |
| `created_at`, `started_at`, `finished_at` | When the task was created, started, and finished, in ISO 8601 format and UTC. |
| `stage` | The stage that the task is in. |
| `progress` | The progress of the current stage, with `current`, `total`, and `percent`, and `throughput`, `eta_seconds`, and `items` where the stage measures them. |
| `stages` | The stages that the task has reached so far, each with its `name`, `status`, and duration in `seconds`. |
| `messages` | The messages after `since`. Each has a `seq`, `time`, `level`, and `text`. |
| `messages_dropped` | The number of messages after `since` that are no longer kept. A task keeps its last 2000 messages. |
| `next_since` | The value to pass as `since` in the next call. |
| `result` | When the task completed, what it produced, as described for each tool. |
| `error` | When the task failed, the error. |

### task.list

Lists the tasks of the client that are still kept, oldest first.

| Argument | Description |
| --- | --- |
| `task_type` | Optional. Only the tasks of this type: `util` for dumps, loads, copies, exports, and imports, or `dba` for cloud deployments. Default: all tasks. |

Returns one entry for each task, with the fields that `task.get` returns, except `messages` and `messages_dropped`.

### task.cancel

Stops a running task, which then ends as `cancelled`. Cancelling a finished task does nothing.

| Argument | Description |
| --- | --- |
| `task_id` | The task ID that the tool that started the task returned. |

For a `util` task, the utility is interrupted as if by Ctrl+C. A load that is stopped can be resumed by loading the same dump again. A `dba` task stops waiting for the cloud vendor, but what the vendor already started, such as building a server, goes on and has to be deleted separately.

Returns the task's state, as `task.get` returns it, without `messages` and `messages_dropped`.

## Common Failures

| Symptom | Cause |
| --- | --- |
| The MCP server offers no `util.*` tools. | The server doesn't serve the `db.*` group, runs in multi-tenant mode, or is from a MariaDB Shell release earlier than 26.10.2. |
| A tool reports that the MariaDB Shell binary wasn't found. | The MCP server can't find a shell to run the task in. Put `mariadb-shell` on the `PATH`. |
| A tool reports that four `util` tasks are already running. | The client has reached its limit of running tasks. Wait for a task to finish, or stop one with `task.cancel`. |
| A tool refuses an option. | The option is one that the tool sets itself. See [Options and Paths](#options-and-paths). |
| A load, import, or copy fails because of `local_infile`. | The server that the data goes into has `local_infile` disabled. |
| A dump fails because the output directory isn't empty. | `output_url` names a directory that already holds files. Use a new directory. |
| A dump to a `.mariadb.dump.zip` file is refused. | The file already exists, its directory doesn't exist, or a `.tmp` directory or `.part` file is left over from a dump that didn't finish. Remove the leftover, or use a new file name. |

<sub>_This page is licensed: GPLv2_</sub>

{% @marketo/form formId="4316" %}
