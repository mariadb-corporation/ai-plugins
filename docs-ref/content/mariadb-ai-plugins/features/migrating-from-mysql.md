---
description: >-
  Move an application and its database from MySQL to MariaDB with MariaDB AI
  Plugins: compatibility guidance from the skills, and the optional migrator
  tools for the database migration itself.
---

# Migrating from MySQL

The plugins help with a MySQL-to-MariaDB migration at two levels: the skills explain what changes for your SQL and application code, and the optional `migrator.*` tools migrate the database itself.

## Requirements

* For compatibility guidance: any plugin with the `mysql-to-mariadb` skill, `dev` or `sql`.
* For the database migration: the `dev` plugin, and the migration tooling installed on Linux or macOS with `mariadb-shell -- mcp setup --installMigrator`.
* Connections to both the MySQL source and the MariaDB target, configured with `mcp setup`.

## Skills and Tools

| Skills | Tools |
| --- | --- |
| `mysql-to-mariadb`, `mariadb-migrator`, `mariadb-migrator-discovery`, `mariadb-migrator-configure`, `mariadb-migrator-modes`, `mariadb-migrator-run`, `mariadb-migrator-verify`, `mariadb-migrator-troubleshooting` | [`migrator.*`](../mcp-tool-reference/migrator-tools.md), `db.*`, `sandbox.*` |

## Assess Compatibility

Ask the agent what changes if you move the application from MySQL to MariaDB. It reads the `mysql-to-mariadb` skill and reviews your schema and queries for differences.

## Configure the Migration

`migrator.set_config` writes the migration configuration. It names configured connections only and refuses passwords.

## Plan and Run

1. `migrator.plan` resolves the steps and validates the configuration without changing anything.
2. `migrator.run` performs the migration.
3. If a run fails, `migrator.resume` continues it from where it stopped.

{% hint style="danger" %}
Omit `out` for every new run. A run pointed at the output directory of an earlier run reports every step as `SKIPPED`, exits with status 0, and migrates nothing. Check that every step reports `DONE`.
{% endhint %}

## Verify the Result

The `mariadb-migrator-verify` skill covers checking the finished migration on the target with the `db.*` tools: object counts per type, foreign keys, row counts, value spot checks, and signing in as each migrated account. To rehearse first, migrate into a [sandbox instance](sandbox-instances.md).
