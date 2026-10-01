---
description: >-
  The dev, sql, and contributor variants of MariaDB AI Plugins: which skills
  each one ships and which ones include the mariadb-shell MCP server.
---

# Plugin Variants

Each harness ships the same plugin variants, all built from the same sources.

| Variant | Skills | MCP server |
| --- | --- | --- |
| `dev` | The full set: SQL statements, built-in functions, command-line tools, connectors, topical skills, and all of the repository's [additional skills](skills-reference/additional-skills.md). | Yes |
| `sql` | A SQL-focused subset: SQL statements, built-in functions, topical skills, and the repository's SQL script skills. | Yes |
| `contributor` | Skills for contributing to MariaDB tooling itself, vendored from MariaDB Shell. | No |

Unless you know you need a different variant, install `dev`.

## Availability by Harness

| Harness | `dev` | `sql` | `contributor` |
| --- | --- | --- | --- |
| Claude Code | Yes | Yes | Yes |
| Codex | Yes | Yes | Yes |
| OpenCode | Yes | Yes | Yes |
| Pi | Yes | No | No |

## Skill Counts

| Variant | Skills |
| --- | --- |
| `dev` | 85 |
| `sql` | 47 |
| `contributor` | 3 |

The [Skills Reference](skills-reference/) lists every skill and the variants that ship it.

## Directory Layout

In the repository, each variant lives in `<harness>/<variant>-plugin/`, for example `claude/dev-plugin/` or `codex/sql-plugin/`. Pi's plugin lives in `pi/dev-plugin/`, with the repository-root `package.json` as its manifest.
