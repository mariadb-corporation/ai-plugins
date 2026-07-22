# Project Context

## Project

`ai-plugins` packages MariaDB agent skills (+ the native `mariadb-shell` MCP
server) as installable plugins for three coding agents: Claude Code (`claude/`),
Codex (`codex/`), OpenCode (`opencode/`). Each agent has three plugin variants:
`dev` (full skills + MCP), `sql` (SQL-focused subset + MCP), and `contributor`
(skills-only, from a different source repo). Skills are vendored (never hand-
edited) by `scripts/sync-skills.sh`.

## Architecture / key decisions

- **Flat skill layout everywhere**: `skills/<skill>/SKILL.md`, regardless of
  upstream grouping. Required by OpenCode (skills discovered one dir deep); keeps
  plugins identical on disk. Vendored `.skills-manifest.json` rewritten to flat
  paths, layer grouping preserved.
- **Two skill sources**:
  - `dev`/`sql` ← `mariadb-corporation/mariadb-docs` `agent-skills/` (has a
    manifest with layers). Pinned `DEFAULT_REF`.
  - `contributor` ← `mariadb-corporation/mariadb-shell` `.claude/skills/` (PRIVATE,
    NO manifest → scan every `SKILL.md`). Fetched via GitHub API tarball with
    `GH_TOKEN`/`gh auth token`; best-effort — warns+skips (exit 0) if no token.
    `CONTRIB_REF` defaults to `main`.
- **`vendor_into()` include-list**: empty = all layers (+ local additional-skills)
  = `dev`; `sql` passes `SQL_INCLUDE_LAYERS=(granular-statements granular-functions
  topical)`. So `granular/tools`, `granular/connectors`, `additional` are dev-only
  — a new dev-only upstream layer needs NO code change, just bump the ref.
  `vendor_contributor_into()` is a separate manifest-less vendorer.
- **`mariadb-shell` is MySQL Shell 9.7.0** (mysqlsh). Sandboxes in
  `~/mysql-sandboxes/<port>/`. MCP tools: `sandbox.deploy/start/stop/kill/delete/
  vendor/version`, `db.connect/execute_sql/execute_sql_script/close`, `msm.*`.
  `sandbox.deploy` sets a root password (blank rejected on connect);
  `sandbox.delete` refuses a running instance (stop/kill first).
- **Launcher** (`mariadb-mcp-launcher.sh`/`.cmd`, dev+sql only): resolves
  `$MARIADB_SHELL_BIN` → PATH `mariadb-shell` if version >= `MARIADB_SHELL_VERSION`
  (pure-bash `version_ge`) → version-keyed cache → GitHub release. Always execs
  `mariadb-shell -- mcp start-server --transport=stdio`; MCP configs pass no args.
  `.mcp.json` active (renamed from `_disabled`).
- Version axes: `set-mariadb-shell-version.sh` (binary `9.7.0`),
  `set-plugin-version.sh` (package `26.7.0`; also CHANGELOG + README).

## Current state

- **9 plugin dirs** (dev+sql+contributor × 3 hosts). Synced counts: dev = 58
  (incl. 7 `granular/connectors`), sql = 46, contributor = 1
  (`create-shell-plugin`).
- **`sync-skills.sh`** handles all three sources; dev/sql sync verified; contributor
  step correctly skips without a token. `DEFAULT_REF=1513b3b` (mariadb-docs main).
- **Marketplaces** (`.claude-plugin`, `.codex-plugin`) register dev + sql +
  contributor. Root `README.md` documents all three variants (hard skill counts
  removed) + updated layout tree.
- **Tests**: 3 suites; `claude/dev-plugin-tests` also has opt-in Tier 4 `e2e`
  (passed for real). All 3 pass `pytest -m static` = 472 each. Guardrail
  `test_expected_statement_skill_count == 31`; `see_also_refs()` backtick-only.
- **CI**: `.github/workflows/{claude,codex,opencode}-test.yml` run
  `pytest -m static|db|eval -ra`. (`test.yml` was renamed to `claude-test.yml`,
  internal `name: claude-tests`.)
- **Uncommitted** (branch `wip/AIPL-4`): contributor plugin dirs (untracked) +
  marketplace/README/sync-skills.sh edits. Connector sync already committed.

## Known issues / not done

- Contributor skills populated here **from the local `~/git/mariadb-shell` clone**
  (no token in session) as a stand-in; a token-backed `sync-skills.sh` reproduces
  from GitHub. Provenance commit `4c361e5`.
- e2e tier is claude-only (not propagated to codex/opencode).
- README/test docs still say "3-tier pytest suite" — stale for claude (has 4th
  opt-in e2e tier). Left as-is.
- Unusual version numbers (`9.7.0` shell / `26.7.0` package) unconfirmed as
  intentional.

## Files that matter

- `scripts/sync-skills.sh` -> vendors all plugins; dev/sql (manifest+include-list) + contributor (scan, private).
- `scripts/set-mariadb-shell-version.sh` / `set-plugin-version.sh` -> version bumpers.
- `claude/dev-plugin/scripts/mariadb-mcp-launcher.sh`/`.cmd` -> canonical launchers (copied to dev+sql).
- `claude/dev-plugin-tests/test_e2e_claude.py` -> Tier 4 e2e (opt-in `-m e2e`).
- `claude/dev-plugin-tests/lib/mcp_stdio.py` -> minimal MCP-over-stdio client.
- `{claude,codex,opencode}/dev-plugin-test(s)/{lib/skills.py,test_structure.py}` -> shared parsing + Tier1.
- `{claude,codex,opencode}/contributor-plugin/` -> skills-only plugin (manifest+README+CHANGELOG+LICENSE, no MCP).
- `additional-skills/mariadb-schema-create-script/SKILL.md` -> the SQL "Start Block" the e2e asserts.

## Next steps

1. Commit the contributor plugin + marketplace/README/sync-skills.sh changes.
2. Run a token-backed `scripts/sync-skills.sh` to re-vendor contributor from GitHub (confirm parity with local stand-in).
3. Optionally: propagate e2e tier to codex/opencode; add a CI workflow / test suite for contributor if desired.
4. Confirm version numbers `9.7.0` / `26.7.0`.

## Gotchas / things not to repeat

- New dev-only upstream layer → no logic change; keep it out of `SQL_INCLUDE_LAYERS`, bump `DEFAULT_REF`.
- Contributor source has NO manifest and is PRIVATE — scan `SKILL.md`, fetch via API tarball + token, skip gracefully.
- e2e teardown: cannot `sandbox.delete` a running instance — `sandbox.stop` (needs pw) or `sandbox.kill` first.
- Sandbox root password NOT blank — pin it (`test`, passed to Claude in the prompt) or connect fails.
- `see_also_refs()` false-positived on mariadb.com/docs URL slugs; fixed to backtick-only skill names.
- Statement-count guardrail hardcoded `== 31` in all 3 suites — bump on re-sync that changes statements.
- `sync-skills.sh` re-run bumps `synced_at` in every `skills-source.json`.
- macOS `sort -V` unreliable → launcher uses pure-bash `version_ge`.
- `/checkpoint` step-1 `git -C status` is malformed (missing path); ran with repo root.

## Git state

Branch: `wip/AIPL-4`

Modified (tracked): `.claude-plugin/marketplace.json`, `.codex-plugin/marketplace.json`,
`README.md`, `scripts/sync-skills.sh`.

Untracked: `claude/contributor-plugin/`, `codex/contributor-plugin/`,
`opencode/contributor-plugin/` (each: `.{claude,codex}-plugin/plugin.json` or none
for opencode, `README.md`, `CHANGELOG.md`, `LICENSE`, `skills-source.json`,
`skills/.skills-manifest.json`, `skills/create-shell-plugin/`).

Prior work (sql plugins, version scripts, launcher/MCP changes, workflow rename,
connector sync) is already committed.
