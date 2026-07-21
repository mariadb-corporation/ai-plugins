# Project Context

## Project

`ai-plugins` packages MariaDB agent skills + the native `mariadb-shell` MCP server
as installable plugins for three coding agents: Claude Code (`claude/`), Codex
(`codex/`), and OpenCode (`opencode/`). Skills are vendored from
`mariadb-corporation/mariadb-docs/agent-skills` (baseline MariaDB 11.8 LTS). Each
host has a `dev-plugin` (full: all skill layers + client tools + MCP) and now a
`sql-plugin` (SQL-focused: omits client tools).

## Architecture / key decisions

- **Flat skill layout everywhere**: `skills/<skill>/SKILL.md`, regardless of the
  upstream `granular/{statements,functions,tools}` + `topical` grouping. Required
  by OpenCode (discovers skills one dir deep); keeps all plugins identical on disk.
  The vendored `.skills-manifest.json` is rewritten so `path`s point at the flat
  location while layer grouping is preserved.
- **`scripts/sync-skills.sh`** vendors from a pinned `DEFAULT_REF` into every
  plugin. `vendor_into()` takes an optional **include-list of layer keys**; empty =
  all layers (+ local `additional-skills/`). `dev` plugins get everything; `sql`
  plugins get only `granular-statements`, `granular-functions`, `topical` (no
  `granular-tools`, no `additional`).
- **`mariadb-shell` is MySQL Shell 9.7.0** (mysqlsh). Sandboxes live in
  `~/mysql-sandboxes/<port>/`. MCP tools are `sandbox.deploy/start/stop/kill/
  delete/...` and `db.connect`/`db.execute_sql`/`db.execute_sql_script`.
  `sandbox.deploy` sets a root password (blank is rejected on connect);
  `sandbox.delete` refuses a *running* instance (stop or kill first).
- **Launcher resolution order** (`mariadb-mcp-launcher.sh`/`.cmd`): (1)
  `$MARIADB_SHELL_BIN`; (2) `mariadb-shell` on PATH if version >=
  `MARIADB_SHELL_VERSION`; (3) cached download; (4) download from GitHub releases.
  Cache is keyed by version only (`~/.cache/mariadb/mariadb-shell/<ver>/`), so all
  plugins share one binary. Launcher always execs
  `mariadb-shell -- mcp start-server --transport=stdio` (stdio, not HTTP); the MCP
  configs pass NO extra args.
- Two version axes, two scripts: `set-mariadb-shell-version.sh` (binary version,
  currently `9.7.0`) and `set-plugin-version.sh` (package version, currently
  `26.7.0`, also in CHANGELOG headings + README `Version **…**`).
- `.mcp.json` is now **active** (renamed from `.mcp.json_disabled`); OpenCode uses
  `opencode.json` with `{env:MARIADB_<DEV|SQL>_PLUGIN}` substitution.

## Current state

- **Working**: all six plugins on disk (dev+sql × 3 hosts), synced to 51 skills
  (dev) / 46 (sql) from upstream `main`. sync-skills.sh, both version scripts,
  launchers with PATH-preference + stdio invocation, marketplace registration for
  `sql`. `.mcp.json` files enabled.
- **Tests (claude/dev-plugin-tests)**: Tier 1 `static` (423 pass), Tier 2 `db`
  (self-skips w/o server), Tier 3 `eval` (opt-in), Tier 4 `e2e` (opt-in) — the new
  end-to-end test **passes for real** (drives `claude` CLI + plugin + MCP; builds
  schema, deploys sandbox on random port, verifies `notes-app` schema, tears down
  via `sandbox.delete`).
- **Not committed**: everything is uncommitted on branch `wip/AIPL-4` (see Git
  state). No commits made this session.
- **Known**: `sql-plugin` folders + many new skill dirs are still untracked.
  `codex/opencode` have their own `dev-plugin-test(s)` dirs that were NOT updated
  with the e2e tier (only `claude/dev-plugin-tests`). Their READMEs still say "24
  skills" in the test docs.

## Files that matter

- `scripts/sync-skills.sh` -> vendors skills into all plugins; include-list logic.
- `scripts/set-mariadb-shell-version.sh` -> sets `MARIADB_SHELL_VERSION` across configs/launchers/READMEs.
- `scripts/set-plugin-version.sh` -> sets package version in plugin.json + READMEs.
- `claude/dev-plugin/scripts/mariadb-mcp-launcher.sh` / `.cmd` -> canonical launchers (copied to all 6 plugins).
- `claude/dev-plugin-tests/test_e2e_claude.py` -> Tier 4 e2e test.
- `claude/dev-plugin-tests/lib/mcp_stdio.py` -> minimal MCP-over-stdio client (e2e teardown/discovery).
- `claude/dev-plugin-tests/lib/skills.py` -> skill/manifest parsing; `see_also_refs()` is backtick-only.
- `claude/dev-plugin-tests/test_structure.py` -> Tier 1; statement-count guardrail == 31.
- `additional-skills/mariadb-schema-create-script/SKILL.md` -> defines the SQL "Start Block" the e2e asserts.
- `.claude-plugin/marketplace.json`, `.codex-plugin/marketplace.json` -> list `dev` + `sql`.

## Next steps

1. Decide whether to commit; stage the untracked `sql-plugin/` dirs, new skill dirs, test files, and scripts.
2. Optionally propagate the e2e tier (or at least the "24 skills" doc fixes) to `codex/dev-plugin-test` and `opencode/dev-plugin-test`.
3. Optionally add the `sql` plugins to the root `README.md` plugin table.
4. Confirm the unusual version numbers (`9.7.0` shell / `26.7.0` package) are intended.
5. Run `pytest -m e2e` in CI only where `claude` + `mariadb-shell` + creds exist (it self-skips otherwise).

## Gotchas / things not to repeat

- e2e teardown: **cannot** `sandbox.delete` a running instance — must `sandbox.stop`
  (needs root password) or `sandbox.kill` first. First real run left a sandbox on
  56163 that had to be manually killed+deleted.
- Sandbox root password is **not blank** — pin it (test uses `test`, passed to
  Claude in the prompt) or pymysql/db.connect gets "Access denied … using
  password: NO".
- `see_also_refs()` false-positived on `mariadb.com/docs` URL path segments
  (`…/mariadb-binlog-options`); fixed by matching only backtick-wrapped skill names.
- Re-running `sync-skills.sh` bumps `synced_at` in every `skills-source.json` even
  with no content change — revert dev-plugin provenance churn if scope is sql-only.
- macOS `sort -V` is unreliable; the launcher's `version_ge` is pure bash.
- The `/checkpoint` command's `git -C $1` expects a path arg; invoked bare, `$1` is
  empty — used repo root instead.

## Git state

Branch: `wip/AIPL-4`

Modified (tracked): root `.DS_Store`, both `marketplace.json`, `scripts/sync-skills.sh`,
and per dev-plugin (× claude/codex/opencode): `plugin.json`/`opencode.json`,
`CHANGELOG.md`, `README.md`, launcher `.sh`/`.cmd`(+`_disabled`), `skills-source.json`,
`skills/.skills-manifest.json`, and the `mariadb-json-functions` + `mariadb-numeric-functions`
SKILL.md. Renamed: `claude|codex/dev-plugin/.mcp.json_disabled -> .mcp.json`.
Test suite: `claude/dev-plugin-tests/{README.md,pyproject.toml,lib/skills.py,test_structure.py}`.

Untracked: `.claude/commands/`, `scripts/set-mariadb-shell-version.sh`,
`scripts/set-plugin-version.sh`, `claude/dev-plugin-tests/{test_e2e_claude.py,lib/mcp_stdio.py}`,
`{claude,codex,opencode}/sql-plugin/`, ~26 new skill dirs per host under
`{claude,codex,opencode}/dev-plugin/skills/` (mariadb-alter-user, -binlog, -call,
-client, -control-flow-functions, -create-function/-procedure/-sequence/-trigger/-user,
-drop-user, -encryption-functions, -explain, -grant, -information-functions,
-lock-tables, -prepare, -rename-table, -revoke, -set, -set-transaction, -show,
-transactions, -truncate-table, -vector-functions, -window-functions), plus stray `.DS_Store`.
