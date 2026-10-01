---
description: >-
  Define REST endpoints for a MariaDB schema with the MariaDB REST Service SQL
  statements, run by the agent through the mariadb-shell MCP server.
---

# REST Endpoints with MariaDB REST Service

The MariaDB REST Service turns schema objects into REST endpoints that serve and accept JSON. It is administered entirely through SQL statements, an extended `REST` grammar that MariaDB Shell understands, so the agent defines services and endpoints with the same MCP tools it uses for any other SQL.

{% hint style="warning" %}
As of MariaDB AI Plugins 26.9.5, you can define REST services and endpoints with MariaDB Shell, but the MariaDB REST Daemon that serves them isn't available.
{% endhint %}

## Requirements

* The `dev` plugin. The REST Service skills aren't part of the `sql` plugin.
* A connection to a server where the account may create schemas, because `CONFIGURE REST METADATA` creates one.

## Skills and Tools

| Skills | Tools |
| --- | --- |
| `mariadb-rest-service-create`, `mariadb-rest-service-update-endpoints`, `mariadb-rest-service-authorization`, `mariadb-rest-service-show`, `mariadb-rest-service-drop` | `db.connect`, `db.execute_sql` |

## Configure the Metadata

The agent runs `CONFIGURE REST METADATA` once per server to create the REST Service metadata schema.

## Create a Service and Endpoints

The agent creates a REST service, adds a REST schema to it, and exposes tables and views as REST data mapping views, and stored procedures and functions as REST procedures and functions.

{% hint style="warning" %}
REST Service statements depend on session state. The agent must run them one at a time with `db.execute_sql` on a single connection, not with `db.execute_sql_script`, which runs each statement in a new session.
{% endhint %}

## Control Access

The `mariadb-rest-service-authorization` skill covers requiring login on endpoints: REST authentication apps, REST users, REST roles, and the `GRANT` and `REVOKE` statements for REST privileges at the service, schema, and object level.
