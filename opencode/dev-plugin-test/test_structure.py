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
