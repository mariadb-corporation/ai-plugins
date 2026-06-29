# MariaDB plugin test suite

Tests for the MariaDB Claude Code plugin (`../dev-plugin`), focused on the granular
**statement skills**. Three tiers:

| Tier | Marker | Needs | What it checks |
| ------ | -------- | ----- | ---------------- |
| 1. Static / structural | `static` | nothing | frontmatter, manifest↔disk consistency, cross-references, SQL fences, statement-skill contract — over all 24 skills |
| 2. SQL execution | `db` | MariaDB 11.8 | the skills' recommended DDL runs on a real server and has the documented effect (curated golden fixtures) |
| 3. Behavioral evals | `eval` | `ANTHROPIC_API_KEY` | Claude, given the skill, produces the MariaDB-preferred form (opt-in; deselected by default) |

## Setup

```sh
pip install -r requirements.txt        # from this directory
```

## Run

```sh
# Tier 1 — fast, no services
pytest -m static

# Tier 2 — needs a MariaDB 11.8 server
docker compose -f docker-compose.yml up -d
MARIADB_PASSWORD=test pytest -m db
docker compose -f docker-compose.yml down -v

# Tier 3 — opt-in, calls the Anthropic API
ANTHROPIC_API_KEY=... pytest -m eval
```

By default (`pytest`) the eval tier is deselected, so `static` + `db` run when a
DB is reachable (and `db` cases self-skip when it isn't).

### MariaDB connection (Tier 2)

Configured via env vars, defaulting to the `docker-compose.yml` service:
`MARIADB_HOST` (127.0.0.1), `MARIADB_PORT` (3306), `MARIADB_USER` (root),
`MARIADB_PASSWORD` (test). Any reachable MariaDB 11.x works.

### Model (Tier 3)

Defaults to `claude-opus-4-8`; override with `EVAL_MODEL`. Note `temperature` is
rejected on Opus 4.8, so the harness uses `effort: "low"` for determinism.

## Layout

```text
claude/dev-plugin-tests/
├── lib/skills.py            # shared SKILL.md / manifest parsing
├── conftest.py              # path setup + MariaDB fixtures
├── test_structure.py        # Tier 1
├── test_statements_sql.py   # Tier 2 runner
├── fixtures/<skill>.yaml     # Tier 2 golden cases (create-database & create-table filled; rest stubbed)
└── evals/                   # Tier 3 (test_behavioral.py + cases/)
```

## Adding coverage

- **New SQL case:** add to the relevant `fixtures/<skill>.yaml` (schema is documented
  at the top of `fixtures/mariadb-create-database.yaml`). The 10 non-pilot statement
  skills ship as empty stubs — fill `cases:` to extend coverage.
- **New behavioral case:** add to `evals/cases/<skill>.yaml`.
