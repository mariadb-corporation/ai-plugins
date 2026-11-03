# Current state

[← Project Context](../PROJECT_CONTEXT.md)

What exists and works, and what is known not to. The design behind it is in [architecture](architecture.md).

## Works

- **Plugins**: dev / sql / contributor for Claude Code, Codex, OpenCode and Hermes; dev only for Pi; `mariadb-guard` for Hermes; Cursor through the Claude Code marketplace. Skill counts: `docs/_config.yml` `skill_count` (dev), or count `*/…-plugin/skills/*/SKILL.md`.
- **MCP server** wired in every MCP-bearing plugin through its launcher, with the CLI guard; **SQL language server** for Claude Code, OpenCode and Hermes (Hermes via a user-added config snippet); Codex and pi get the `sql.*` MCP tools instead.
- **Hermes plugin catalog**: `mariadb-dev` and `mariadb-guard` install by name (`hermes plugins install mariadb-dev --enable`) from `plugin-catalog/mariadb-{dev,guard}.yaml` in `NousResearch/hermes-agent` (added by #145982; page <https://hermes-agent.nousresearch.com/docs/plugins/mariadb-dev>). Read the YAML for the current pin and version; `requires_hermes` names the minimum Hermes. `mariadb-sql` and contributor are folder installs (`hermes plugins install mariadb/ai-plugins#hermes/<plugin> --enable`).
- **Tests**: a suite per harness with static + db tiers by default and opt-in e2e (see architecture); `./run_tests.py` runs them all on the shell's Python with combined coverage. CI runs static + db per suite with plain `pytest`.
- **Native Windows**: Codex (extensionless launcher → `.cmd`), Claude Code and OpenCode (extensionless commands), Pi (cross-spawn runs the `.cmd`) are verified on Windows 11 ARM64; the `.cmd` LSP launcher passes its clean-install race there.
- **DevHub** live at <https://ai-plugins.mariadb.org/>: tutorials, learning paths, a generated skill catalog, an architecture page, the MCP tool reference and an offline-install page (direct download links for source archives, shell packages + SHA256SUMS of the floor, sandbox server packages). The home page shows "Version <plugin_version> · MariaDB Shell <shell_floor> or newer".
- **Reference docs** (`docs-ref/`): GitBook source for mariadb.com/docs (Community Tools) + a Docusaurus preview; see [reference docs](docs-ref.md).
- **SE enablement video** (`videos/se-enablement/`): `build.sh` rebuilds `videos/output/MariaDB-AI-Plugins-SE-Enablement.{mp4,srt}` (~2:11, −16 LUFS) in a few minutes from a clean checkout after `videos/setup.sh`. Voice tuning settled with the user: `Maria-DB`, `AI-Plugins`, whoosh at 0.16, closing line "Get started at mariadb.com/docs" with the full docs-ref URL on screen.

## Known issues and gaps

- **Windows MCP server needs pywin32** in mariadb-shell's bundled Python (see gotchas) — the plugins can't fix it.
- **Hero code samples are cut off on phones** (scrollable, with a `…` marker); see next steps.
- **Hermes on native Windows is untested**; its docs give the `.cmd` path unverified.
- **Pi has no sql/contributor variants.** OpenCode has no REST/MSM e2e.
- The docs list no `rest.*`/`restd.*` MCP groups on purpose (see [reference docs](docs-ref.md)).
- `--ch-accent-btn-hover` is defined in both token blocks of `style.css` but used nowhere.
