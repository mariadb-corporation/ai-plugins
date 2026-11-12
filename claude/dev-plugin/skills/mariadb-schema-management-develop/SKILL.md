---
name: mariadb-schema-management-develop
description: "Develop the next version of a MariaDB Schema Management (MSM) schema in development/<schema>_next.sql: by section, or with msm.set_schema_statements / msm.drop_schema_object / msm.edit_schema, which add, replace, change and drop tables, columns, keys, views and routines in the SQL and keep the migration for the next update script; REST endpoints with msm.set_rest_statements / msm.drop_rest_object; rename the schema before its first release; create and lay out schema diagrams; and split large sections into SOURCE-included files under development/sections/ with msm.split_sections. Use when evolving an existing MSM schema, editing the _next.sql script, adding, renaming or changing schema objects, working on an MSM schema diagram, or splitting a growing script. Read mariadb-schema-management first for the section model."
---

# MSM — Developing the Next Version

After a release, `prepare_release` has already bumped the development version and
you continue editing `development/<schema>_next.sql` toward the next release.
This skill covers iterating on that script, schema edits with `msm.edit_schema`,
schema diagrams, and the **SOURCE breakout** files that keep the script
maintainable. See `mariadb-schema-management` for the section
model. Assume MariaDB 11.8.

## Iterating on `_next.sql`

Prefer the tools that place statements themselves: `msm.set_schema_statements`
and `msm.drop_schema_object` for objects from SQL, `msm.edit_schema` for
structured changes, `msm.set_rest_statements` / `msm.drop_rest_object` for
section 180. Otherwise make changes in the same sections you authored
initially, using `msm.set_section_sql_content` /
`msm.get_sql_content_from_section`:

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
| `add_view`, `replace_view` | `view`: `name`, `definition` (the `SELECT` alone) |
| `drop_view` | `view` |
| `add_routine`, `replace_routine` | `routine`: `name`, `kind`, `parameters`, `returns` (a function), `body` |
| `add_trigger`, `replace_trigger` | `trigger`: `name`, `timing` (`BEFORE`, `AFTER`), `events` (`INSERT`, ...), `table`, `body` |
| `rename_trigger`, `drop_trigger` | `trigger`, `new_name` (rename) |
| `add_event`, `replace_event` | `event`: `name`, `schedule` (`EVERY 1 DAY`, ...), `body` |
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

### Adding and replacing objects from SQL: `msm.set_schema_statements`

When you have the CREATE statement, let msm decide where it goes and in what
form:

```text
msm.set_schema_statements(
    base_hash="<source_hash>",
    statements=[
        "CREATE TABLE author (id INT UNSIGNED NOT NULL PRIMARY KEY, name VARCHAR(100) NOT NULL)",
        "CREATE VIEW note_titles AS SELECT id, title FROM note",
    ],
    expect=[{"kind": "table", "name": "author"},
            {"kind": "view", "name": "note_titles"}],   # optional guard
)
```

- One CREATE per statement, of a table, sequence, view, procedure, function,
  trigger or event, **named without its schema**, without `DELIMITER`.
- A new object is added: a table or sequence to section 140, the others to 150
  in the form that runs again.
- A view, routine, trigger or event the project has is **replaced where it
  stands** (no update-script statement: 150 runs in full on every
  deployment). An unchanged definition is left alone (`changed: false`).
- A table or sequence the project has is refused: change it with
  `msm.edit_schema`, which writes the `ALTER`s a deployed server needs.
- `expect` (`{kind, name, table?}` per statement) refuses a statement that
  creates another object, before anything is written.
- All statements are one edit, with `msm.edit_schema`'s answer plus
  `statements: [{kind, name, file, line, replaced, changed}]`.
- It needs a current `mariadb-lsp` (it refuses an older one, saying to update
  it or the MariaDB Shell).

`msm.get_object_templates` gives msm's plain CREATE templates for a view,
procedure, function, trigger, event and sequence (placeholders `${name}`,
`${schema}`, and `${table}` for a trigger); fill them and send them here.

`msm.drop_schema_object(kind, name, base_hash)` removes a table, sequence,
view, procedure, function, trigger or event (through `msm.edit_schema`'s drop
ops, so after the first release the DROP is kept for the next update script).
It is refused for an object another one needs.

## REST endpoints in an MSM project

An MSM project's REST endpoints live in its section 180, which every
deployment runs in full. When the user wants endpoints in the project, put
them there with `msm.set_rest_statements`, not by running them on a server
(the project would not know them, and the next deployment would not create
them) and not with `msm.set_section_sql_content`. Running REST statements on
a server directly, when the user asks for that, is still fine; it only leaves
the project out. For the REST DDL itself (the
`CREATE REST VIEW` field mapping, options, `@` flags) read
`mariadb-rest-service-create`.

### Adding endpoints, step by step

1. **Get the base hash.** `msm.get_schema_diagrams()`: the
   `schema_definition` row's `source_hash`. Each REST call answers with the
   next one (the first of its `rows`).
2. **Make sure the objects exist in the project.** A `CREATE REST VIEW`,
   `PROCEDURE` or `FUNCTION` exposes a table, view or routine of this schema,
   so add those first (`msm.set_schema_statements`).
3. **Write the service, its schema and its objects** in one call, parents
   first. Every statement names its place, as a statement of its own (no `USE
   REST ...`): a schema `ON SERVICE /svc`, an object `ON SERVICE /svc SCHEMA
   /p` (one combined clause). Write the database schema's name as the
   project's schema. Give options such as `PUBLISHED` or `ADD AUTH APP "name"`
   in the `CREATE` itself, as an `ALTER` can't be passed:

   ```text
   msm.set_rest_statements(
       base_hash="<source_hash>",
       statements=[
           'CREATE REST SERVICE /shop PUBLISHED COMMENT "Shop API"',
           'CREATE REST SCHEMA /v1 ON SERVICE /shop FROM `shop` COMMENT "Version 1"',
           'CREATE REST VIEW /products ON SERVICE /shop SCHEMA /v1 AS `shop`.`product` { id: id @KEY @SORTABLE, name: name, price: price } AUTHENTICATION NOT REQUIRED COMMENT "Product catalog"',
       ],
   )
   ```

   msm writes each as `CREATE OR REPLACE` (`IF NOT EXISTS` is refused) and
   places it: an item section 180 already creates is replaced where it stands
   (its other statements go, except `ALTER`s that only link or unlink auth
   apps; an `ALTER` that links an app and changes more is refused); a new
   item goes after its service's or schema's statements. Backtick a name that
   is a keyword, such as a `CLASS` name. The answer has `statements: [{kind,
   service, schema, object, file, line, replaced}]` and `notes` to check.
4. **Change or rename** an endpoint by sending its new `CREATE` the same way;
   `replaces={"kind": "object", "service": ..., "schema": ..., "object":
   ...}` renames a REST object (not a service or schema).
5. **Remove** one with `msm.drop_rest_object(kind, service, base_hash,
   schema=None, object=None)` (`kind`: `service`, `schema` or `object`): its
   statements and everything on it go. It writes no DROP: the next
   `msm.prepare_release` writes it into the update script's section 280.
6. **Show the endpoints on the diagram** (unless the user doesn't want a
   diagram): read the diagram with `msm.get_schema_diagrams(diagram=)`, add
   one `RestObjectFigure` per REST object (`restService`, `restSchema`,
   `restObject` exactly as section 180 writes them, and a `left`/`top` clear of
   the other figures, as the layout never places or moves them) and send the
   whole document back with `msm.set_schema_diagram`. Then end with the review
   link (see "Handing the project back" in `mariadb-schema-management`).

Both tools check that nothing but the given items changed, write everything or
nothing, and make the snapshot again. Paths are compared as the server does:
case and quotes ignored, `anna, mike@/svc` the same as `mike,anna@/svc`.

### What stays outside section 180

`msm.set_rest_statements` takes only services, schemas and their views,
procedures and functions, and section 280 can only remove those and auth app
links. Keep the rest on the server, not in the project:

- `CONFIGURE REST METADATA`: once per server, before the first deployment
  that has REST endpoints. The deployment account needs its REST role active.
- Auth apps, REST users and REST roles (`mariadb-rest-service-authorization`):
  create them on each server. The project only links an app by name (`ADD AUTH
  APP` in `CREATE REST SERVICE`), so the app must exist on the server before
  the deployment.
- Content sets.

## Renaming the schema: `msm.rename_schema`

`msm.rename_schema(new_schema_name, dry_run=False)` renames the schema of a
project **that has no release yet**. Everything that names it follows, all or
nothing: `msm.project.json`, the development file names, `USE`, `CREATE
SCHEMA`, every schema qualifier and banner in the SQL and its breakout files,
the pending update script, the template's README/CHANGELOG lines, the
snapshot, the project folder where it still has msm's name for the schema,
and the project lists. Call it with `dry_run=True` first: it answers
`allowed` and a `reason` (`released`, `invalid-name`, `same-name`,
`folder-exists`, `lsp-missing`, `restricted`) without changing anything. Show
the user the `warnings` (the schema name inside strings, projects whose
`schemaDependencies` name the old schema). After a rename,
`project_path` is the project's new folder; use it in the review link.

## Schema diagrams

Make and change the diagrams of section 160 through the tools, never in the SQL:

| Task | Tool |
| --- | --- |
| New diagram | `msm.create_schema_diagram(name, tables=, views=, sequences=, routines=, events=)`: all tables by default, laid out; the other objects only when named |
| Add objects, tidy up | `msm.layout_schema_diagram(name, tables=, views=, sequences=, routines=, events=, keep_placed=True)`: places the figures without a position; `keep_placed=False` lays all out again |
| Read | `msm.list_schema_diagrams`, `msm.get_schema_diagrams(diagram=)`; `msm.get_schema_diagram_image` for a picture they leave out |
| Change by hand | `msm.set_schema_diagram(document)`: an `msm-diagram/1` document; figure types `TableFigure` (its card lists the table's triggers unless `triggersExpanded` is false), `ViewFigure`, `SequenceFigure`, `RoutineGroupFigure` (`routines`), `EventGroupFigure` (`events`), `RestObjectFigure` (`restService`, `restSchema`, `restObject`: the paths as section 180 writes them), `NoteFigure`, `ImageFigure`; a figure without `left`/`top` is placed by the layout; an `ImageFigure` sent without its picture keeps the stored one |
| Rename | `msm.rename_schema_diagram(name, new_name)`: refused for a name another diagram has, compared case-insensitively |
| Remove | `msm.remove_schema_diagram(name)` |

- **REST object figures** are added only with `msm.set_schema_diagram` (see
  "REST endpoints in an MSM project", step 6). The layout never places or moves
  them, and they are dropped once section 180 no longer creates their object.
- **`upright`:** any card figure may have `upright`. When `true`, the card
  stands on the page and covers `width` × `depth` (`depth` 20 by default);
  `height` is how high it stands. When `false`, it lies flat and covers
  `width` × `height`. Without the key, a REST object figure stands and every
  other figure lies flat.
- **Connections** follow the foreign keys' definitions, not just their names. A
  key that is dropped and added again under a new name keeps its line and that
  line's settings. A line is dropped only when no key between its two tables
  is left. Lines go from the child table (the start figure) to the parent.

**Keep the diagrams current.** When you add tables, views, sequences, routines
or events, add them to the project's diagram with
`msm.layout_schema_diagram(name, tables=, views=, ...)`, which places them and
runs the automatic layout on them. A project without a diagram gets one as in
`mariadb-schema-management-create`, step 4, unless the user doesn't want one.
Then end the answer with a review link to each diagram you created or changed,
or, when no diagram was created or changed, one link to the project alone
(see "Handing the project back" in `mariadb-schema-management`).

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
