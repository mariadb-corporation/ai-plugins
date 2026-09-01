# Copyright (c) 2026, MariaDB plc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License, version 2.0,
# as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See
# the GNU General Public License, version 2.0, for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA

"""Tier 1 — static / structural checks of the vendored skills.

No DB, no LLM: fast and deterministic, suitable as the always-on CI gate.
Parametrized over every skill in the manifest (plus a few suite-wide invariants).
"""

from __future__ import annotations

import pytest

from lib import skills

pytestmark = pytest.mark.static

ALL_SKILLS = skills.load_skills()
STATEMENT_SKILLS = skills.statement_skills()
ADDITIONAL_SKILLS = skills.additional_skills()


def _id(s: skills.Skill) -> str:
    return s.name


# --- per-skill frontmatter / naming -----------------------------------------


@pytest.mark.parametrize("skill", ALL_SKILLS, ids=_id)
def test_skill_md_exists(skill: skills.Skill):
    assert skill.path.is_file(), f"missing SKILL.md at {skill.rel_path}"


@pytest.mark.parametrize("skill", ALL_SKILLS, ids=_id)
def test_frontmatter_has_name_and_description(skill: skills.Skill):
    fm = skill.frontmatter
    assert isinstance(fm.get("name"), str) and fm["name"].strip(), "frontmatter missing non-empty `name`"
    desc = fm.get("description")
    assert isinstance(desc, str) and len(desc.strip()) >= 20, "frontmatter missing a substantive `description`"


@pytest.mark.parametrize("skill", ALL_SKILLS, ids=_id)
def test_frontmatter_name_matches_dir(skill: skills.Skill):
    assert skill.frontmatter.get("name") == skill.dir_name, (
        f"frontmatter name {skill.frontmatter.get('name')!r} != directory {skill.dir_name!r}"
    )


@pytest.mark.parametrize("skill", ALL_SKILLS, ids=_id)
def test_manifest_name_matches_frontmatter(skill: skills.Skill):
    assert skill.name == skill.frontmatter.get("name"), (
        f"manifest name {skill.name!r} != frontmatter name {skill.frontmatter.get('name')!r}"
    )


@pytest.mark.parametrize("skill", ALL_SKILLS, ids=_id)
def test_description_has_use_when_trigger(skill: skills.Skill):
    # The discoverability contract: every skill tells the agent when to use it.
    assert "use when" in skill.frontmatter.get("description", "").lower(), (
        "description should contain a 'Use when …' trigger clause"
    )


@pytest.mark.parametrize("skill", ALL_SKILLS, ids=_id)
def test_sql_fences_balanced(skill: skills.Skill):
    assert skill.fence_count() % 2 == 0, "unbalanced ``` code fences in SKILL.md"


@pytest.mark.parametrize("skill", ALL_SKILLS, ids=_id)
def test_see_also_refs_resolve(skill: skills.Skill):
    known = skills.skill_names()
    dangling = {r for r in skill.see_also_refs() if r not in known}
    assert not dangling, f"See Also references unknown skills: {sorted(dangling)}"


# --- statement-skill content contract ---------------------------------------


@pytest.mark.parametrize("skill", STATEMENT_SKILLS, ids=_id)
def test_statement_has_llms_often_miss(skill: skills.Skill):
    assert skills.has_section(skill.body, "What LLMs Often Miss"), (
        "statement skills must carry a 'What LLMs Often Miss' section"
    )


@pytest.mark.parametrize("skill", STATEMENT_SKILLS, ids=_id)
def test_statement_has_runnable_sql(skill: skills.Skill):
    assert skill.sql_blocks(), "statement skills must include at least one ```sql block"


# --- suite-wide invariants ---------------------------------------------------


def test_manifest_paths_exist_on_disk():
    missing = [s.rel_path for s in ALL_SKILLS if not s.path.is_file()]
    assert not missing, f"manifest lists skills not on disk: {missing}"


def test_every_disk_skill_is_in_manifest():
    manifest_paths = {(skills.SKILLS_ROOT / s.rel_path).resolve() for s in ALL_SKILLS}
    disk_paths = {p.resolve() for p in skills.discover_disk_skills()}
    orphans = disk_paths - manifest_paths
    assert not orphans, f"SKILL.md files on disk but absent from manifest: {sorted(map(str, orphans))}"


def test_skill_names_unique():
    names = [s.name for s in ALL_SKILLS]
    dupes = {n for n in names if names.count(n) > 1}
    assert not dupes, f"duplicate skill names: {sorted(dupes)}"


def test_expected_statement_skill_count():
    # Guardrail against an unintended change to the vendored set: the count of
    # granular statement skills. Bump this when sync-skills.sh pulls a ref that
    # legitimately adds or removes statement skills.
    assert len(STATEMENT_SKILLS) == 31, f"expected 31 statement skills, found {len(STATEMENT_SKILLS)}"


# --- vendored `additional` skills match their source in this repo ------------
#
# `additional-skills/` is the editable source; the copies under each plugin's
# skills/ are vendored by scripts/sync-skills.sh. Editing the source without
# re-running that script leaves every plugin shipping stale text, which no other
# check would notice: the manifest still agrees with what is on disk, and the
# stale copy still parses. This is the check that notices.


@pytest.mark.parametrize("skill", ADDITIONAL_SKILLS, ids=_id)
def test_additional_skill_matches_its_source(skill: skills.Skill):
    sources = skills.additional_sources(skill.name)
    assert sources, (
        f"no source for the vendored {skill.name!r} under additional-skills/*/ — "
        "it was removed from (or renamed in) the source tree without re-running "
        "scripts/sync-skills.sh"
    )
    assert len(sources) == 1, (
        f"{skill.name!r} exists in more than one additional-skills/ subfolder: "
        + ", ".join(str(p.relative_to(skills.REPO_ROOT)) for p in sources)
    )
    source = sources[0]
    assert skill.path.read_text(encoding="utf-8") == source.read_text(encoding="utf-8"), (
        f"vendored {skill.rel_path} differs from {source.relative_to(skills.REPO_ROOT)} — "
        "re-run scripts/sync-skills.sh from the repo root"
    )


# --- Codex MCP wiring (static: the file shape Codex actually reads) -----------
#
# Every mistake here registers a server that silently never starts, and nothing
# says so until a tool call finds no tools. Three facts drive these checks, all
# measured against a real Codex (0.147, re-verified on 0.151.0):
#
#   1. Codex reads the camelCase `mcpServers` key; a `mcp_servers` key is
#      ignored outright.
#   2. It expands NO placeholder when spawning a plugin's server — it execs the
#      stored `command` verbatim. `${CODEX_PLUGIN_ROOT}` is not a variable it
#      knows at all, and `${CLAUDE_PLUGIN_ROOT}` is not expanded on this path.
#   3. It does resolve a relative `cwd` against the plugin root, and resolves a
#      relative `command` from there. So the working shape is a relative,
#      *extensionless* command plus `"cwd": "."` — extensionless because that is
#      what lets one command name serve every OS: Unix runs the shim via its
#      shebang, while Windows walks %PATHEXT% onto the .cmd.
#
# Hence the command, the cwd and the launcher trio have to stay consistent with
# each other; each of these tests guards one leg of that.


def _mcp_server() -> dict:
    import json

    config = json.loads((skills.PLUGIN_ROOT / ".mcp.json").read_text(encoding="utf-8"))
    assert "mcpServers" in config, (
        "codex/dev-plugin/.mcp.json must declare `mcpServers` (camelCase); codex "
        f"ignores any other key, so it would register no server at all. Found: {list(config)}"
    )
    servers = config["mcpServers"]
    assert "mariadb" in servers, f"no `mariadb` server in .mcp.json: {list(servers)}"
    return servers["mariadb"]


def test_mcp_config_uses_the_key_codex_reads():
    _mcp_server()


def test_mcp_config_avoids_a_placeholder_codex_cannot_expand():
    raw = (skills.PLUGIN_ROOT / ".mcp.json").read_text(encoding="utf-8")
    assert "${" not in raw, (
        "codex/dev-plugin/.mcp.json contains a ${...} placeholder. Codex expands none "
        "of them when it spawns a plugin's MCP server — it execs the command verbatim, "
        'so the server dies with "No such file or directory". Use a relative command '
        'plus "cwd": "." instead.'
    )


def test_mcp_command_is_relative_extensionless_and_paired_with_cwd():
    server = _mcp_server()
    command = server.get("command", "")
    assert command == "./scripts/mariadb-mcp-launcher", (
        "codex/dev-plugin/.mcp.json `command` must be the relative, extensionless "
        f"./scripts/mariadb-mcp-launcher, not {command!r}. Relative because Codex expands "
        "no placeholder; extensionless because that is the only single name that resolves "
        "on macOS/Linux (shebang) and on Windows (%PATHEXT% -> .cmd) alike."
    )
    assert server.get("cwd") == ".", (
        'codex/dev-plugin/.mcp.json must set "cwd": "." — it is what Codex resolves to the '
        f"plugin root, and without it the relative command resolves from the user's "
        f"working directory and the server never starts. Found: {server.get('cwd')!r}"
    )


def test_launcher_trio_backs_the_extensionless_command():
    scripts = skills.PLUGIN_ROOT / "scripts"
    shim = scripts / "mariadb-mcp-launcher"
    real = scripts / "mariadb-mcp-launcher.sh"
    windows = scripts / "mariadb-mcp-launcher.cmd"

    for path in (shim, real):
        assert path.is_file(), f"missing launcher: {path}"
        # Codex execs the shim directly on Unix; without +x it dies with EACCES.
        assert path.stat().st_mode & 0o111, f"launcher is not executable: {path}"
    assert windows.is_file(), (
        f"missing {windows.name}: it is what %PATHEXT% resolution lands on for Windows, "
        "so without it the extensionless command has nothing to find there."
    )
    assert shim.read_text(encoding="utf-8").startswith("#!"), (
        f"{shim.name} needs a shebang: it has no extension, so the kernel has nothing "
        "else to go on when Codex execs it on macOS/Linux."
    )
