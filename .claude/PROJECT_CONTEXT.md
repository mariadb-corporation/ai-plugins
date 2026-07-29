# Project Context

## Project

`ai-plugins` packages MariaDB agent skills (+ the native `mariadb-shell` MCP server) as installable plugins for three coding agents: Claude Code (`claude/`), Codex (`codex/`), OpenCode (`opencode/`). Each agent has `dev` (full skills + MCP), `sql` (SQL subset + MCP), `contributor` (skills-only) variants. Skills are vendored (never hand-edited) by `scripts/sync-skills.sh`. **This work stream** added a set of **MariaDB REST Service** skills (a fork of the MySQL REST Service) and **Schema Management (MSM)** lifecycle skills under `additional-skills/`, reorganized `additional-skills/` into `sql/`/`rest/`/`schema-management/` subfolders with per-plugin selection, extended the Claude e2e test to exercise the REST skills end-to-end (full run passes), and updated the README.

## Architecture / key decisions

- **Flat skill layout everywhere** (`skills/<skill>/SKILL.md`); OpenCode discovers one dir deep. `.skills-manifest.json` rewritten to flat paths, layer grouping preserved.
- **Skill sources**: `dev`/`sql` ← `mariadb-corporation/mariadb-docs` `agent-skills/` (manifest w/ layers, pinned `DEFAULT_REF=1513b3b`); `contributor` ← private `mariadb-shell` `.claude/skills/` (needs `GH_TOKEN`, skips gracefully without). `additional-skills/` (this repo's own) is grouped into topic subfolders — `sql/`, `rest/`, `schema-management/` — vendored flat into a single `additional` manifest layer. `sync-skills.sh` selects per plugin via `ADDITIONAL_SUBDIRS=(sql rest schema-management)` and include keys `additional-<subfolder>` (or bare `additional`=all): dev (empty include list) gets all subfolders; `sql` gets only `sql/` via `SQL_INCLUDE_LAYERS=(granular-statements granular-functions topical additional-sql)`. So `rest/` and `schema-management/` are dev-only.
- **REST skills mirror the MySQL REST Service DDL verbatim** (it's a fork). Branding decisions (user-confirmed): keep upstream identifiers `mysql_rest_service_metadata` + roles `mysql_rest_service_*`; rebrand serving component to **"REST Daemon"** and admin tool to **`mariadb-shell`**. Source docs: `/Users/mzinner/git/mysql-shell-plugins/mrs_plugin/docs/sections/{sql,devGuide}/*`.
- **MSM (Schema Management) skills** teach the schema lifecycle (create → develop → release → deploy) as an overview + 4 focused skills. Source: `/Users/mzinner/git/mysql-shell-plugins/{msm_plugin/lib/management.py,mcp_plugin/lib/msm_functions.py}` + `msm_plugin/templates/`.
- **Tier-1 static contract** (each SKILL.md): frontmatter `name` == dir; `description` has "Use when" (≥20 chars); balanced ``` fences; any backticked `mariadb-*`/`mysql-*` under a `## See Also` heading must resolve to a real skill.
- **e2e test (Tier 4, opt-in `-m e2e`, claude-only)**: drives the real `claude` CLI **once** in a module-scoped `workflow` fixture, then asserts side effects in **6 separate `test_stepN_*` tests** (runnable individually via `pytest -k stepN`). Sandbox teardown lives in the fixture `finally` so it always runs (even on timeout).
- **REST verification**: `SHOW REST` are mariadb-shell DDL extensions → run via the MCP server (`_rest_via_show`, discovers the SQL tool from `tools/list` at runtime), with a `mysql_rest_service_metadata` PyMySQL query fallback (`_rest_via_metadata`).
- `mariadb-shell` == MySQL Shell fork (`mysqlsh`); sandboxes in `~/mysql-sandboxes/<port>/`. MCP tools: `sandbox.deploy/start/stop/kill/delete`, `db.connect/execute_sql/execute_sql_script/close`, `msm.*`.

## Current state

- **Done & working:**
  - 5 REST skills in `additional-skills/rest/`: `mariadb-rest-service-{create,update-endpoints,authorization,show,drop}`.
  - MSM skills in `additional-skills/schema-management/`: overview `mariadb-schema-management` + `mariadb-schema-management-{create,develop,release,deploy}`. `mariadb-schema-create-script` moved to `additional-skills/sql/`.
  - `additional-skills/` reorganized into `sql/`/`rest/`/`schema-management/`; `sync-skills.sh` updated for per-subfolder selection and re-run. Counts: dev = 68 skills (additional=11: 5 rest + 5 MSM + schema-create-script); sql = 47 (additional=1: only schema-create-script). Manifests match disk.
  - README updated (plugin table, "what each plugin provides", repo-layout tree, skills-sync section) for the subfolders + dev/sql split.
  - e2e test split into 6 step tests + teardown-on-timeout fix. **Full e2e: 6 passed in 5m10s** vs local claude, incl. `test_step5` (REST DDL executed via MCP → `/notesApp` + endpoints verified) — works end-to-end **after the user fixed the mrs plugin**.
  - **Static tests: 542 passed in ALL THREE suites** (claude/codex/opencode). No test changes needed — the only hardcoded count is `test_expected_statement_skill_count == 31` (statement layer only; unaffected by the `additional` layer).
- **In progress:** nothing committed — awaiting commit/PR decision.
- **Known issues:** none blocking.

## Files that matter

- `additional-skills/rest/mariadb-rest-service-create/SKILL.md` -> CONFIGURE REST METADATA → CREATE REST SERVICE/SCHEMA → REST VIEW (GraphQL block, @KEY/@SORTABLE/@UNNEST/CRUD) + REST PROCEDURE/FUNCTION.
- `additional-skills/rest/mariadb-rest-service-{update-endpoints,authorization,show,drop}/SKILL.md` -> ALTER; auth apps/users/roles + GRANT/REVOKE REST; SHOW REST / SHOW CREATE REST; DROP REST.
- `additional-skills/schema-management/mariadb-schema-management{,-create,-develop,-release,-deploy}/SKILL.md` -> MSM lifecycle (overview + 4 steps; `-develop` documents SOURCE breakout files; `-release` the fill-update-then-generate order).
- `additional-skills/sql/mariadb-schema-create-script/SKILL.md` -> standalone (non-MSM) create-script conventions; the e2e Start-Block assertion.
- `claude/dev-plugin-tests/test_e2e_claude.py` -> fixture `workflow` + `test_step0..5`; helpers `_rest_via_show`, `_rest_via_metadata`, `_parse_rest_paths`, `_find_sql_tool`, `_teardown_sandbox`.
- `claude/dev-plugin-tests/lib/{mcp_stdio.py,skills.py}` + `test_structure.py` -> MCP stdio client + tier-1 static contract.
- `scripts/sync-skills.sh` -> vendors skills; `ADDITIONAL_SUBDIRS` + `SQL_INCLUDE_LAYERS` drive per-plugin subfolder selection; rerun after editing `additional-skills/`.

## Next steps

1. Commit on `wip/AIPL-4`: the `additional-skills/` reorg (renames into `sql/` + `rest/`, new `schema-management/`), the 5 MSM skills, `sync-skills.sh`, `README.md`, and the re-vendored plugin trees + manifests + `skills-source.json` across all 6 dev/sql plugins.
2. Push to `origin/wip/AIPL-4`.
3. Optionally open a PR.
4. (Optional) Propagate the REST/MSM e2e steps to codex/opencode suites.

## Gotchas / things not to repeat

- **REST DDL over MCP root cause (user FIXED in `mysql-shell-plugins/mrs_plugin/lib/general.py`)**: REST metadata deploy chose its management session via `"shell.Object" in str(type(session))` → `open_session()` (no-arg = duplicate the GLOBAL session), which raises **"An open session is required when duplicating sessions"** when there's no global session (headless/MCP). Interactive worked only because a global session existed. Empirically: MCP session type = `<class 'shell.Object'>`, headless global session = `None`, and `shell.Object` has no `.connection_options` (so the else-branch fallback also failed; `get_uri()` strips the password → prompt hang).
- **MSM deployment composition:** sections **140/240/170/270** become **stored-procedure bodies** → plain `;`-terminated, NO `DELIMITER`, dynamic SQL for conditional DDL; sections **130/150/230/250/190/290** are top-level with `DELIMITER %%`. Order: `prepare_release` → **fill update script (240/250/270)** → `generate_deployment_script` → `deploy_schema` (generating before filling the update script yields a script that creates fresh but can't upgrade older installs).
- **MSM SOURCE breakout:** `SOURCE './sections/x.sql'[start:end];` uses **character-offset** slices to strip each file's own copyright header/footer (`[53:]`, `[663:-115]`, `[:N]`); relative to `development/`; inlined at `prepare_release` (dev-time only).
- **bash 3.2 (macOS) + `set -u`:** guard empty-array expansion (`[ "${#arr[@]}" -gt 0 ]`) — done for `add_subdirs` in `sync-skills.sh`.
- `db.execute_sql_script` runs each statement in a **fresh session** → REST grammar needs one continuous session; run REST statements individually via `db.execute_sql` on one connection (claude adapts automatically).
- MCP `db.connect` needs a **bare** uri `root@127.0.0.1:PORT` (not `mariadb://...` → "not a configured connection"); `db.execute_sql_script` rejects file paths outside allowed paths → pass SQL inline.
- Background `... | tee log` reports **tee's** exit (0), not pytest's — always read the pytest summary line.
- Timeouts orphan sandboxes if teardown isn't in a `finally` (leaked 51111/51914 earlier). Clean via MCP `sandbox.stop`+`sandbox.delete` (fallback `sandbox.kill`). All session sandboxes now cleaned (51111, 51914, 52646, e2e's 54042).
- Foreground `sleep` is blocked by the harness; use `run_in_background` / Monitor.
- `see_also_refs()` counts only backticked `mariadb-*`/`mysql-*` under `## See Also`; underscored names like `mysql_rest_service_metadata` don't match (safe).
- Sandbox root password must not be blank (pin `test`); `sandbox.delete` refuses a running instance.
- mariadb-shell binary: `/Users/mzinner/git/mariadb-shell/build/bin/mariadb-shell`; MCP plugin source: `/Users/mzinner/git/mysql-shell-plugins/mcp_plugin`; REST/mrs plugin: `/Users/mzinner/git/mysql-shell-plugins/mrs_plugin`.

## Git state

Branch: `wip/AIPL-4`

```text
 M README.md
 M scripts/sync-skills.sh
R  additional-skills/mariadb-rest-service-*/SKILL.md -> additional-skills/rest/...   (5 renames, staged)
R  additional-skills/mariadb-schema-create-script/SKILL.md -> additional-skills/sql/...   (staged)
 M {claude,codex,opencode}/{dev,sql}-plugin/skills/.skills-manifest.json   (6)
 M {claude,codex,opencode}/{dev,sql}-plugin/skills-source.json             (6)
?? additional-skills/schema-management/            (overview + 4 MSM skills, untracked)
?? {claude,codex,opencode}/dev-plugin/skills/mariadb-schema-management*/   (5 each, re-vendored)
?? {claude,codex,opencode}/sql-plugin/skills/mariadb-schema-create-script/ (re-vendored at new path)
```

Prior commit `e09dc70` (REST skills + e2e split) already pushed to `origin/wip/AIPL-4`. `.claude/settings.json` is no longer modified (its earlier machine-specific Read permission was intentionally not committed).
