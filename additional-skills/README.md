# Vendored MariaDB skills — sources & licensing

The skills bundled in each plugin's `skills/` folder are **vendored** — copied in
by `scripts/sync-skills.sh`, never hand-edited. To change a skill, edit it in its
source (below) or under this repo's `additional-skills/`, then re-run the sync.
The exact upstream repository, subdirectory, commit, and sync date for a given
plugin are recorded in that plugin's `skills/skills-source.json`.

## Sources

`sync-skills.sh` assembles each plugin's skills from up to three sources:

1. **MariaDB docs — agent skills** —
   [`mariadb-corporation/mariadb-docs`](https://github.com/mariadb-corporation/mariadb-docs),
   `agent-skills/` (pinned commit). Supplies the statement, function, client-tool,
   connector, and topical skill layers for the `dev` and `sql` plugins.
2. **MariaDB Shell — contributor skills** —
   [`mariadb-corporation/mariadb-shell`](https://github.com/mariadb-corporation/mariadb-shell),
   `.claude/skills/`. Supplies the `contributor` plugins.
3. **This repository — `additional-skills/`** — the repo-local skills under
   [`mariadb-corporation/ai-plugins`](https://github.com/mariadb-corporation/ai-plugins)
   `additional-skills/` (`sql/`, `rest/`, `schema-management/`), vendored flat
   alongside the upstream skills.

## Licensing

- Skill files vendored from an **external repository** (sources 1 and 2 above)
  are licensed **as indicated in their original repositories**. In particular,
  the `topical` layer of `mariadb-docs/agent-skills` is distributed under the
  **MIT** license — see that layer in the upstream repository for its
  `LICENSE`/attribution.
- Skill files sourced from this repository's **`additional-skills/`** folder
  (source 3) are licensed under the **GNU General Public License, version 2
  (GPL-2.0)** — the same license as the plugin code (see the plugin's `LICENSE`).
