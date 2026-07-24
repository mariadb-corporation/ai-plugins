# Project Context

## Project

`ai-plugins` packages MariaDB agent skills (+ the native `mariadb-shell` MCP server) as installable plugins for three coding agents: Claude Code (`claude/`), Codex (`codex/`), OpenCode (`opencode/`). Each agent has `dev` (full skills + MCP), `sql` (SQL subset + MCP), `contributor` (skills-only) variants. Skills are vendored (never hand-edited) by `scripts/sync-skills.sh`. **This session** added a set of **MariaDB REST Service** skills (a fork of the MySQL REST Service) under `additional-skills/` and extended the Claude e2e test to exercise them end-to-end; the full e2e run passes.

## Architecture / key decisions

- **Flat skill layout everywhere** (`skills/<skill>/SKILL.md`); OpenCode discovers one dir deep. `.skills-manifest.json` rewritten to flat paths, layer grouping preserved.
- **Skill sources**: `dev`/`sql` ← `mariadb-corporation/mariadb-docs` `agent-skills/` (manifest w/ layers, pinned `DEFAULT_REF=1513b3b`); `contributor` ← private `mariadb-shell` `.claude/skills/` (needs `GH_TOKEN`, skips gracefully without). `additional-skills/*/SKILL.md` (this repo's own) are auto-discovered and vendored flat into `dev`/`sql` only, under an `additional` manifest layer. `sql` excludes it via `SQL_INCLUDE_LAYERS=(granular-statements granular-functions topical)`.
- **REST skills mirror the MySQL REST Service DDL verbatim** (it's a fork). Branding decisions (user-confirmed): keep upstream identifiers `mysql_rest_service_metadata` + roles `mysql_rest_service_*`; rebrand serving component to **"REST Daemon"** and admin tool to **`mariadb-shell`**. Source docs: `/Users/mzinner/git/mysql-shell-plugins/mrs_plugin/docs/sections/{sql,devGuide}/*`.
- **Tier-1 static contract** (each SKILL.md): frontmatter `name` == dir; `description` has "Use when" (≥20 chars); balanced ``` fences; any backticked `mariadb-*`/`mysql-*` under a `## See Also` heading must resolve to a real skill.
- **e2e test (Tier 4, opt-in `-m e2e`, claude-only)**: drives the real `claude` CLI **once** in a module-scoped `workflow` fixture, then asserts side effects in **6 separate `test_stepN_*` tests** (runnable individually via `pytest -k stepN`). Sandbox teardown lives in the fixture `finally` so it always runs (even on timeout).
- **REST verification**: `SHOW REST` are mariadb-shell DDL extensions → run via the MCP server (`_rest_via_show`, discovers the SQL tool from `tools/list` at runtime), with a `mysql_rest_service_metadata` PyMySQL query fallback (`_rest_via_metadata`).
- `mariadb-shell` == MySQL Shell fork (`mysqlsh`); sandboxes in `~/mysql-sandboxes/<port>/`. MCP tools: `sandbox.deploy/start/stop/kill/delete`, `db.connect/execute_sql/execute_sql_script/close`, `msm.*`.

## Current state

- **Done & working:**
  - 5 REST skills in `additional-skills/`: `mariadb-rest-service-{create,update-endpoints,authorization,show,drop}` (pass the static contract).
  - `sync-skills.sh` run → vendored into all 6 dev/sql plugins (Claude/Codex/OpenCode) + manifests + `skills-source.json` updated.
  - e2e test split into 6 step tests + teardown-on-timeout fix.
  - **Full e2e: 6 passed in 5m10s** vs local claude, incl. `test_step5` (REST DDL executed via MCP → `/notesApp` + endpoints verified). Confirms skill → MCP → REST-metadata works end-to-end **after the user fixed the mrs plugin**.
- **In progress:** nothing committed — awaiting commit/PR decision.
- **Known issues:** none blocking. `.claude/settings.json` shows modified in git — not touched by this work stream; verify before committing.

## Files that matter

- `additional-skills/mariadb-rest-service-create/SKILL.md` -> CONFIGURE REST METADATA → CREATE REST SERVICE/SCHEMA → REST VIEW (GraphQL block, @KEY/@SORTABLE/@UNNEST/CRUD) + REST PROCEDURE/FUNCTION.
- `additional-skills/mariadb-rest-service-update-endpoints/SKILL.md` -> ALTER REST *, NEW REQUEST PATH, publish/unpublish, MERGE-vs-overwrite OPTIONS, ADD/REMOVE AUTH APP.
- `additional-skills/mariadb-rest-service-authorization/SKILL.md` -> admin roles, AUTH APP (MRS/MYSQL/OAuth2), REST USER/ROLE, GRANT/REVOKE REST.
- `additional-skills/mariadb-rest-service-show/SKILL.md` -> `SHOW REST ...` / `SHOW CREATE REST ...`.
- `additional-skills/mariadb-rest-service-drop/SKILL.md` -> DROP REST * (metadata-only; implicit cascade).
- `claude/dev-plugin-tests/test_e2e_claude.py` -> fixture `workflow` + `test_step0..5`; helpers `_rest_via_show`, `_rest_via_metadata`, `_parse_rest_paths`, `_find_sql_tool`, `_teardown_sandbox`.
- `claude/dev-plugin-tests/lib/{mcp_stdio.py,skills.py}` + `test_structure.py` -> MCP stdio client + tier-1 static contract.
- `scripts/sync-skills.sh` -> vendors skills; rerun after editing `additional-skills/`.

## Next steps

1. Confirm `.claude/settings.json` modification is intended (or revert) before committing.
2. Commit on `wip/AIPL-4`: 5 new skills + vendored plugin changes (skills/ + manifests + skills-source.json across 6 plugins) + e2e test changes.
3. Optionally open a PR.
4. (Optional) `cd claude/dev-plugin-tests && ../../.venv/bin/python -m pytest -m static` to confirm the new skills pass the contract.
5. (Optional) Propagate the REST e2e steps to codex/opencode suites.

## Gotchas / things not to repeat

- **REST DDL over MCP root cause (user FIXED in `mysql-shell-plugins/mrs_plugin/lib/general.py`)**: REST metadata deploy chose its management session via `"shell.Object" in str(type(session))` → `open_session()` (no-arg = duplicate the GLOBAL session), which raises **"An open session is required when duplicating sessions"** when there's no global session (headless/MCP). Interactive worked only because a global session existed. Empirically: MCP session type = `<class 'shell.Object'>`, headless global session = `None`, and `shell.Object` has no `.connection_options` (so the else-branch fallback also failed; `get_uri()` strips the password → prompt hang).
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
 M .claude/settings.json                              (NOT from this work — verify)
 M claude/dev-plugin-tests/test_e2e_claude.py
 M claude/dev-plugin/skills-source.json
 M claude/dev-plugin/skills/.skills-manifest.json
 M claude/sql-plugin/skills-source.json
 M codex/dev-plugin/skills-source.json
 M codex/dev-plugin/skills/.skills-manifest.json
 M codex/sql-plugin/skills-source.json
 M opencode/dev-plugin/skills-source.json
 M opencode/dev-plugin/skills/.skills-manifest.json
 M opencode/sql-plugin/skills-source.json
?? additional-skills/mariadb-rest-service-{create,update-endpoints,authorization,show,drop}/
?? claude/dev-plugin/skills/mariadb-rest-service-*/     (5 dirs)
?? codex/dev-plugin/skills/mariadb-rest-service-*/      (5 dirs)
?? opencode/dev-plugin/skills/mariadb-rest-service-*/   (5 dirs)
```
