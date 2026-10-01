#!/usr/bin/env python3
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

"""Generate the Skills Reference pages of the reference docs.

The skill tables are generated, not hand-written, so they cannot drift from
what the plugins ship. Run after `scripts/sync-skills.sh` (which regenerates
docs/_data/skills.yml, the grouping read here):

    python3 docs-ref/scripts/generate-skill-pages.py

Reads:
  * docs/_data/skills.yml                 — layers, their order, the sql flag
  * claude/dev-plugin/skills/*/SKILL.md   — each skill's description
  * claude/contributor-plugin/skills/     — the contributor plugin's skills
  * additional-skills/<group>/<skill>/    — which group a local skill is in

Writes one GitBook page per layer under
docs-ref/content/mariadb-ai-plugins/skills-reference/. The section README is
hand-written and not touched.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CATALOG = REPO / "docs/_data/skills.yml"
DEV_SKILLS = REPO / "claude/dev-plugin/skills"
CONTRIBUTOR_SKILLS = REPO / "claude/contributor-plugin/skills"
ADDITIONAL = REPO / "additional-skills"
OUT = REPO / "docs-ref/content/mariadb-ai-plugins/skills-reference"

# layer id → (file name, page title, page description, intro paragraph)
PAGES = {
    "granular-statements": (
        "sql-statement-skills.md",
        "SQL Statement Skills",
        "Reference for the MariaDB AI Plugins skills that cover individual SQL statements and their MariaDB-specific syntax and behavior.",
        "One skill per SQL statement. Each one covers the MariaDB-specific syntax and behavior that a generic SQL answer gets wrong, such as online DDL algorithms on `ALTER TABLE`, atomic `CREATE OR REPLACE`, and `RETURNING` on `INSERT`.",
    ),
    "granular-functions": (
        "built-in-function-skills.md",
        "Built-in Function Skills",
        "Reference for the MariaDB AI Plugins skills that cover MariaDB built-in function families.",
        "One skill per family of built-in functions, grouped by what the functions operate on.",
    ),
    "granular-tools": (
        "command-line-tool-skills.md",
        "Command-Line Tool Skills",
        "Reference for the MariaDB AI Plugins skills that cover the MariaDB command-line client and utilities.",
        "One skill per MariaDB command-line program, covering the options and behavior that differ from their MySQL counterparts.",
    ),
    "granular-connectors": (
        "connector-skills.md",
        "Connector Skills",
        "Reference for the MariaDB AI Plugins skills that cover installing and using the MariaDB connectors.",
        "Two skills per MariaDB connector: one for installing and configuring it, one for using it from application code.",
    ),
    "topical": (
        "topical-skills.md",
        "Topical Skills",
        "Reference for the MariaDB AI Plugins topical skills, which cover subjects that span many statements.",
        "Skills about a subject rather than a single statement, such as migrating from MySQL or vector search.",
    ),
    "additional": (
        "additional-skills.md",
        "Additional Skills",
        "Reference for the skills maintained in the MariaDB AI Plugins repository itself: schema scripts, MariaDB REST Service, schema management, migration, and Laravel.",
        "Skills maintained in the `additional-skills/` directory of the MariaDB AI Plugins repository, rather than vendored from the MariaDB documentation. Many of them drive the MCP server's tools.",
    ),
}

ADDITIONAL_GROUPS = {
    "sql": ("SQL Scripts", "Writing schema create scripts."),
    "rest": ("MariaDB REST Service", "Creating and managing REST endpoints with the MariaDB REST Service."),
    "schema-management": ("Schema Management", "The MariaDB Schema Management (MSM) project lifecycle, driven by the `msm.*` tools."),
    "migrator": ("MySQL to MariaDB Migration", "Migrating a MySQL database to MariaDB, driven by the optional `migrator.*` tools."),
    "laravel": ("Laravel", "Using MariaDB from Laravel applications. Shipped with the `dev` plugin only."),
}



def parse_catalog(text):
    """A minimal reader for docs/_data/skills.yml (a fixed, generated shape)."""
    layers, layer, skill = [], None, None
    for line in text.splitlines():
        if m := re.match(r"^- id: (.+)$", line):
            layer = {"id": m[1].strip(), "skills": []}
            layers.append(layer)
        elif m := re.match(r"^    - name: (.+)$", line):
            skill = {"name": m[1].strip(), "sql": False}
            layer["skills"].append(skill)
        elif m := re.match(r"^      sql: (true|false)$", line):
            skill["sql"] = m[1] == "true"
    return layers


def description(skill_dir):
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    fm = re.match(r"^---\n(.*?)\n---", text, re.S)
    m = re.search(r'^description:\s*(?:"((?:[^"\\]|\\.)*)"|(.+))$', fm[1], re.M)
    desc = (m[1] if m[1] is not None else m[2]).replace('\\"', '"').replace("\\\\", "\\")
    # The trailing "Use when …" sentence is addressed to the agent, not the reader.
    desc = re.split(r"\s+Use (?:when|this)\b", desc, maxsplit=1)[0].strip()
    return desc.replace("|", "\\|")


def table(rows, with_plugins=True):
    head = "| Skill | Plugins | What it covers |\n| --- | --- | --- |\n" if with_plugins else "| Skill | What it covers |\n| --- | --- |\n"
    body = ""
    for name, plugins, desc in rows:
        body += f"| `{name}` | {plugins} | {desc} |\n" if with_plugins else f"| `{name}` | {desc} |\n"
    return head + body


def page(title, desc, intro, body):
    return (
        "---\n"
        f"description: >-\n  {desc}\n"
        "---\n\n"
        f"# {title}\n\n"
        f"{intro}\n\n"
        f"{body}"
    )


def rows_for(skills):
    return [
        (s["name"], "`dev`, `sql`" if s["sql"] else "`dev`", description(DEV_SKILLS / s["name"]))
        for s in skills
    ]


def main():
    layers = parse_catalog(CATALOG.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    written = []

    for layer in layers:
        if layer["id"] not in PAGES:
            raise SystemExit(f"no page defined for layer {layer['id']!r} — add it to PAGES")
        file_name, title, desc, intro = PAGES[layer["id"]]

        if layer["id"] == "additional":
            group_of = {
                skill.name: group.name
                for group in ADDITIONAL.iterdir() if group.is_dir()
                for skill in group.iterdir() if (skill / "SKILL.md").exists()
            }
            body = ""
            for group, (heading, blurb) in ADDITIONAL_GROUPS.items():
                skills = [s for s in layer["skills"] if group_of.get(s["name"]) == group]
                if skills:
                    body += f"## {heading}\n\n{blurb}\n\n{table(rows_for(skills))}\n"
            unknown = [s["name"] for s in layer["skills"] if group_of.get(s["name"]) not in ADDITIONAL_GROUPS]
            if unknown:
                raise SystemExit(f"additional skills in no known group: {unknown}")
        else:
            body = table(rows_for(layer["skills"]))

        (OUT / file_name).write_text(page(title, desc, intro, body), encoding="utf-8")
        written.append(file_name)

    contributor = sorted(p.parent.name for p in CONTRIBUTOR_SKILLS.glob("*/SKILL.md"))
    body = table([(n, None, description(CONTRIBUTOR_SKILLS / n)) for n in contributor], with_plugins=False)
    (OUT / "contributor-skills.md").write_text(
        page(
            "Contributor Skills",
            "Reference for the skills in the MariaDB AI Plugins contributor plugin, for working on MariaDB tooling itself.",
            "The skills of the `contributor` plugin, vendored from the MariaDB Shell repository. They are for developing MariaDB Shell and its plugins, not for using MariaDB, and the `contributor` plugin ships no MCP server.",
            body,
        ),
        encoding="utf-8",
    )
    written.append("contributor-skills.md")
    print(f"wrote {len(written)} pages to {OUT.relative_to(REPO)}: {', '.join(written)}")


if __name__ == "__main__":
    main()
