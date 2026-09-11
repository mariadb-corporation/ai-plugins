---
order: 4
slug: sandbox-lifecycle
title: "Throwaway MariaDB servers with the sandbox.* tools"
description: >-
  Deploy, start, stop, kill and delete local MariaDB instances on demand — no
  Docker, no container runtime, no administrator rights. The safety net that
  lets an agent try a destructive change before it touches anything real.
level: beginner
duration: "20 min"
area: sandbox
tools: ["sandbox.list_available_versions", "sandbox.deploy", "sandbox.start", "sandbox.stop", "sandbox.kill", "sandbox.delete", "sandbox.version"]
skills: ["mariadb-features"]
path_label: "Operate and Optimize, Step 1"
prerequisites:
  - "A plugin installed and `mariadb-shell -- mcp setup` run once."
  - "Nothing else. A sandbox needs no MariaDB Server on the machine — it downloads one if it has to."
---

The single most useful thing about giving an agent database tools is also the
scariest, and the `sandbox.*` group is the answer to both. Seven tools that
create and destroy complete MariaDB server instances in a folder, so "try this
migration first" is a real option rather than a wish.

<div class="prompt" markdown="1">
*Spin up a MariaDB sandbox on port 3310 with root password `demo-pw`, tell me
what version it is, and leave it running.*
</div>

## What a sandbox actually is

A directory with a data directory and a config file in it, plus a running
`mariadbd`.

That server does **not** have to be installed on the machine. `sandbox.deploy`
resolves one from three places, **in this order**, and the order is the design:

1. **The `PATH`.** A machine that already satisfies the request downloads
   nothing.
2. **Versions already downloaded**, one directory per version under
   `~/.local/share/mariadb-sandbox-server/` (on Windows,
   `%LOCALAPPDATA%\Programs\mariadb-sandbox-server`).
3. **The published index** — fetch, verify the SHA-256 as the body streams past,
   unpack, then use it.

<div class="callout callout--tip" markdown="1">
**The `PATH` is deliberately not held to "newest".** It holds one server, and
the only question is whether it satisfies what you asked for. A machine with
11.8.9 installed will not fetch 11.8.10 because you said `11`. Already-downloaded
copies and the index *do* take the newest match.
</div>

```text
~/.mariadb-shell/sandboxes/3310/                     # macOS and Linux
%USERPROFILE%\MariaDB\mariadb-shell\sandboxes\3310\  # Windows
```

There is no image, no container daemon and no root requirement, and cleanup is a
directory removal. The port doubles as the instance's name: every tool takes
`port`, and that is how it finds the instance.

## Pick a version — `sandbox.list_available_versions`

```text
sandbox.list_available_versions()                 → the newest patch of each series
sandbox.list_available_versions(series="11.8")    → every 11.8 patch release
sandbox.list_available_versions(series="11")      → every release under 11
```

With no argument you get **one version per release series** — the newest patch
of each. Pass a series to see every release below it.

Only versions with a package built for **your** platform are listed, and
anything listed can always be deployed: if it is not on the machine already,
`sandbox.deploy` fetches it.

<div class="callout" markdown="1">
**The index is a static file inside the plugin, not a live lookup.** What a given
plugin version can install is therefore reproducible and reviewable in a diff,
and listing costs no network. The flip side: publishing a new server version
means shipping a new plugin.
</div>

## Deploy — `sandbox.deploy`

```text
sandbox.deploy(port=3310, password="demo-pw", ssl=False)
```

The parameters worth knowing:

| Parameter | Notes |
| --- | --- |
| `port` | Required. Also the instance's identity for every other tool. |
| `password` | The `root` password. **Never leave it blank** — see below. |
| `server_version` | The release to run — `11.8.9`, `11.8` or `11`. Each level you leave off is satisfied by the newest release below it; a leading `v` is fine. **Cannot be combined with `mariadbd_path`**: both name the server to run. |
| `ssl` | Defaults to `False`. Turning it on needs `openssl` on the machine. |
| `sandbox_dir` | Put the instance somewhere other than the default root. Must be on the allowed-paths list. |
| `allow_root_from` | Which hosts the `root` account may connect from. |
| `mariadbd_options` | Extra server options — how you test a non-default setting. |
| `timeout` | How long to wait for the server to come up. |

Three things happen on a successful deploy:

1. A server is resolved (see above), the data directory is initialized and
   `mariadbd` starts. The deploy's own message names where the server came from
   — **found on the PATH**, **already downloaded**, or **downloaded now** —
   because two seconds and two minutes deserve different explanations.
2. A `root@'%'` account is created and the server listens on **all interfaces**.
3. The connection `root@127.0.0.1:<port>` is **registered with the MCP server**,
   with its password in the shell's secret store — so `db.connect` works
   immediately, with no `mcp setup` run in between.

<div class="callout callout--warn" markdown="1">
**Three ways a deploy goes wrong, and what each looks like**

- **It hangs.** The sandbox directory is not on the allowed-paths list. The path
  guard falls back to an interactive confirmation that a headless agent cannot
  answer, so the call never returns. Add the directory with
  `mariadb-shell -- mcp setup`.
- **It succeeds, but nothing can connect.** The password was blank.
  `db.connect` refuses the registered connection, and the error reads like an
  allow-list problem. Always pass a password.
- **It fails on TLS.** `ssl: True` without `openssl` on the machine. Deploy with
  `ssl: False`, which is the default, unless you are specifically testing TLS.
- **It refuses `server_version` and `mariadbd_path` together.** Both name the
  server to run, so the tool will not guess which you meant.
</div>

<div class="callout callout--warn" markdown="1">
**A downloaded server is not on your `PATH`, and two tools need to know that.**
`sandbox.start` has to be given the same `mariadbd_path` the deploy reported, and
**shutdown needs `sandbox.kill` rather than `sandbox.stop`** — the shell's stop
path takes no `mariadbdPath` and so cannot find the binary. The deploy message
tells you both. It does not apply to a server that came from the `PATH`.
</div>

Because it listens on all interfaces with a `root@'%'` account, a sandbox is a
development tool. Do not leave one running on a machine on an untrusted network.

## Stop, start, delete — the lifecycle

```text
sandbox.stop(port=3310, password="demo-pw")   # graceful; needs the password
sandbox.start(port=3310)                      # bring the same data back up
sandbox.kill(port=3310)                       # forceful; when stop will not
sandbox.delete(port=3310)                     # remove the directory for good
```

The rules that matter:

- **`stop` needs the root password.** It shuts the server down through the
  server, not by signalling the process.
- **`delete` refuses a running instance.** This is on purpose. Stop first; if
  stop fails, `kill` and then `delete`.
- **`start` is not `deploy`.** `start` brings an existing instance back with its
  data intact. `deploy` on a port that already has an instance is an error, not
  an overwrite.

<div class="callout callout--tip" markdown="1">
**Always clean up in the same breath as you create.** An agent whose run times
out leaves the server running and the directory behind, and the next `deploy` on
that port fails for reasons that look unrelated. Make the teardown part of the
instruction: *"…and delete the sandbox when you are done, even if a step fails."*
</div>

## Check what you got — `sandbox.version` and `sandbox.vendor`

```text
sandbox.version(port=3310)   → "11.8.x"
sandbox.vendor(port=3310)    → "MariaDB"
```

`sandbox.vendor` exists because the sandbox machinery can also stand up a
**MySQL** instance. That is what makes the MySQL-to-MariaDB migration tutorial
runnable on one laptop: a MySQL source and a MariaDB target, both throwaway.

## Put it to work: rehearse a destructive change

This is the pattern the whole group exists for.

<div class="prompt" markdown="1">
*I need to add a `NOT NULL` column with a default to a 50-million-row table on
production. Before we do anything: deploy a sandbox on 3311, recreate the table
structure there, fill it with a few million rows, and measure what the `ALTER`
actually does — which algorithm it picks, whether it locks, and how long it
takes. Then tell me whether it is safe to run online.*
</div>

The agent will reach for the `mariadb-alter-table` skill, which is where it
learns about `ALGORITHM=INSTANT`, `ALGORITHM=NOCOPY`, `LOCK=NONE` and
`ALTER ONLINE TABLE` — and it will find out by *running* it rather than by
asserting it. That is a rehearsal you could not easily do by hand, and it costs
one sandbox.

Other jobs in the same shape:

- **Test a version upgrade, or check compatibility across releases.** Two
  sandboxes on different `server_version`s and the same script on both — that is
  [Tutorial 10](../compare-server-versions/).
- **Reproduce a bug on a clean server.** No local state, no "works on my
  machine".
- **Try a config change.** `mariadbd_options` on deploy, then measure.
- **Review a pull request's migration.** Apply it to a sandbox seeded with the
  current schema, and see what it does.

## Tidy up

<div class="prompt" markdown="1">
*List the sandboxes you have created in this session and delete all of them.*
</div>

Then check the directory yourself — `~/.mariadb-shell/sandboxes/` — because an
orphan from a timed-out run will still be sitting there.

<h2 class="no-step" id="what-you-built">What you learned</h2>

- A sandbox is a folder plus a `mariadbd` from your local install. No Docker, no
  root, and cleanup is a delete.
- `deploy` registers its connection automatically; `stop` needs the password;
  `delete` refuses a running instance; `kill` is the fallback.
- A hanging deploy means allowed paths; a connectable-but-refused one means a
  blank password.
- The real payoff is rehearsal: dangerous changes get tried somewhere that does
  not matter first.

**Where to go next**

- [Diagnose a slow query](../diagnose-a-slow-query/) — a sandbox is also where
  you test an index without touching production.
- [Migrate from MySQL](../mysql-to-mariadb-migration/) — two sandboxes, one
  MySQL, one MariaDB, one migration.
