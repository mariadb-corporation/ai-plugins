---
name: mariadb-schema-management-develop
description: "Develop the next version of a MariaDB Schema Management (MSM) schema in development/<schema>_next.sql: by section, or with msm.edit_schema / msm.add_schema_object, which change tables, columns, keys, views and routines in the SQL and keep the migration for the next update script; create and lay out schema diagrams; and split large sections into SOURCE-included files under development/sections/ with msm.split_sections. Use when evolving an existing MSM schema, editing the _next.sql script, adding, renaming or changing schema objects, working on an MSM schema diagram, or splitting a growing script. Read mariadb-schema-management first for the section model."
---

# MSM — Developing the Next Version

After a release, `prepare_release` has already bumped the development version and
you continue editing `development/<schema>_next.sql` toward the next release.
This skill covers iterating on that script, schema edits with `msm.edit_schema`,
schema diagrams, and the **SOURCE breakout** files that keep the script
maintainable. See `mariadb-schema-management` for the section
model. Assume MariaDB 11.8.

## Iterating on `_next.sql`

Make changes in the same sections you authored initially, using
`msm.set_section_sql_content` / `msm.get_sql_content_from_section`:

- New/changed **tables, sequences and data** → section 140.
- New/changed **views, routines, triggers, events** → section 150 (idempotent:
  `CREATE OR REPLACE` / `DROP IF EXISTS`). This is the ONLY place for them: the
  target's section 150 runs in full on every deployment, so upgraded schemas
  get them too. Removing an object additionally needs a `DROP ... IF EXISTS` in
  the update script: section 260 for a procedure or function, 240 for anything
  else.
- **Grants/roles** → section 170 (`CREATE ROLE IF NOT EXISTS`, then `GRANT`);
  it also runs on every deployment. Revoking a privilege additionally needs a
  `REVOKE` in the update script's section 270.
- **Diagrams** → section 160 is written by msm only (see "Schema diagrams"
  below). After changing CREATE statements by hand, run
  `msm.update_schema_definition` so the schema snapshot and the diagrams follow
  (figures of dropped tables are removed).

The development file always describes the **full, current** schema (not a diff) —
it is the source for the next version snapshot. The per-release *migration* from
the previous version is written separately when you prepare the release (see
`mariadb-schema-management-release`, sections 240/270).

Keep the development version in section 910 current with
`msm.set_development_version` as the target version firms up.

## Changing the schema with `msm.edit_schema`

`msm.edit_schema` makes schema changes in the SQL for you, through the MariaDB SQL
language server (`mariadb-lsp`): in `_next.sql` and every breakout file, in the
style of the statements around it.
Prefer it over editing by hand, for renames in particular: a rename reaches the
definition and every reference (foreign keys, indexes, views, routine and
trigger bodies, `GRANT`s, `DROP ... IF EXISTS`), and the diagrams follow a
renamed table, view or routine, while one renamed by hand disappears from them.

```text
msm.get_schema_diagrams()   # the schema_definition row has source_hash;
                            # diagram="<name>" leaves the other diagrams out

msm.edit_schema(
    base_hash="<that source_hash>",
    edits=[
        {"op": "rename_table", "table": "note", "new_name": "notes"},
        {"op": "add_column", "table": "notes",
         "column": {"name": "author_id", "type": "INT UNSIGNED", "nullable": False},
         "after": "id"},
        {"op": "add_foreign_key", "table": "notes", "foreign_key": {
            "name": "fk_notes_author", "columns": ["author_id"],
            "references": {"table": "author", "columns": ["id"]}}},
    ],
)
```

Put related edits in one call: they apply in order, so a later one uses the names
an earlier one gave.
Objects are given in the shape `msm.get_schema_diagrams`' snapshot has them; a
member left out takes the snapshot's default (`nullable` true, no `comment`, ...),
so send a column's whole definition to `modify_column`.

| Op | Members |
| --- | --- |
| `rename_table`, `rename_view` | `table` / `view`, `new_name` |
| `rename_column` | `table`, `column`, `new_name` |
| `rename_routine`, `drop_routine` | `routine`, `new_name` (rename), `kind` = `procedure` or `function` when both kinds have the name |
| `add_table` | `table`: `name`, `columns`, `indexes`, `foreign_keys`, `options` |
| `drop_table` | `table` |
| `add_column` | `table`, `column`, and `after` (a column name) or `first` |
| `modify_column` | `table`, `column` (its name now), `new_column` (a new `name` renames it too) |
| `drop_column` | `table`, `column` |
| `set_table_options` | `table`, `options` (`{"engine": ..., "comment": ...}`; `null` removes one) |
| `add_index` | `table`, `index`: `name`, `kind` (`unique`, ...), `columns` (or `key_parts` for lengths and order) |
| `drop_index` | `table`, and `name`, `kind: "primary"`, or `columns` (an unnamed index) |
| `set_primary_key` | `table`, `columns` |
| `add_foreign_key` | `table`, `foreign_key`: `name`, `columns`, `references` (`table`, `columns`), `on_delete`, `on_update` |
| `drop_foreign_key` | `table`, and `name` or `columns` (an unnamed key) |
| `add_view` | `view`: `name`, `definition` (the `SELECT` alone) |
| `drop_view` | `view` |
| `add_routine` | `routine`: `name`, `kind`, `parameters`, `returns` (a function), `body` |
| `add_trigger` | `trigger`: `name`, `timing` (`BEFORE`, `AFTER`), `events` (`INSERT`, ...), `table`, `body` |
| `rename_trigger`, `drop_trigger` | `trigger`, `new_name` (rename) |
| `add_event` | `event`: `name`, `schedule` (`EVERY 1 DAY`, ...), `body` |
| `rename_event`, `drop_event` | `event`, `new_name` (rename) |
| `add_sequence` | `sequence`: `name`, and `type`, `start`, `increment`, ... where wanted |
| `rename_sequence`, `drop_sequence` | `sequence`, `new_name` (rename) |

- New tables and sequences go into section 140; views, routines, triggers and
  events into section 150, written so the section can run again
  (`CREATE OR REPLACE`, or `DROP ... IF EXISTS` first). No index is written for a foreign key: send `add_index` first where
  one should be (a 1:1 relationship's `UNIQUE`).
- An index or foreign key sent without a `name` (`add_index`, `add_foreign_key`,
  `add_table`) gets one in the script: an index its first column's name (`_2`,
  `_3`, ... when taken), a foreign key `fk_<table>_<referenced table>`. So a
  later drop of it migrates too; dropping a key the script already had without a
  name has no migration (note `no-migration`).
- Refused, with nothing written: a drop of a table, column or index that a
  foreign key (or an `AUTO_INCREMENT` column) still needs, of a sequence a
  column's default takes values from, or of a trigger another one `FOLLOWS` or
  `PRECEDES` (`referenced`: drop what needs it first); a name already taken; an
  unknown object.
- It needs a `mariadb-lsp` with the `edit` command (an older one does fewer ops,
  and the call names those it cannot do). With a binary that lacks the op, make
  the change by hand, run `msm.update_schema_definition`, and add renamed objects
  back to the diagrams with `msm.layout_schema_diagram`; without any
  `mariadb-lsp`, those tools fail too.
- `base_hash` is the stored snapshot's `source_hash`; the first of the result's
  `rows` is the new snapshot, with the `source_hash` for the next call. A call against a
  snapshot made again since is refused: read it again and redo the edits. Without
  a snapshot, or after editing the SQL by hand, run
  `msm.update_schema_definition` first.
- All edits are applied, or none. Check every entry of `notes` (e.g.
  `still-referenced`, `no-migration`).
- **After the first release**, each edit's migration statements are kept in
  the pending update script `development/<schema>_update_next.sql`: table
  changes and the DROPs of tables, sequences, views, triggers and events for
  240, routine DROPs for 260 (a new view, routine, trigger or event needs none:
  150 creates it). The next `prepare_release` moves them into the new update
  script (see `mariadb-schema-management-release`). They take the schema along, not its
  data: a `NOT NULL` column added to a table with rows gets the type's default
  (`0` for a number), not a valid reference, so a backfill has to run before a
  foreign key on it.
  Changes you make by hand are not kept:
  their migration is still yours to write at release time.

### Adding an object from a template

`msm.add_schema_object(kind, name, base_hash, template=None, table=None)` adds a
`view`, `procedure`, `function`, `trigger` (needs `table`), `event` or
`sequence` from msm's template (`msm.get_object_templates`) or your own: one
plain CREATE of that kind with unqualified names and the placeholders
`${name}`, `${schema}` and, for a trigger, `${table}`. A sequence goes into 140
before the first table, the rest into 150. It returns the `file` and `line`
where the new statement starts, so you can fill in its body. Refused: a name
taken (tables, views and sequences share one namespace), an unknown table, a
stale `base_hash`.

## Schema diagrams

Make and change the diagrams of section 160 through the tools, never in the SQL:

| Task | Tool |
| --- | --- |
| New diagram | `msm.create_schema_diagram(name, tables=, views=, sequences=, routines=, events=)`: all tables by default, laid out; the other objects only when named |
| Add objects, tidy up | `msm.layout_schema_diagram(name, tables=, views=, sequences=, routines=, events=, keep_placed=True)`: places the figures without a position; `keep_placed=False` lays all out again |
| Read | `msm.list_schema_diagrams`, `msm.get_schema_diagrams(diagram=)`; `msm.get_schema_diagram_image` for a picture they leave out |
| Change by hand | `msm.set_schema_diagram(document)`: an `msm-diagram/1` document; figure types `TableFigure` (its card lists the table's triggers unless `triggersExpanded` is false), `ViewFigure`, `SequenceFigure`, `RoutineGroupFigure` (`routines`), `EventGroupFigure` (`events`), `NoteFigure`, `ImageFigure`; a figure without `left`/`top` is placed by the layout; an `ImageFigure` sent without its picture keeps the stored one |
| Rename | `msm.rename_schema_diagram(name, new_name)`: refused for a name another diagram has, compared case-insensitively |
| Remove | `msm.remove_schema_diagram(name)` |

## SOURCE breakout files (keeping the script maintainable)

When a section grows large, move its body into one or more files under
`development/sections/` and reference them from `_next.sql` with a `SOURCE`
statement. MSM inlines this content when it snapshots the version during
`prepare_release`, so SOURCE is purely a **development-time** organizing tool —
released version and deployment scripts are always fully inlined.

### Syntax

```sql
SOURCE '<relative-or-absolute-path>'[<start>:<end>]; -- optional comment
```

- The `[start:end]` slice is optional and selects the part of the referenced
  file to inline; without it (or with `[:]`) the whole file is inlined. Each
  bound is empty, a **line number** `lnN`, or a **character offset**, and the two
  kinds mix freely:
  - `[ln4:]` — from line 4 on (drop a three-line copyright header).
  - `[ln4:ln-4]` — lines 4 through the 4th-last (drop the last three too).
    Lines count from 1, the end line is included, `ln-1` is the last line.
  - `[53:]` — drop the first 53 characters (Python slice; negative counts from
    the end, so `[663:-115]` also drops a 115-character footer).
- Line numbers and the optional slice need a MariaDB Shell newer than 26.10.2
  (its `msm_plugin` with mariadb-shell-plugins PR #60). With 26.10.2 or older,
  always give a slice of character offsets: there a `SOURCE` line without a
  slice is copied into the release verbatim and fails the deployment, and `[:]`
  makes `prepare_release` fail.
- Relative paths resolve against the **development/** folder (where `_next.sql`
  lives), so use `'./sections/...'`.
- The leading indentation of the `SOURCE` line is applied to every inlined line.

### Why the slice

Each breakout file is a **standalone, valid SQL file** with its own copyright
header (and optionally a footer). The slice strips that header/footer so only the
object definitions are inlined into `_next.sql`. Prefer line numbers: `[ln4:]`
stays right when the header's text changes but not its line count, while a
character offset must be recounted whenever the header is edited.

### Example

`development/<schema>_next.sql`, section 140 body:

```sql
SOURCE './sections/140-10_tables.sql'[663:-115]; -- Ignore header and footer
SOURCE './sections/140-30_inserts.sql'[53:];     -- Remove copyright header
```

section 150 body:

```sql
SOURCE './sections/150-10_procedures_functions.sql'[ln4:];
SOURCE './sections/150-20_views.sql'[ln4:];
SOURCE './sections/150-30_triggers.sql'[ln4:];
```

### When to break out

Keep a section inline while its body is small; once it grows past the project's
`maxInlineSectionSize` (default 16 KB, optional key in `msm.project.json`) move
it into breakout files. msm does this itself for section 160 (the diagrams VIEW
nearly always exceeds it), and the imports for every large section. A project
that wants a single `_next.sql` file sets a large `maxInlineSectionSize` (with
`msm.set_project_settings`).

**`msm.split_sections(sections=["140", "150", "170"])`** does the split for
you: it moves each statement, with the comments above it, into the files below
and replaces the section body with their `SOURCE ...[lnN:]` lines. A section
that already includes a file, has nothing to move, or has a statement of no
known kind between two that move is left as it is and reported in `skipped`;
running it twice changes nothing.

### Splitting existing sections: `msm.split_sections`

To break existing sections out, let `msm.split_sections` move the statements
rather than moving them by hand:

```text
msm.split_sections(sections=["150"])     # default: 140, 150 and 170
```

It moves each statement, with the comments above it, into the file for its kind
(table below), leaves a `SOURCE` line per file, and lists the sections it left
as they are in `skipped`, with the reason.

### File naming convention

Name breakout files `<section-id>-<NN>_<topic>.sql` so they sort in load order
and map back to their section, e.g. `140-10_tables.sql`,
`140-30_inserts.sql`, `150-10_procedures_functions.sql`, `170_roles.sql`.
Split by object kind (the names `msm.split_sections` and the Workbench import
use) — **routines before views**, since a view on a function that does not
exist yet fails:

| File | Holds |
| --- | --- |
| `140-10_tables.sql` | `CREATE TABLE`, `CREATE SEQUENCE` |
| `140-20_table_additions.sql` | `CREATE INDEX`, and `ALTER TABLE` that only adds keys, indexes or constraints (e.g. FKs between the tables) |
| `140-30_inserts.sql` | base-data `INSERT`s |
| `150-10_procedures_functions.sql` | routines |
| `150-20_views.sql` | `CREATE OR REPLACE VIEW` |
| `150-30_triggers.sql` | triggers |
| `150-40_events.sql` | events |
| `160_schema_diagrams.sql` | the diagrams VIEW — written by msm |
| `170_roles.sql` | roles and grants |

### Rules

- Respect the section's placement/delimiter rule even in breakout files: content
  destined for 140/170 must be plain `;`-terminated (it lands in a
  stored-procedure body); content for 150 uses `DELIMITER %%` for routine bodies.
- **Routines before views** in section 150 (see `mariadb-schema-management-create`),
  hence `150-10_procedures_functions` before `150-20_views`.
- Keep the `SOURCE` lines inside the correct MSM section of `_next.sql`; edit that
  section body via `msm.set_section_sql_content` so the banners stay intact.
- After editing breakout files, a `prepare_release` will inline them; verify the
  generated version snapshot looks complete.

## Next

When the development version is feature-complete, prepare a release:
`mariadb-schema-management-release`.

## See Also

- `mariadb-schema-management` — lifecycle overview and full section model.
- `mariadb-schema-management-create` — the initial project + first authoring.
- `mariadb-schema-management-release` — snapshot the version and write the migration (including what `msm.edit_schema` kept).
- `mariadb-alter-table`, `mariadb-create-view`, `mariadb-create-procedure` — the DDL you edit here.
