# Project Context

## Project

`ai-plugins` packages MariaDB agent skills + the native `mariadb-shell` MCP server
as installable plugins for three coding agents: Claude Code (`claude/`), Codex
(`codex/`), and OpenCode (`opencode/`). Skills are vendored from
`mariadb-corporation/mariadb-docs/agent-skills` (baseline MariaDB 11.8 LTS). Each
host has a `dev-plugin` (full: all skill layers + client tools + connectors + MCP)
and a `sql-plugin` (SQL-focused: statements+functions+topical only).

## Architecture / key decisions

- **Flat skill layout everywhere**: `skills/<skill>/SKILL.md`, regardless of the
  upstream `granular/{statements,functions,tools,connectors}` + `topical` grouping.
  Required by OpenCode (skills discovered one dir deep); keeps plugins identical on
  disk. Vendored `.skills-manifest.json` is rewritten so `path`s are flat while
  layer grouping is preserved.
- **`scripts/sync-skills.sh`** vendors from a pinned `DEFAULT_REF` into every
  plugin. `vendor_into()` takes an optional **include-list of layer keys**: empty =
  all layers (+ local `additional-skills/`) = dev behavior; sql passes
  `SQL_INCLUDE_LAYERS=(granular-statements granular-functions topical)`. So
  `granular/tools`, `granular/connectors`, and `additional` are **dev-only** — no
  code change needed to route a new dev-only layer, just its absence from the
  include-list.
- **`mariadb-shell` is MySQL Shell 9.7.0** (mysqlsh). Sandboxes live in
  `~/mysql-sandboxes/<port>/`. MCP tools: `sandbox.deploy/start/stop/kill/delete/
  vendor/version`, `db.connect`/`db.execute_sql`/`db.execute_sql_script`/`db.close`,
  `msm.*`. `sandbox.deploy` sets a root password (blank rejected on connect);
  `sandbox.delete` refuses a *running* instance (stop or kill first).
- **Launcher resolution order** (`mariadb-mcp-launcher.sh`/`.cmd`): (1)
  `$MARIADB_SHELL_BIN`; (2) `mariadb-shell` on PATH if version >=
  `MARIADB_SHELL_VERSION` (pure-bash `version_ge`, not `sort -V`); (3) cached
  download; (4) GitHub release download. Cache keyed by version only
  (`~/.cache/mariadb/mariadb-shell/<ver>/`) → all plugins share one binary.
  Always execs `mariadb-shell -- mcp start-server --transport=stdio`; MCP configs
  pass NO extra args (`.mcp.json` "args": []; opencode command has no "mcp").
- Two version axes / two scripts: `set-mariadb-shell-version.sh` (binary,
  `9.7.0`) and `set-plugin-version.sh` (package, `26.7.0`; also CHANGELOG headings
  + README `Version **…**`).
- `.mcp.json` is **active** (renamed from `.mcp.json_disabled`); OpenCode uses
  `opencode.json` with `{env:MARIADB_<DEV|SQL>_PLUGIN}` substitution.

## Current state

- **Working**: 6 plugins (dev+sql × 3 hosts) synced at upstream ref `1513b3b`.
  Counts: **dev = 58 skills** (incl. 7 new `granular/connectors`), **sql = 46**
  (connectors + tools + additional excluded). Marketplace registers `dev` + `sql`
  (claude/codex). Launchers do PATH-preference + stdio invocation.
- **Tests**: only `claude/dev-plugin-tests` has the Tier 4 `e2e` test; all three
  suites (`claude/dev-plugin-tests`, `codex/dev-plugin-test`,
  `opencode/dev-plugin-test`) pass `pytest -m static` = **472 passed** each. Tier 4
  e2e **passed for real** earlier (drives `claude` CLI + plugin + MCP; schema +
  sandbox + `notes-app` verified + torn down via `sandbox.delete`).
- **CI workflows**: `.github/workflows/{claude,codex,opencode}-test.yml`; each runs
  `pytest -m static|db|eval -ra`. `test.yml` was renamed to `claude-test.yml`
  (internal `name:` now `claude-tests`).
- **Git**: connector additions + manifest/provenance + `sync-skills.sh` are
  **staged** (see Git state). Prior session work (sql-plugin, version scripts, test
  files, launcher/MCP changes, workflow rename) appears already committed. Branch
  `wip/AIPL-4`.
- **Known/not done**: e2e tier is claude-only (not propagated to codex/opencode).
  Root `README.md` plugin table lists only `dev` plugins, not `sql`. Codex/opencode
  test-suite READMEs may still reference stale skill counts. Unusual version
  numbers (`9.7.0` shell / `26.7.0` package) unconfirmed as intentional.

## Files that matter

- `scripts/sync-skills.sh` -> vendors skills; include-list logic; `DEFAULT_REF=1513b3b`.
- `scripts/set-mariadb-shell-version.sh` -> sets `MARIADB_SHELL_VERSION` across configs/launchers/READMEs.
- `scripts/set-plugin-version.sh` -> sets package version in plugin.json + READMEs.
- `claude/dev-plugin/scripts/mariadb-mcp-launcher.sh`/`.cmd` -> canonical launchers (copied to all 6 plugins).
- `claude/dev-plugin-tests/test_e2e_claude.py` -> Tier 4 e2e (opt-in `-m e2e`).
- `claude/dev-plugin-tests/lib/mcp_stdio.py` -> minimal MCP-over-stdio client (e2e teardown/discovery).
- `{claude,codex,opencode}/dev-plugin-test(s)/lib/skills.py` -> `see_also_refs()` backtick-only.
- `{claude,codex,opencode}/dev-plugin-test(s)/test_structure.py` -> statement-count guardrail == 31.
- `additional-skills/mariadb-schema-create-script/SKILL.md` -> defines the SQL "Start Block" the e2e asserts.

## Next steps

1. Commit the staged connector sync (message: bump ref to 1513b3b, add granular/connectors to dev).
2. Optionally propagate the e2e tier + stale-count doc fixes to codex/opencode suites.
3. Optionally add `sql` plugins to root `README.md` table; add sql to any CI matrix.
4. Confirm version numbers `9.7.0` / `26.7.0` are intended.
5. If a branch-protection rule required a check named `tests`, repoint it to `claude-tests`.

## Gotchas / things not to repeat

- New dev-only upstream layers need NO logic change — dev vendors all layers; only
  ensure the layer key is absent from `SQL_INCLUDE_LAYERS`. Just bump `DEFAULT_REF`.
- e2e teardown: cannot `sandbox.delete` a running instance — `sandbox.stop` (needs
  root password) or `sandbox.kill` first. First real run leaked a sandbox on 56163.
- Sandbox root password is NOT blank — pin it (`test`, passed to Claude in the
  prompt) or connect fails "Access denied … using password: NO".
- `see_also_refs()` false-positived on `mariadb.com/docs` URL slugs
  (`…/mariadb-binlog-options`); fixed to match only backtick-wrapped skill names.
- Statement-count guardrail is hardcoded (`== 31`) in all 3 suites — bump on any
  re-sync that changes the statements layer.
- Re-running `sync-skills.sh` bumps `synced_at` in every `skills-source.json`.
- macOS `sort -V` unreliable → launcher uses pure-bash `version_ge`.
- `/checkpoint` command's step-1 `git -C status` is malformed (missing path arg);
  ran with repo root instead.

## Git state

Branch: `wip/AIPL-4`

Staged (index):
- `scripts/sync-skills.sh` (M)
- per dev-plugin × claude/codex/opencode: `skills-source.json` (M),
  `skills/.skills-manifest.json` (M), and 7 new
  `skills/mariadb-connector-{c,cpp,j,nodejs,odbc,python,r2dbc}/SKILL.md` (A)
- per sql-plugin × claude/codex/opencode: `skills-source.json` (M),
  `skills/.skills-manifest.json` (M) — provenance/manifest churn only (synced_at +
  path flattening), no connector content

Working tree otherwise clean; nothing unstaged/untracked.
