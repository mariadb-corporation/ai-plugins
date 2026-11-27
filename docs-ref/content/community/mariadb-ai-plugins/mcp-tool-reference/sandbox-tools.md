---
description: >-
  Reference for the sandbox tools of the mariadb-shell MCP server, which list deployable MariaDB Server versions and deploy, list, start, stop, and delete local instances.
---

# sandbox Tools

<!--
  SYNCED: this page is maintained in mariadb-corporation/ai-plugins, under docs-ref/content/,
  and copied one way into mariadb-docs (tools/community/mariadb-ai-plugins/).
  Make every change in mariadb-corporation/ai-plugins. A change made in mariadb-docs or in the
  GitBook editor is overwritten by the next sync.
-->

The `sandbox.*` tools deploy and manage local MariaDB Server instances for development and testing. For an introduction, see [Sandbox Instances](../features/sandbox-instances.md).

## Overview

| Tool | Description |
| --- | --- |
| `sandbox.list_available_versions` | Lists the server versions `sandbox.deploy` can install. |
| `sandbox.deploy` | Creates and starts an instance, and registers its connection with the MCP server. |
| `sandbox.list_instances` | Lists the instances in the default sandbox location, with their versions and status. |
| `sandbox.start` | Restarts an existing instance with its data intact. |
| `sandbox.stop` | Shuts an instance down gracefully. |
| `sandbox.kill` | Stops an instance forcefully. |
| `sandbox.delete` | Removes an instance. |
| `sandbox.vendor` | Returns the instance's vendor, `MariaDB` or `MySQL`. |
| `sandbox.version` | Returns the instance's server version. |

## sandbox.list_available_versions

Lists the server versions `sandbox.deploy` can install.

| Argument | Description |
| --- | --- |
| `series` | Optional. A series such as `11.8` or `11`. |

Without an argument, it lists the newest patch release of each series. With a series, it lists every release in that series. Only packages built for the current platform are listed, and every listed version can be deployed.

## sandbox.deploy

Creates and starts an instance, and registers its connection with the MCP server.

| Argument | Description |
| --- | --- |
| `port` | The instance's port. |
| `password` | The password for the instance's `root` user. The agent passes a freshly generated random password of 16 or more letters and digits, unless the user asks for a particular one. The password is stored with the registered connection. An empty string leaves `root` without a password, so that with the default `allow_root_from` anyone who can reach the port can log in. |
| `sandbox_dir` | The sandbox directory. Must be in an allowed path. Leave empty for the default sandbox location. |
| `allow_root_from` | The host pattern for a remote `root` account. Default: `%`. An empty string skips creating the account. |
| `server_id` | The instance's `server_id`. |
| `ssl` | Whether to generate certificates and enable TLS. Default: `False`, so that `openssl` isn't needed. `True` requires `openssl`. |
| `openssl_path` | The `openssl` executable, or its directory. |
| `server_version` | A version such as `11.8.9`, `11.8` for the latest patch release of that series, or `11` for the latest release of that major version. `sandbox.list_available_versions` lists the versions on offer. Leave empty for the server on the `PATH`. Can't be combined with `mariadbd_path`. |
| `mariadbd_path` | The `mariadbd` binary, or its installation directory. |
| `mariadbd_options` | Additional options for the `[mysqld]` section, as `option=value` strings. |
| `timeout` | Seconds to wait for the instance to start. Default: `60`. |

The tool deploys a standalone instance of the server on the `PATH`, of the server at `mariadbd_path`, or of the requested `server_version`, sets its `root` password, and leaves it running. For a `server_version`, it uses the server on the `PATH` if that satisfies the request, then a copy that was already downloaded, and otherwise downloads the package first, which is a few hundred megabytes. MariaDB Server therefore doesn't need to be installed.

The instance is registered as a connection for its `root` account, with the password kept in the secret store. It appears in `db.list_connections`, and the agent works with it through the `db.*` tools. The returned message confirms the deployment and names the server version when one was requested. For a server that was found or downloaded for `server_version`, the message also names the `mariadbd_path` to pass to `sandbox.start` later.

## sandbox.list_instances

Lists the instances in the default sandbox location, with their versions and status.

| Argument | Description |
| --- | --- |
| `port` | Optional. The port of a single instance to report. Leave empty to list every instance. |

Instances deployed with an explicit `sandbox_dir` aren't listed. Listing every instance asks each one for its version and probes its port, so pass a port to check a single instance, for example after starting, stopping, or deploying it.

The tool returns one entry for each instance, ordered by port, with its `port`, its server `version` as major.minor.patch (`null` if it can't be determined), and its `status`, `running` or `stopped`. With a port, it returns a list of that one instance, or an empty list when no sandbox uses the port.

## sandbox.start

Restarts an existing instance with its data intact.

| Argument | Description |
| --- | --- |
| `port` | The instance's port. |
| `sandbox_dir` | The sandbox directory. Must be in an allowed path. Leave empty for the default sandbox location. |
| `mariadbd_path` | The `mariadbd` binary, or its installation directory. For a server that `sandbox.deploy` found or downloaded for `server_version`, pass the path that its message names. |
| `timeout` | Seconds to wait for the instance to start. Default: `60`. |

If the instance has REST Daemons, the tool starts them after the instance. It returns a `message` and `restd`, with one entry for each REST Daemon of the sandbox: its `directory`, `port`, `url`, `status`, and `log_path`, and an `error` where the daemon didn't start. The instance is started even when a daemon isn't.

## sandbox.stop

Shuts an instance down gracefully.

| Argument | Description |
| --- | --- |
| `port` | The instance's port. |
| `sandbox_dir` | The sandbox directory. Must be in an allowed path. Leave empty for the default sandbox location. |
| `password` | Leave empty. The tool uses the `root` password that was stored when the instance was deployed, on Windows to request the shutdown. |
| `timeout` | Seconds to wait for the instance to stop. Default: `60`. |

If the instance has REST Daemons, the tool stops them before the instance. It returns a `message` and `restd`, with one entry for each REST Daemon of the sandbox, as `sandbox.start` returns them.

## sandbox.kill

Stops an instance forcefully.

| Argument | Description |
| --- | --- |
| `port` | The instance's port. |
| `sandbox_dir` | The sandbox directory. Must be in an allowed path. Leave empty for the default sandbox location. |

The fallback when `sandbox.stop` doesn't work. The tool also stops the instance's REST Daemons, and returns a `message` and `restd` as `sandbox.stop` does.

## sandbox.delete

Removes an instance.

| Argument | Description |
| --- | --- |
| `port` | The instance's port. |
| `sandbox_dir` | The sandbox directory. Must be in an allowed path. Leave empty for the default sandbox location. |

Refuses a running instance. Stop or kill it first. The tool deletes the instance's REST Daemon with it, and removes the connection that `sandbox.deploy` registered. It returns a `message` and `restd`, with one entry for each REST Daemon deleted, as `sandbox.start` returns them.

## sandbox.vendor

Returns the instance's vendor, `MariaDB` or `MySQL`.

| Argument | Description |
| --- | --- |
| `port` | The instance's port. |
| `sandbox_dir` | The sandbox directory. Must be in an allowed path. Leave empty for the default sandbox location. |
| `mariadbd_path` | The `mariadbd` or `mysqld` binary, or its installation directory. |

Returns `null` if the vendor can't be determined.

## sandbox.version

Returns the instance's server version.

| Argument | Description |
| --- | --- |
| `port` | The instance's port. |
| `sandbox_dir` | The sandbox directory. Must be in an allowed path. Leave empty for the default sandbox location. |
| `mariadbd_path` | The `mariadbd` binary, or its installation directory. |

Returns the version as major.minor.patch, or `null` if it can't be determined.

## Common Failures

| Symptom | Cause |
| --- | --- |
| `sandbox.deploy` doesn't return. | The sandbox directory isn't on the allowed-paths list. |
| The deploy fails on TLS. | `ssl` is `True` and `openssl` isn't installed. |

<sub>_This page is licensed: GPLv2_</sub>

{% @marketo/form formId="4316" %}
