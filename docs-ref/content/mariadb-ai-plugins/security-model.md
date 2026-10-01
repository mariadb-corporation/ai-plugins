---
description: >-
  The two allow-lists that bound what an AI agent can reach through the
  mariadb-shell MCP server, configured connections and allowed paths, and the
  account privileges you choose.
---

# Security Model

The MCP server refuses everything it hasn't been told about. Two allow-lists, both set with `mariadb-shell -- mcp setup`, make up the whole model.

## Connections

The agent can't connect to a server you haven't configured. `db.connect` checks its argument against the configured connections, and `db.list_connections` is how the agent finds out which ones exist.

Matching normalizes equivalent spellings: a `mariadb://` or `mysql://` scheme, the host name's case, the default port, and an inline password all match the stored connection. A URI that asks for more than was configured is refused:

```
root@127.0.0.1:3310/notes_app         → refused (a default schema)
root@127.0.0.1:3310?ssl-mode=REQUIRED → refused (an option)
```

The refusal is deliberate. Returning a connection that silently dropped the schema or the TLS requirement would be worse than refusing.

{% hint style="warning" %}
The allow-list controls which server the agent reaches. The MariaDB account controls what the agent can do there. Give each configured connection a dedicated account with only the privileges it needs. Read-only access to one schema is a sensible setting, and far stronger than any instruction in a prompt.
{% endhint %}

## Paths

Every tool that touches a file is limited to the allowed-paths list. This covers `db.execute_sql_script` with a `file_path`, all `msm.*` tools, and `sandbox.deploy` with a `sandbox_dir`. A path that isn't on the list falls back to an interactive confirmation, which an agent can't answer:

* The `msm.*` tools fail.
* `sandbox.deploy` stops responding.

Both mean the same thing: add the directory with `mcp setup`.

## Connections Created by Sandboxes

`sandbox.deploy` registers `root@127.0.0.1:<port>` with its password, so the agent can connect to the instance it just created. This is the only way a connection appears without you configuring it, and it points only at a local, throwaway server.

## Credentials

Passwords are stored in MariaDB Shell's secret store, which uses the platform's secret storage. They are kept separately from your regular MariaDB Shell connections and never written to a file the agent can read. The `migrator.set_config` tool refuses passwords for the same reason.
