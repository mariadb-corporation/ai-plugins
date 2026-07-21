# MariaDB AI Plugins

First-class **MariaDB** support for AI coding agents. This repo packages the same
MariaDB capability — a curated set of agent **skills** plus the native
**`mariadb-shell` MCP server** — for three agent tools:

| Agent | Plugin | Test suite | CI workflow |
| ----- | ------ | ---------- | ----------- |
| [Claude Code](https://claude.com/claude-code) | [`claude/dev-plugin`](claude/dev-plugin) | [`claude/dev-plugin-tests`](claude/dev-plugin-tests) | [claude-test.yml](.github/workflows/claude-test.yml) |
| [Codex](https://openai.com/codex) | [`codex/dev-plugin`](codex/dev-plugin) | [`codex/dev-plugin-test`](codex/dev-plugin-test) | [codex-test.yml](.github/workflows/codex-test.yml) |
| [OpenCode](https://opencode.ai) | [`opencode/dev-plugin`](opencode/dev-plugin) | [`opencode/dev-plugin-test`](opencode/dev-plugin-test) | [opencode-test.yml](.github/workflows/opencode-test.yml) |

Each plugin ships **25 skills** (24 vendored from upstream + 1 local), baseline
**MariaDB 11.8 LTS**, and the same auto-downloading `mariadb-shell` MCP server.

## What each plugin provides

1. **Skills** — MariaDB agent skills (`SKILL.md` docs) covering SQL statements,
   functions, client tools, and topical deep-dives. 24 are vendored from
   [`mariadb-corporation/mariadb-docs/agent-skills`](https://github.com/mariadb-corporation/mariadb-docs/tree/main/agent-skills);
   1 (`mariadb-schema-create-script`) is maintained locally in
   [additional-skills/](additional-skills). The agent surfaces the right skill by
   its `description` "Use when …" trigger.
2. **A native MCP server** — the [`mariadb-shell`](https://github.com/mariadb-corporation/mariadb-shell)
   binary, launched by [scripts/mariadb-mcp-launcher.sh](claude/dev-plugin/scripts/mariadb-mcp-launcher.sh)
   (and `.cmd` for native Windows). On first use it detects OS/arch, downloads the
   matching release into a user cache, verifies its checksum, and runs it as the
   MCP server over stdio. Subsequent runs reuse the cached binary.

> NOTE: The MCP server configuration/loading scripts are currently disabled until the MariaDB Shell is available.
> While the `mariadb-shell` repo is private, set `GH_TOKEN` so the launcher can
> authenticate to the GitHub release download.

## Installation

### Claude Code

```text
/plugin marketplace add mariadb-corporation/ai-plugins
/plugin install dev@mariadb
```

### Codex

```text
/plugin marketplace add mariadb-corporation/ai-plugins
/plugin install dev@mariadb
```

Reload (`/reload-plugins`) if Codex doesn't pick it up automatically. See
[codex/dev-plugin/README.md](codex/dev-plugin/README.md) for details.

### OpenCode

OpenCode has no central marketplace. Merge the `mcp` block from
[opencode/dev-plugin/opencode.json](opencode/dev-plugin/opencode.json) into your
`opencode.json`, point `MARIADB_DEV_PLUGIN` at the plugin dir, and symlink its
flat `skills/` into an OpenCode skills directory. Full steps in
[opencode/dev-plugin/README.md](opencode/dev-plugin/README.md).

## Repository layout

```text
ai-plugins/
├── .claude-plugin/marketplace.json    # Claude Code marketplace entry
├── .codex-plugin/marketplace.json     # Codex marketplace entry
├── additional-skills/                 # repo-local skills, vendored into every plugin
│   └── mariadb-schema-create-script/
├── claude/
│   ├── dev-plugin/                    # the Claude Code plugin (skills/, scripts/, .mcp.json)
│   └── dev-plugin-tests/              # its 3-tier pytest suite
├── codex/
│   ├── dev-plugin/
│   └── dev-plugin-test/
├── opencode/
│   ├── dev-plugin/
│   └── dev-plugin-test/
├── scripts/
│   └── sync-skills.sh                 # vendors skills into all three plugins
└── .github/workflows/                 # one CI workflow per plugin
```

## Skills sync

Skills are **vendored** into each plugin — the plugins are self-contained and are
never edited by hand. [scripts/sync-skills.sh](scripts/sync-skills.sh) is the
single source of truth:

```sh
scripts/sync-skills.sh          # use the pinned upstream ref
scripts/sync-skills.sh <ref>    # override with a tag / branch / commit
```

It downloads the upstream `agent-skills/` tree once at a pinned ref, copies every
skill plus the local `additional-skills/` into each plugin's `skills/` dir, and
writes per-plugin provenance to `skills-source.json`.

**Flat layout.** All three plugins vendor skills flat — `skills/<skill>/SKILL.md`
— regardless of how they are grouped upstream. This is what OpenCode requires (it
discovers skills only one directory deep) and it keeps every plugin identical on
disk. The vendored `.skills-manifest.json` is rewritten to flat paths while
preserving each skill's layer grouping, so the manifest-driven test suites still
resolve. Requires `jq` and `curl`.

## Testing

Each plugin has a parallel **3-tier pytest suite**:

| Tier | Marker | Needs | Checks |
| ---- | ------ | ----- | ------ |
| 1. Static / structural | `static` | nothing | frontmatter, manifest↔disk consistency, cross-references, SQL fences, statement-skill contract |
| 2. SQL execution | `db` | MariaDB 11.8 | the skills' recommended DDL runs on a live server with the documented effect |
| 3. Behavioral evals | `eval` | an LLM API key | the skill steers the model toward the MariaDB-preferred form (opt-in; deselected by default) |

```sh
cd claude/dev-plugin-tests      # or codex/ , opencode/ dev-plugin-test
pip install -r requirements.txt
pytest -m static                # fast, no services
pytest -m db                    # needs a MariaDB 11.8 server (docker-compose.yml provided)
pytest -m eval                  # opt-in, calls the LLM API
```

The eval tier uses the SDK matching its agent: the Claude and OpenCode suites call
the Anthropic SDK (`claude-opus-4-8`, needs `ANTHROPIC_API_KEY`); the Codex suite
calls the OpenAI SDK. CI runs `static` on every push/PR, `db` on PRs, and `eval`
nightly / on demand.

## License

Plugin code is **GPL-2.0** (see each plugin's `LICENSE`). Skills vendored from the
topical layer are redistributed under **MIT** — see the `skills/topical/LICENSE`
and `VENDORED.md` inside each plugin.
