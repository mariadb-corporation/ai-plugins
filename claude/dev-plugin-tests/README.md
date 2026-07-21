# MariaDB plugin test suite

Tests for the MariaDB Claude Code plugin (`../dev-plugin`), focused on the granular
**statement skills**. Four tiers:

| Tier | Marker | Needs | What it checks |
| ------ | -------- | ----- | ---------------- |
| 1. Static / structural | `static` | nothing | frontmatter, manifest↔disk consistency, cross-references, SQL fences, statement-skill contract |
| 2. SQL execution | `db` | MariaDB 11.8 | the skills' recommended DDL runs on a real server and has the documented effect (curated golden fixtures) |
| 3. Behavioral evals | `eval` | `ANTHROPIC_API_KEY` | Claude, given the skill, produces the MariaDB-preferred form (opt-in; deselected by default) |
| 4. End-to-end | `e2e` | authenticated `claude` CLI + `mariadb-shell` + PyMySQL | the real Claude Code CLI, with the plugin + MCP server loaded, builds a schema script (with the skill's Start Block), spins up a sandbox, runs the script through the MCP server, and the sandbox is torn down via a `sandbox.delete` MCP call (opt-in; deselected by default) |

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

# Tier 4 — opt-in, drives the real Claude Code CLI end-to-end
pytest -m e2e
```

Tier 4 needs an already-authenticated `claude` CLI (a logged-in session or
`ANTHROPIC_API_KEY` — override the binary with `CLAUDE_BIN`) and a `mariadb-shell`
the launcher can resolve — on `PATH` at a version ≥ the plugin's pin, or pointed
at via `MARIADB_SHELL_BIN`. It runs Claude in a throwaway project
dir (the plugin's `skills/` symlinked into `.claude/skills/` and its `.mcp.json`
passed via `--mcp-config --strict-mcp-config`), on a free ephemeral port chosen at
runtime, then verifies the `notes-app.sql` Start Block, that the sandbox is
reachable on that port, and the `notes-app` schema, before dropping the sandbox
with a real `sandbox.delete` MCP call. It self-skips when any prerequisite is
missing. The sandbox root password is pinned (told to Claude in the prompt) so
the test can connect to verify and stop it for teardown. Sandbox connection knobs:
`E2E_SANDBOX_HOST`, `E2E_SANDBOX_PORT` (pin the port instead of picking a free
one), `E2E_SANDBOX_USER` (root), `E2E_SANDBOX_PASSWORD` (test), `E2E_MODEL`,
`E2E_TIMEOUT`.

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
├── lib/mcp_stdio.py         # minimal MCP-over-stdio client (Tier 4 teardown)
├── conftest.py              # path setup + MariaDB fixtures
├── test_structure.py        # Tier 1
├── test_statements_sql.py   # Tier 2 runner
├── test_e2e_claude.py       # Tier 4 (real `claude` CLI + plugin + MCP server)
├── fixtures/<skill>.yaml     # Tier 2 golden cases (create-database & create-table filled; rest stubbed)
└── evals/                   # Tier 3 (test_behavioral.py + cases/)
```

## Adding coverage

- **New SQL case:** add to the relevant `fixtures/<skill>.yaml` (schema is documented
  at the top of `fixtures/mariadb-create-database.yaml`). The 10 non-pilot statement
  skills ship as empty stubs — fill `cases:` to extend coverage.
- **New behavioral case:** add to `evals/cases/<skill>.yaml`.
