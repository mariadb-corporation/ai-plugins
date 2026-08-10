# MariaDB plugin test suite

Tests for the MariaDB OpenCode plugin (`../dev-plugin`), focused on the granular
**statement skills**. Three tiers:

| Tier | Marker | Needs | What it checks |
| ------ | -------- | ----- | ---------------- |
| 1. Static / structural | `static` | nothing | frontmatter, manifest↔disk consistency, cross-references, SQL fences, statement-skill contract — over all 24 skills |
| 2. SQL execution | `db` | `mariadb-shell` + a server binary | the skills' recommended DDL runs on a real server and has the documented effect (curated golden fixtures) — against a sandbox instance the suite deploys itself |
| 3. Behavioral evals | `eval` | `ANTHROPIC_API_KEY` | a Claude model (OpenCode is most commonly run on Claude), given the skill, produces the MariaDB-preferred form (opt-in; deselected by default) |

## Setup

Only needed when driving pytest directly — the repo-root `run_tests.py` installs
these into the `mariadb-shell` Python itself.

```sh
pip install -r requirements.txt        # from this directory
```

## Run

**Preferred:** the repo-root [`run_tests.py`](../../run_tests.py) runs this suite (and
its sibling suites) with the Python that ships inside `mariadb-shell`, installs the
requirements below into it, and writes a combined coverage report:

```sh
../../run_tests.py opencode            # this suite, default tiers
../../run_tests.py opencode -m static  # one tier
```

To drive pytest directly from this directory instead:

```sh
# Tier 1 — fast, no services
pytest -m static

# Tier 2 — deploys its own throwaway sandbox instance
pytest -m db

# Tier 2 against a server of your own instead (docker-compose.yml provided)
docker compose -f docker-compose.yml up -d
MARIADB_PASSWORD=test pytest -m db
docker compose -f docker-compose.yml down -v

# Tier 3 — opt-in, calls the Anthropic API
ANTHROPIC_API_KEY=... pytest -m eval
```

By default (`pytest`) the eval tier is deselected, so `static` + `db` run when a
DB is reachable (and `db` cases self-skip when it isn't).

### MariaDB connection (Tier 2)

By default the tier needs nothing running: it deploys a throwaway **sandbox
instance** on a free port through the `mariadb-shell` MCP server's `sandbox.*`
tools (`lib/sandbox.py`) and deletes it when the session ends. The shell's user
config home is isolated to a temp dir for the run — the real one's plugins
symlinked in, the sandbox dir allow-listed — so `~/.mariadb-shell` is left alone.
It needs a `mariadb-shell` (on `PATH`, or `MARIADB_SHELL_BIN` / `MARIADB_SHELL`)
and a `mariadbd`/`mysqld` on `PATH` for the instance to start;
`MARIADB_SANDBOX_MARIADBD` pins that binary. Without them the tier skips.

Setting any of `MARIADB_HOST` (127.0.0.1), `MARIADB_PORT` (3306), `MARIADB_USER`
(root) or `MARIADB_PASSWORD` (test) runs against that already-started server
instead — the `docker-compose.yml` service, CI's service container, or any
reachable MariaDB 11.x — and skips if it is unreachable.

### Model (Tier 3)

Defaults to `claude-opus-4-8`; override with `EVAL_MODEL` to whatever model your
Anthropic key can reach. The harness sends no `temperature` (rejected on Opus 4.8)
and uses `output_config={"effort": "low"}` as the determinism lever; the assertions
are tolerant of minor sampling variation.

## Layout

```text
opencode/dev-plugin-test/
├── lib/skills.py            # shared SKILL.md / manifest parsing
├── conftest.py              # path setup + MariaDB fixtures
├── test_structure.py        # Tier 1
├── test_statements_sql.py   # Tier 2 runner
├── fixtures/<skill>.yaml     # Tier 2 golden cases (create-database & create-table filled; rest stubbed)
└── evals/                   # Tier 3 (test_behavioral.py + cases/)
```

The plugin vendors its skills in a **flat** layout (OpenCode discovers skills one
directory deep), and the vendored `.skills-manifest.json` records the flat paths —
so the manifest-driven loaders in `lib/skills.py` work unchanged.

## Adding coverage

- **New SQL case:** add to the relevant `fixtures/<skill>.yaml` (schema is documented
  at the top of `fixtures/mariadb-create-database.yaml`). The 10 non-pilot statement
  skills ship as empty stubs — fill `cases:` to extend coverage.
- **New behavioral case:** add to `evals/cases/<skill>.yaml`.
