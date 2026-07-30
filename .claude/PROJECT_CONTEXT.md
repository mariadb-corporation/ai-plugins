# Project Context

## Project

`ai-plugins` packages MariaDB agent skills (+ the native `mariadb-shell` MCP server) as installable plugins for three coding agents: Claude Code (`claude/`), Codex (`codex/`), OpenCode (`opencode/`). Each agent has `dev` (full skills + MCP), `sql` (SQL subset + MCP), `contributor` (skills-only) variants. Skills are vendored (never hand-edited) by `scripts/sync-skills.sh`. **This work stream** added a set of **MariaDB REST Service** skills (a fork of the MySQL REST Service) and **Schema Management (MSM)** lifecycle skills under `additional-skills/`, reorganized `additional-skills/` into `sql/`/`rest/`/`schema-management/` subfolders with per-plugin selection, added **two Claude e2e tests** that exercise the REST skills and the MSM lifecycle skills end-to-end (both pass), and updated the README.

## Architecture / key decisions

- **Flat skill layout everywhere** (`skills/<skill>/SKILL.md`); OpenCode discovers one dir deep. `.skills-manifest.json` rewritten to flat paths, layer grouping preserved.
- **Skill sources**: `dev`/`sql` ← `mariadb-corporation/mariadb-docs` `agent-skills/` (manifest w/ layers, pinned `DEFAULT_REF=1513b3b`); `contributor` ← private `mariadb-shell` `.claude/skills/` (needs `GH_TOKEN`, skips gracefully without). `additional-skills/` (this repo's own) is grouped into topic subfolders — `sql/`, `rest/`, `schema-management/` — vendored flat into a single `additional` manifest layer. `sync-skills.sh` selects per plugin via `ADDITIONAL_SUBDIRS=(sql rest schema-management)` and include keys `additional-<subfolder>` (or bare `additional`=all): dev (empty include list) gets all subfolders; `sql` gets only `sql/` via `SQL_INCLUDE_LAYERS=(granular-statements granular-functions topical additional-sql)`. So `rest/` and `schema-management/` are dev-only.
- **REST skills mirror the MySQL REST Service DDL verbatim** (it's a fork). Branding decisions (user-confirmed): keep upstream identifiers `mysql_rest_service_metadata` + roles `mysql_rest_service_*`; rebrand serving component to **"REST Daemon"** and admin tool to **`mariadb-shell`**. Source docs: `/Users/mzinner/git/mysql-shell-plugins/mrs_plugin/docs/sections/{sql,devGuide}/*`.
- **MSM (Schema Management) skills** teach the schema lifecycle (create → develop → release → deploy) as an overview + 4 focused skills. Source: `/Users/mzinner/git/mysql-shell-plugins/{msm_plugin/lib/management.py,mcp_plugin/lib/msm_functions.py}` + `msm_plugin/templates/`.
- **Tier-1 static contract** (each SKILL.md): frontmatter `name` == dir; `description` has "Use when" (≥20 chars); balanced ``` fences; any backticked `mariadb-*`/`mysql-*` under a `## See Also` heading must resolve to a real skill.
- **e2e tests (Tier 4, opt-in `-m e2e`, claude-only)**: each drives the real `claude` CLI **once** in a module-scoped `workflow` fixture, then asserts side effects in **6 separate `test_stepN_*` tests** (runnable individually via `pytest -k stepN`). Two files: `test_e2e_claude.py` (REST) and `test_e2e_msm_claude.py` (MSM).
- **REST e2e** (`test_e2e_claude.py`): spins up a real sandbox; sandbox teardown lives in the fixture `finally` so it always runs (even on timeout). `SHOW REST` are mariadb-shell DDL extensions → run via the MCP server (`_rest_via_show`, discovers the SQL tool from `tools/list` at runtime), with a `mysql_rest_service_metadata` PyMySQL query fallback (`_rest_via_metadata`).
- **MSM e2e** (`test_e2e_msm_claude.py`): **no DB/sandbox** — `msm.prepare_release`/`generate_deployment_script` are pure on-disk ops, so every check is a file. Drives claude through **two releases** (v1.0.0 → develop → v1.1.0) and asserts the *right sections* were used (tables in create-140 / update-240, views in 150 / 250), the **update script was filled** (comments stripped so the empty template can't pass), and the v1.1.0 deployment script composes **all** objects. Hermetic: points `MYSQLSH_USER_CONFIG_HOME` at a throwaway dir and pre-seeds its `settings.json` allow-list with the project dir (no touching real `~/.mysqlsh`, no path-trust elicitation). Section split via `_sections()` on `^-- MSM Section NNN:` banners.
- `mariadb-shell` == MySQL Shell fork (`mysqlsh`); sandboxes in `~/mysql-sandboxes/<port>/`. MCP tools: `sandbox.deploy/start/stop/kill/delete`, `db.connect/execute_sql/execute_sql_script/close`, `msm.*`.

## Current state

- **Done & working:**
  - 5 REST skills in `additional-skills/rest/`: `mariadb-rest-service-{create,update-endpoints,authorization,show,drop}`.
  - MSM skills in `additional-skills/schema-management/`: overview `mariadb-schema-management` + `mariadb-schema-management-{create,develop,release,deploy}`. `mariadb-schema-create-script` moved to `additional-skills/sql/`.
  - `additional-skills/` reorganized into `sql/`/`rest/`/`schema-management/`; `sync-skills.sh` updated for per-subfolder selection and re-run. Counts: dev = 68 skills (additional=11: 5 rest + 5 MSM + schema-create-script); sql = 47 (additional=1: only schema-create-script). Manifests match disk.
  - README updated (plugin table, "what each plugin provides", repo-layout tree, skills-sync section) for the subfolders + dev/sql split.
  - REST e2e split into 6 step tests + teardown-on-timeout fix. **Full REST e2e: 6 passed in 5m10s** vs local claude, incl. `test_step5` (REST DDL executed via MCP → `/notesApp` + endpoints verified) — works end-to-end **after the user fixed the mrs plugin**.
  - **MSM e2e: 6 passed in 11m23s** vs local claude (`test_e2e_msm_claude.py`) — claude scaffolded the `notes_app` project, authored v1.0.0 (tables→140, activity VIEW→150), released it, developed v1.1.0 (notebook/tag tables + notes_details VIEW), **filled the 1.0.0→1.1.0 update script** (240/250), and generated a v1.1.0 deployment script containing all objects.
  - **Static tests: 542 passed in ALL THREE suites** (claude/codex/opencode). No test changes needed — the only hardcoded count is `test_expected_statement_skill_count == 31` (statement layer only; unaffected by the `additional` layer).
- **In progress:** MSM e2e test (`test_e2e_msm_claude.py`) being committed.
- **Known issues:** none blocking.

## Files that matter

- `additional-skills/rest/mariadb-rest-service-create/SKILL.md` -> CONFIGURE REST METADATA → CREATE REST SERVICE/SCHEMA → REST VIEW (GraphQL block, @KEY/@SORTABLE/@UNNEST/CRUD) + REST PROCEDURE/FUNCTION.
- `additional-skills/rest/mariadb-rest-service-{update-endpoints,authorization,show,drop}/SKILL.md` -> ALTER; auth apps/users/roles + GRANT/REVOKE REST; SHOW REST / SHOW CREATE REST; DROP REST.
- `additional-skills/schema-management/mariadb-schema-management{,-create,-develop,-release,-deploy}/SKILL.md` -> MSM lifecycle (overview + 4 steps; `-develop` documents SOURCE breakout files; `-release` the fill-update-then-generate order).
- `additional-skills/sql/mariadb-schema-create-script/SKILL.md` -> standalone (non-MSM) create-script conventions; the e2e Start-Block assertion.
- `claude/dev-plugin-tests/test_e2e_claude.py` -> REST e2e: fixture `workflow` + `test_step0..5`; helpers `_rest_via_show`, `_rest_via_metadata`, `_parse_rest_paths`, `_find_sql_tool`, `_teardown_sandbox`.
- `claude/dev-plugin-tests/test_e2e_msm_claude.py` -> MSM e2e: fixture `workflow` + `test_step0..5`; helpers `_find_project`, `_sections` (MSM banner split), `_strip_sql_comments`, `_seed_allowed_path` (isolated `MYSQLSH_USER_CONFIG_HOME` allow-list).
- `claude/dev-plugin-tests/lib/{mcp_stdio.py,skills.py}` + `test_structure.py` -> MCP stdio client + tier-1 static contract.
- `scripts/sync-skills.sh` -> vendors skills; `ADDITIONAL_SUBDIRS` + `SQL_INCLUDE_LAYERS` drive per-plugin subfolder selection; rerun after editing `additional-skills/`.

## Next steps

1. (Optional) Open a PR for `wip/AIPL-4`.
2. (Optional) Propagate the REST/MSM e2e steps to codex/opencode suites.

Done & pushed: commit `de71679` (reorg + 5 MSM skills + sync-skills.sh + README + re-vendored trees), and the MSM e2e test commit (this change).

## Gotchas / things not to repeat

- **REST DDL over MCP root cause (user FIXED in `mysql-shell-plugins/mrs_plugin/lib/general.py`)**: REST metadata deploy chose its management session via `"shell.Object" in str(type(session))` → `open_session()` (no-arg = duplicate the GLOBAL session), which raises **"An open session is required when duplicating sessions"** when there's no global session (headless/MCP). Interactive worked only because a global session existed. Empirically: MCP session type = `<class 'shell.Object'>`, headless global session = `None`, and `shell.Object` has no `.connection_options` (so the else-branch fallback also failed; `get_uri()` strips the password → prompt hang).
- **MSM deployment composition:** sections **140/240/170/270** become **stored-procedure bodies** → plain `;`-terminated, NO `DELIMITER`, dynamic SQL for conditional DDL; sections **130/150/230/250/190/290** are top-level with `DELIMITER %%`. Order: `prepare_release` → **fill update script (240/250/270)** → `generate_deployment_script` → `deploy_schema` (generating before filling the update script yields a script that creates fresh but can't upgrade older installs).
- **MSM SOURCE breakout:** `SOURCE './sections/x.sql'[start:end];` uses **character-offset** slices to strip each file's own copyright header/footer (`[53:]`, `[663:-115]`, `[:N]`); relative to `development/`; inlined at `prepare_release` (dev-time only).
- **bash 3.2 (macOS) + `set -u`:** guard empty-array expansion (`[ "${#arr[@]}" -gt 0 ]`) — done for `add_subdirs` in `sync-skills.sh`.
- **MSM tools are all path-gated** by the MCP server's `settings.json` allow-list (`<config home>/plugin_data/mcp_plugin/settings.json`, key `allowedPaths`); a non-allowed path falls back to an elicitation the headless CLI can't answer → tool fails. The shell honors **`MYSQLSH_USER_CONFIG_HOME`** (verified: it relocates `mysqlsh.log` + `plugin_data`), so the MSM e2e sets it to a temp dir and pre-seeds the allow-list — never mutate the real `~/.mysqlsh`. The `msm` plugin method is `msm.create_new_project_folder` (not `create_project`); `license="GPLv2"` is rejected (no stored license by that name) — omit it or pass custom text.
- `db.execute_sql_script` runs each statement in a **fresh session** → REST grammar needs one continuous session; run REST statements individually via `db.execute_sql` on one connection (claude adapts automatically).
- MCP `db.connect` needs a **bare** uri `root@127.0.0.1:PORT` (not `mariadb://...` → "not a configured connection"); `db.execute_sql_script` rejects file paths outside allowed paths → pass SQL inline.
- Background `... | tee log` reports **tee's** exit (0), not pytest's — always read the pytest summary line.
- Timeouts orphan sandboxes if teardown isn't in a `finally` (leaked 51111/51914 earlier). Clean via MCP `sandbox.stop`+`sandbox.delete` (fallback `sandbox.kill`). All session sandboxes now cleaned (51111, 51914, 52646, e2e's 54042).
- Foreground `sleep` is blocked by the harness; use `run_in_background` / Monitor.
- `see_also_refs()` counts only backticked `mariadb-*`/`mysql-*` under `## See Also`; underscored names like `mysql_rest_service_metadata` don't match (safe).
- Sandbox root password must not be blank (pin `test`); `sandbox.delete` refuses a running instance.
- mariadb-shell binary: `/Users/mzinner/git/mariadb-shell/build/bin/mariadb-shell`; MCP plugin source: `/Users/mzinner/git/mysql-shell-plugins/mcp_plugin`; REST/mrs plugin: `/Users/mzinner/git/mysql-shell-plugins/mrs_plugin`.

## Git state

Branch: `wip/AIPL-4` (clean after this commit).

Commit history on the branch (all pushed to `origin/wip/AIPL-4`):

- `e09dc70` — REST skills + e2e split.
- `de71679` — additional-skills reorg (renames into `sql/`+`rest/`, new `schema-management/`) + 5 MSM skills + sync-skills.sh + README + re-vendored plugin trees/manifests/skills-source.
- (this commit) — `claude/dev-plugin-tests/test_e2e_msm_claude.py` (MSM e2e) + this PROJECT_CONTEXT update.

Heads-up (this session): the `codex/dev-plugin-test` and `opencode/dev-plugin-test` dirs went **missing from the working tree** (not by any deliberate action here); restored from HEAD with `git restore` and kept out of the commit. `.claude/settings.json` remains intentionally uncommitted.
