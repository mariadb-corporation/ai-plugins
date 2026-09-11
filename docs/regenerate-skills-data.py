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

"""Regenerate docs/_data/skills.yml from the vendored skill manifests.

The DevHub's skill catalog is generated rather than hand-maintained so it cannot
drift from what the plugins actually ship. Run this after `scripts/sync-skills.sh`:

    python3 docs/regenerate-skills-data.py

Reads the `dev` plugin's manifest for the full list and the `sql` plugin's for
the subset marker, both from the `claude/` plugins (all harnesses vendor the
same content).
"""

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEV = REPO / "claude/dev-plugin/skills/.skills-manifest.json"
SQL = REPO / "claude/sql-plugin/skills/.skills-manifest.json"
OUT = REPO / "docs/_data/skills.yml"

# Prose for each manifest layer. A layer with no entry here still renders, using
# its raw id as the title — so a new upstream layer shows up rather than vanishing.
LAYER_TEXT = {
    "granular-statements": (
        "SQL statements",
        "One skill per statement, each covering the MariaDB-specific syntax and "
        "behaviour that a generic SQL answer gets wrong — online DDL algorithms on "
        "ALTER TABLE, atomic CREATE OR REPLACE, RETURNING on INSERT, IGNORED "
        "indexes, and so on.",
    ),
    "granular-functions": (
        "Built-in functions",
        "The function families, grouped by what they operate on. Includes the "
        "traps: aggregates skip NULLs, GROUP_CONCAT truncates silently at "
        "group_concat_max_len, and ONLY_FULL_GROUP_BY is not in the default sql_mode.",
    ),
    "granular-tools": (
        "Command-line tools",
        "The client and utility programs — how batch mode changes the output "
        "format, what --flashback generates, and why mysql is still a symlink for "
        "the same binary.",
    ),
    "granular-connectors": (
        "Connectors",
        "Two skills per connector: installing and configuring it, and writing "
        "application code against it. Placeholder styles, autocommit defaults, "
        "prepared-statement behaviour and pooling all differ per connector, and are "
        "the usual source of bugs.",
    ),
    "topical": (
        "Topical guides",
        "Cross-cutting subjects that do not map to a single statement: query "
        "optimization, vector search, system-versioned tables, and what changes "
        "when an application moves from MySQL.",
    ),
    "additional": (
        "Shipped by this repository",
        "The skills maintained here rather than vendored from the docs repo — the "
        "MariaDB REST Service DDL, the Schema Management lifecycle, the "
        "create-script conventions, and the MySQL-to-MariaDB migrator.",
    ),
}


def names(manifest_path):
    manifest = json.loads(manifest_path.read_text())
    return manifest["layers"]


def main():
    dev_layers = names(DEV)
    sql_names = {s["name"] for layer in names(SQL).values() for s in layer["skills"]}

    lines = [
        "# GENERATED FILE — do not edit by hand.",
        "# Regenerate with: python3 docs/regenerate-skills-data.py",
        "# Source: claude/{dev,sql}-plugin/skills/.skills-manifest.json",
    ]
    for layer_id, layer in dev_layers.items():
        title, description = LAYER_TEXT.get(layer_id, (layer_id, ""))
        lines.append(f"- id: {layer_id}")
        lines.append(f"  title: {json.dumps(title, ensure_ascii=False)}")
        lines.append(f"  description: {json.dumps(description, ensure_ascii=False)}")
        lines.append("  skills:")
        for skill in layer["skills"]:
            lines.append(f"    - name: {skill['name']}")
            lines.append(f"      sql: {str(skill['name'] in sql_names).lower()}")
    OUT.write_text("\n".join(lines) + "\n")

    total = sum(len(layer["skills"]) for layer in dev_layers.values())
    print(f"{OUT.relative_to(REPO)}: {len(dev_layers)} layers, "
          f"{total} dev skills, {len(sql_names)} in the sql subset")


if __name__ == "__main__":
    main()
