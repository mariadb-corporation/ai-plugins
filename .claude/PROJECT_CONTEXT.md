# Project Context

Index. Each area below lives in its own file under `.claude/context/` — read the
ones your work touches, not the whole set. This file keeps the description, the
layout and the context-file table. PR and branch state is not recorded here: read it
live (`gh pr list`, `git branch`), as `/read-checkpoint` does.

## Project

`ai-plugins` packages MariaDB agent skills (+ the native `mariadb-shell` MCP server and, where supported, its SQL language server) as installable plugins for five coding agents: Claude Code (`claude/`), Codex (`codex/`), OpenCode (`opencode/`), Pi/pi.dev (`pi/`), and Hermes Agent (`hermes/`); Cursor installs the Claude Code plugins. Each agent has `dev` (all skills + MCP), `sql` (SQL subset + MCP) and `contributor` (skills-only) variants — Pi has only `dev`, Hermes adds `mariadb-guard` — and Hermes users install `mariadb-dev`/`mariadb-guard` by name from the Hermes plugin catalog. Skills are vendored (never hand-edited) by `scripts/sync-skills.sh` from mariadb-docs, mariadb-shell and this repo's `additional-skills/` (REST Service, Schema Management, migrator, Laravel). Alongside the plugins live the DevHub (`docs/`), the reference docs for mariadb.com/docs (`docs-ref/`), generated videos (`videos/`), and a test suite per harness driven by `run_tests.py`.

## Repo layout

| Path | What it is |
| --- | --- |
| `claude/`, `codex/`, `opencode/`, `pi/`, `hermes/` | One dir per coding agent: its plugin variants plus its `*-plugin-test*` suite |
| `additional-skills/` | This repo's own skills, in `sql/` `rest/` `schema-management/` `migrator/` `laravel/`, plus the sources & licensing README |
| `docs/` | The DevHub — Jekyll site served by the fork's GitHub Pages at <https://ai-plugins.mariadb.org/> |
| `docs-ref/` | Reference docs: GitBook source in `content/` (for mariadb.com/docs, Community Tools) + Docusaurus preview; `npm run docs-ref` |
| `videos/` | Generated videos: `setup.sh` + `requirements.txt` build the gitignored `.cache/` toolchain; one folder per video (`se-enablement/`: `PLAN.md`, `build.sh`, `src/`); renders land in gitignored `output/` |
| `scripts/` | `sync-skills.sh` (vendors skills), `set-plugin-version.sh`, `set-mariadb-shell-version.sh` |
| `tests/` | Shared test data (`cli-guard-cases.json`) |
| `run_tests.py`, `pytest-coverage.ini` | Unified runner across every suite, one combined coverage report |
| `package.json` | The pi manifest (`pi` field) + npm scripts |
| `.claude-plugin/`, `.agents/plugins/` | Marketplace manifests for Claude Code (and Cursor) and Codex |
| `test-results/`, `htmlcov/` | Test and coverage output, gitignored |
| `README.md`, `CONTRIBUTING.md`, `LICENSE`, `SECURITY.md` | Root docs; `CONTRIBUTING.md` holds the maintainer docs |

## Context files

| File | What's in it |
| --- | --- |
| [`context/architecture.md`](context/architecture.md) | Design choices and why — plugins and skills, MCP launchers per harness, the Hermes catalog, the language server, tests, the DevHub |
| [`context/current-state.md`](context/current-state.md) | What works and the known issues and gaps |
| [`context/files-that-matter.md`](context/files-that-matter.md) | Path → purpose for the central files, with their editing traps |
| [`context/next-steps.md`](context/next-steps.md) | Ordered list of work still to do |
| [`context/gotchas.md`](context/gotchas.md) | Traps and dead ends — read before retrying anything |
| [`context/repo-conventions.md`](context/repo-conventions.md) | The two remotes and the fork's role, fork sync, DevHub hosting, branch and PR rules, release tagging |
| [`context/docs-ref.md`](context/docs-ref.md) | The `docs-ref/` reference docs: GitBook/preview split, plugin workarounds, content rules (passwords only at the prompt), next steps, build gotchas, markdownlint settings |
