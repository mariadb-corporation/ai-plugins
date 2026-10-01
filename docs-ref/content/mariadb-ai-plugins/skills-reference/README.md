---
description: >-
  Reference for every skill the MariaDB AI Plugins ship, by layer: SQL
  statements, built-in functions, command-line tools, connectors, topical
  skills, and the repository's own skills.
---

# Skills Reference

A skill is a Markdown document the agent reads when the request matches its description. Skills need no database and no configuration, and work offline.

## How the Agent Uses Skills

Each skill has a name and a description. The harness shows the agent the descriptions, and the agent reads a skill in full only when it becomes relevant: a request for a `CREATE TABLE` statement loads `mariadb-create-table`, and a question about vector search loads `mariadb-vector`. You don't select skills yourself.

## Skill Layers

| Layer | Skills | Plugins | Source |
| --- | --- | --- | --- |
| [SQL Statements](sql-statement-skills.md) | 31 | `dev`, `sql` | MariaDB documentation |
| [Built-in Functions](built-in-function-skills.md) | 10 | `dev`, `sql` | MariaDB documentation |
| [Command-Line Tools](command-line-tool-skills.md) | 4 | `dev` | MariaDB documentation |
| [Connectors](connector-skills.md) | 14 | `dev` | MariaDB documentation |
| [Topical](topical-skills.md) | 5 | `dev`, `sql` | MariaDB documentation |
| [Additional](additional-skills.md) | 21 | `dev`; one also in `sql` | MariaDB AI Plugins repository |
| [Contributor](contributor-skills.md) | 3 | `contributor` | MariaDB Shell repository |

The skills are verified against MariaDB 11.8 LTS.

## Skill Versions

Skills are vendored into each plugin at release time, so a plugin version always ships the same skill text. Each plugin records the exact source repository, commit, and sync date of its skills in `skills/skills-source.json`.
