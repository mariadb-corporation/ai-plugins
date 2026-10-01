---
description: >-
  Deploy local, throwaway MariaDB Server instances through the mariadb-shell
  MCP server, without Docker, a container runtime, or administrator rights.
---

# Sandbox Instances

The MCP server can deploy throwaway MariaDB Server instances on your machine. A sandbox needs no Docker, no container runtime, and no administrator rights, and is the quickest way to give the agent a server to work against.

## Deploy a Sandbox

Ask the agent:

```
Deploy a MariaDB sandbox on port 3310.
```

The agent calls `sandbox.deploy`. The sandbox's connection is registered with the MCP server automatically, so the agent can connect to it without running `mcp setup` again.

## Server Versions

MariaDB Server doesn't need to be installed. `sandbox.deploy` looks for a server in this order:

1. A `mariadbd` on the `PATH`.
2. A version the sandbox has already downloaded.
3. The published index of MariaDB Server releases, from which it downloads a package, verifies its SHA-256 checksum, and unpacks it.

To ask for a version, give a full or partial version number, such as `11.8.9`, `11.8`, or `11`; each is satisfied by the newest release that matches. To see what is available for your platform, ask:

```
Which MariaDB server versions can you deploy?
```

The agent calls `sandbox.list_available_versions`.

## Sandbox Lifecycle

| Action | Tool | Notes |
| --- | --- | --- |
| Deploy | `sandbox.deploy` | Creates and starts an instance, and registers its connection. |
| Stop | `sandbox.stop` | Graceful shutdown. |
| Start | `sandbox.start` | Restarts an existing instance with its data intact. |
| Stop forcefully | `sandbox.kill` | The fallback when `sandbox.stop` doesn't work. |
| Delete | `sandbox.delete` | Removes the instance. Refuses a running instance. |

{% hint style="warning" %}
A downloaded server isn't on the `PATH`. To restart its sandbox, `sandbox.start` needs the `mariadbd_path` that the deploy reported, and to shut it down, use `sandbox.kill`; `sandbox.stop` can't find the binary. The deploy message says so at the time.
{% endhint %}

See [sandbox Tools](../mcp-tool-reference/sandbox-tools.md) for every argument.

## File Locations

| What | Linux and macOS | Windows |
| --- | --- | --- |
| Instances | `~/.mariadb-shell/sandboxes/<port>/` | `%USERPROFILE%\MariaDB\mariadb-shell\sandboxes\<port>\` |
| Downloaded servers | `~/.local/share/mariadb-sandbox-server/` | `%LOCALAPPDATA%\Programs\mariadb-sandbox-server\` |

## Security Considerations

{% hint style="danger" %}
A sandbox creates a `root@'%'` account and listens on all network interfaces. It is a development tool. Don't leave one running on an untrusted network.
{% endhint %}

* A sandbox is deployed without TLS, so command-line clients may need `--skip-ssl`.
* The connection a sandbox registers is the only connection that appears without you configuring it. It points only at the local instance the agent just created.
