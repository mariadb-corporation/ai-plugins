---
name: mariadb-schema-management-develop
description: "Develop the next version of a MariaDB Schema Management (MSM) schema in development/<schema>_next.sql — rename tables, columns, views and routines with msm.edit_schema, keep schema diagrams (create, lay out, edit) in step, and keep large scripts maintainable by splitting sections into development/sections/ files linked with the SOURCE '<path>'[start:end]; statement (msm.split_sections). Use when evolving an existing MSM schema for a new version, editing the _next.sql development script, renaming tables, columns, views or routines, creating or laying out an MSM schema diagram, or splitting a growing schema script into SOURCE-included section files. Read mariadb-schema-management first for the section model."
---

# MSM — Developing the Next Version

After a release, `prepare_release` has already bumped the development version and
you continue editing `development/<schema>_next.sql` toward the next release.
This skill covers iterating on that script and the **SOURCE breakout** mechanism
for keeping it maintainable. See `mariadb-schema-management` for the section
model. Assume MariaDB 11.8.

## Iterating on `_next.sql`

Make changes in the same sections you authored initially, using
`msm.set_section_sql_content` / `msm.get_sql_content_from_section`:

- New/changed **tables and data** → section 140.
- New/changed **views, routines, triggers, events** → section 150 (idempotent:
  `CREATE OR REPLACE` / `DROP IF EXISTS`). This is the ONLY place for them: the
  target's section 150 runs in full on every deployment, so upgraded schemas
  get them too. Removing an object additionally needs a `DROP ... IF EXISTS` in
  the update script's section 240.
- **Grants/roles** → section 170 (`CREATE ROLE IF NOT EXISTS`, then `GRANT`);
  it also runs on every deployment. Revoking a privilege additionally needs a
  `REVOKE` in the update script's section 270.

- **Diagrams** → section 160 is written by msm only (see "Schema diagrams"
  below). After changing CREATE statements by hand, run
  `msm.update_schema_definition` so the schema snapshot and the diagrams follow
  (figures of dropped tables are removed); never edit the `msm_schema_diagrams`
  VIEW or `sections/160_schema_diagrams.sql` by hand.

The development file always describes the **full, current** schema (not a diff) —
it is the source for the next version snapshot. The per-release *migration* from
the previous version is written separately when you prepare the release (see
`mariadb-schema-management-release`, sections 240/270).

Keep the development version in section 910 current with
`msm.set_development_version` as the target version firms up.

## Renaming with `msm.edit_schema`

`msm.edit_schema` renames schema objects in the SQL for you, through the MariaDB
SQL language server (`mariadb-lsp`): the definition and every reference — foreign
keys, indexes, views, routine and trigger bodies, `GRANT`s — in `_next.sql` and
every breakout file. Prefer it over renaming by hand: the diagrams follow a
renamed table, view or routine, while one renamed by hand disappears from them.

```text
msm.get_schema_diagrams()      # the schema_definition row's document has source_hash

msm.edit_schema(
    base_hash="<that source_hash>",
    edits=[
        {"op": "rename_table", "table": "note", "new_name": "notes"},
        {"op": "rename_column", "table": "notes", "column": "body", "new_name": "content"},
    ],
)
```

- Ops: `rename_table` (`table`, `new_name`), `rename_column` (`table`, `column`,
  `new_name`), `rename_view` (`view`, `new_name`), `rename_routine` (`routine`,
  `new_name`, and `kind` = `procedure` or `function` when both have the name).
  Edits apply in order, so a later one uses the new names. Other ops (add,
  change or drop tables, columns, indexes, foreign keys) are planned but refused
  as `unsupported` by today's binary: make those changes in the SQL by hand,
  then run `msm.update_schema_definition`.
- It needs a `mariadb-lsp` that has the `edit` command. Without one the call
  fails; then rename by hand, run `msm.update_schema_definition`, and add the
  renamed objects back to the diagrams with `msm.layout_schema_diagram`.
- `base_hash` is the stored snapshot's `source_hash`. If the snapshot was made
  again since you read it, the call is refused: read it again and redo the edits.
  A project without a snapshot needs `msm.update_schema_definition` first; do
  the same when `msm.list_schema_diagrams` says the snapshot is not `current`,
  so the names you read are the script's.
- All edits are applied, or none. Read `notes`: places the binary could not
  change itself (e.g. the name inside a string) for you to check.
- **After the first release**, each edit's migration statements (e.g.
  `RENAME TABLE`) are appended to `development/<schema>_update_next.sql`
  (sections 240 and 290). The next `prepare_release` moves them into the new
  update script. Changes you make by hand are not collected: their migration is
  still yours to write at release time.

## Schema diagrams

A project keeps its EER diagrams in section 160 (see the overview). Make and
change them through the tools, never in the SQL:

- **New diagram:** `msm.create_schema_diagram(name, tables=None, views=None,
  routines=None)` — all tables by default, laid out in layers (a referenced
  table above the tables that refer to it, few crossing lines, tables without
  foreign keys in rows below). Views and routines are added only when named;
  views get a figure each, routines share one routine group figure. Every
  foreign key between two tables shown gets a connection; views and routines get
  none.
- **Add to a diagram / tidy it:** `msm.layout_schema_diagram(name, tables=,
  views=, routines=, keep_placed=True)` adds the named objects and places every
  figure that has no position, as a block below the others. With
  `keep_placed=False` it lays every table, view and routine group figure out
  again. Figures on a layer, notes and images always keep their place.
- **Read:** `msm.list_schema_diagrams` (names, counts, and whether the snapshot
  is `current`), `msm.get_schema_diagrams(diagram=)` (the documents).
  Pictures of image figures are left out there (`image_size` gives their
  length); `msm.get_schema_diagram_image(diagram, figure_id)` returns one.
- **Change by hand:** `msm.set_schema_diagram(document)` replaces the diagram of
  that name with an `msm-diagram/1` document. Figure types: `TableFigure`
  (`table`), `ViewFigure` (`view`), `RoutineGroupFigure` (`routines`: names),
  `NoteFigure` (`text`), `ImageFigure` (`image`: a data URL). Send an image
  figure without `image` to keep its stored picture. Leave `left`/`top` out of
  a figure and `msm.layout_schema_diagram` places it.
- **Remove:** `msm.remove_schema_diagram(name)`.

`msm.create_schema_diagram` and `msm.layout_schema_diagram` make the snapshot
again first when the development script changed since, so they need the
`mariadb-lsp` binary too.

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
nearly always exceeds it) and for the large sections of a Workbench import. A
project that wants a single `_next.sql` file sets a large
`maxInlineSectionSize`.

### Splitting existing sections: `msm.split_sections`

To break existing sections out, let `msm.split_sections` move the statements
rather than moving them by hand. msm never does it on its own:

```text
msm.split_sections()                     # sections 140, 150 and 170
msm.split_sections(sections=["150"])     # only some of them
```

- Each statement moves, with the comments above it, into the file for its kind
  (table below), in its original order, and the section is left with a `SOURCE`
  directive per file. `DELIMITER` blocks are written again in each file.
- A section is **left as it is** and listed in `skipped` (with the reason) when
  it already includes a file, has nothing to move, or has a statement that fits
  no file *between* two that move. Running it twice changes nothing.
- Template sections the script lacks are added first (`sections_added`).
- A schema snapshot that matched the script before is made again
  (`snapshot_updated`); its positions changed with the move.
- It needs the `mariadb-lsp` binary: the language server splits the script.

### File naming convention

Name breakout files `<section-id>-<NN>_<topic>.sql` so they sort in load order
and map back to their section, e.g. `140-10_tables.sql`,
`140-30_inserts.sql`, `150-10_procedures_functions.sql`, `170_roles.sql`.
Split by object kind (the names `msm.split_sections` and the Workbench import
use):

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
- **Routines before views** in section 150: `CREATE VIEW` fails (error 1305)
  when it calls a function that does not exist yet, while routine, trigger and
  event bodies are not checked at `CREATE`. Hence `150-10_procedures_functions`
  comes before `150-20_views`. A view on another view must come after it.
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
