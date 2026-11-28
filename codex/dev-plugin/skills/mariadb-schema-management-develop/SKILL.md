---
name: mariadb-schema-management-develop
description: "Develop the next version of a MariaDB Schema Management (MSM) schema in development/<schema>_next.sql: add, change and drop tables, views, routines, triggers, events, sequences and REST endpoints with plain CREATE and DROP statements sent to msm.set_schema_statements (a changed CREATE TABLE becomes the ALTER TABLE of the next update script; renames keeps a renamed column's data), create and lay out schema diagrams, edit data and grants by section, and keep large sections in SOURCE-included files under development/sections/. Use when evolving an existing MSM schema, editing the _next.sql script, adding, renaming, changing or dropping tables, columns, keys or other schema objects, working on an MSM schema diagram, or splitting a growing script. Read mariadb-schema-management first for the section model."
---

# MSM — Developing the Next Version

After a release, `prepare_release` has already bumped the development version and
you continue editing `development/<schema>_next.sql` toward the next release.
This skill covers changing the schema and its REST endpoints with
`msm.set_schema_statements`, schema diagrams, editing the other
sections, and the **SOURCE breakout** files that keep the script maintainable. See
`mariadb-schema-management` for the section model. Assume MariaDB 11.8.

## Iterating on `_next.sql`

Change schema objects and REST endpoints with `msm.set_schema_statements`,
which places the statements itself: send a `CREATE` to add, replace or change
a table, sequence, view, routine, trigger, event or REST item, and a `DROP` to
remove one. Edit the rest by section, with `msm.get_section_sql_content` /
`msm.set_section_sql_content`:

- **Tables and sequences** → `msm.set_schema_statements` (it writes section
  140). Base data (`INSERT`s) → section 140 by hand.
- **Views, routines, triggers, events** → `msm.set_schema_statements` (it
  writes section 150 in the form that runs again). The target's section 150
  runs in full on every deployment, so upgraded schemas get them too.
- **Grants/roles** → section 170 (`CREATE ROLE IF NOT EXISTS`, then `GRANT`);
  it also runs on every deployment. Revoking a privilege additionally needs a
  `REVOKE` in the update script's section 270.
- **REST endpoints** → `msm.set_schema_statements` too, which writes section
  180 (see "REST endpoints in an MSM project").
- **Diagrams** → section 160 is written by msm only, through the diagram tools
  (see "Schema diagrams"); never edit it.

The development file always describes the **full, current** schema (not a diff) —
it is the source for the next version snapshot. The *migration* from the
previous version is kept separately: what `msm.set_schema_statements` changes
after the first release is kept for the next
update script, and the rest is written when you prepare the release (see
`mariadb-schema-management-release`).

Keep the development version in section 910 current with
`msm.set_development_version` as the target version firms up.

## Changing the schema: `msm.set_schema_statements`

Send plain SQL, one statement per list item: the `CREATE` of each object as it
should be, and a `DROP` for each object to remove. msm decides where each goes,
in what form, and what an upgrade needs:

```text
msm.set_schema_statements(
    statements=[
        "CREATE TABLE note (id UUID NOT NULL DEFAULT UUID_v7() PRIMARY KEY, headline VARCHAR(255) NOT NULL, body MEDIUMTEXT, author_id INT UNSIGNED NULL, CONSTRAINT fk_note_author FOREIGN KEY (author_id) REFERENCES author (id)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4",
        "CREATE TABLE author (id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY, name VARCHAR(100) NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4",
        "CREATE VIEW note_titles AS SELECT id, headline FROM note",
        "DROP VIEW old_note_list",
    ],
    renames={"note": {"title": "headline"}},     # note.title is now headline
    expect=[{"kind": "table", "name": "note"},   # optional guard
            {"kind": "table", "name": "author"},
            {"kind": "view", "name": "note_titles"},
            None],                               # None for a DROP
)
```

- One statement per list item, plain SQL, without `DELIMITER` lines: `CREATE`
  or `DROP` of a table, sequence, view, procedure, function, trigger or event,
  **named without its schema**, and `CREATE` or `DROP` of a REST service,
  schema, view, procedure or function (see "REST endpoints in an MSM
  project"). Schema objects and REST items can be mixed in one call.
- **Never `ALTER` or `RENAME`**: both are refused. To change a table, send its
  whole new `CREATE TABLE`.
- **A new object is added**: a table or sequence to section 140, the others to
  150 in the form that runs again.
- **A view, routine, trigger or event the project has is replaced** where it
  stands (no update-script statement: 150 runs in full on every deployment).
  An unchanged definition is left alone (`changed: false`).
- **A table the project has is changed to the definition given.** Its columns,
  keys, checks and options change where the script defines them, and once the
  project has a release, the `ALTER TABLE` a deployed server needs is kept for
  the next update script. This is the way to change a table: a hand edit of
  section 140 after a release changes the script but keeps no `ALTER`, so
  upgraded servers would never get the change.
  - **Send the complete definition**, every column, key, check and option, as
    a `CREATE TABLE`: what it leaves out is dropped. Read the table first with
    `msm.get_section_sql_content(file_path, "140")` (or its breakout file).
  - **Table options** (`ENGINE`, `DEFAULT CHARSET`, `COLLATE`, `COMMENT`, ...)
    must be given as the project has them: an option left out is removed.
    `AUTO_INCREMENT=n` is the exception; it is kept.
  - **Renaming a column**: name it in `renames={table: {old: new}}`, which
    keeps its data. Without it, the old column is dropped with its data and a
    new, empty one is added.
  - **A possible rename is refused.** When a dropped column and an added column
    are alike apart from the name, the call is refused and nothing is written.
    Send it again with `renames` when it is a rename, or with
    `dropped_columns={table: [column]}` when dropping the column and its data
    is meant. Ask the user when you can't tell.
- **A sequence the project has is refused.** Either send `DROP SEQUENCE s`
  in one call and its new `CREATE SEQUENCE` in the next (after a release
  the update script then drops and re-creates it, so deployed servers restart
  it from its `START`; the drop is refused while a table uses it), or, to keep
  its current value, change it by hand in section 140 and write an `ALTER
  SEQUENCE` into the update script at release time (see
  `mariadb-schema-management-release`).
- `expect` (`{kind, name, table?}` per statement, `table` for a trigger)
  refuses a statement that creates another object, before anything is written.
- All statements are one edit: everything is written, or nothing. A refusal
  names the statement ("Statement 2 ..."): fix that one and send them all
  again. The answer has `statements`, one entry per statement in order, each
  with its `action`: `added`, `replaced`, `unchanged`, `dropped`, or `skipped`
  (a `DROP ... IF EXISTS` of something the project lacks). It also has `files`
  (written), `migration` (the statements kept for the next update script),
  `migration_file` and `notes`. Check every note (`still-referenced`,
  `no-migration`, ...).
- `base_hash` is optional: leave it out. msm works on the project as it is, and
  makes the schema snapshot again first when the script was edited by hand.
- It needs a current `mariadb-lsp` (it refuses an older one, saying to update
  it or the MariaDB Shell).

### Dropping an object

Send its `DROP` to `msm.set_schema_statements`: `DROP TABLE t`, `DROP VIEW v`,
`DROP PROCEDURE p`, `DROP FUNCTION f`, `DROP TRIGGER tr`, `DROP EVENT e`,
`DROP SEQUENCE s`. `DROP TABLE t, u` drops both, and `IF EXISTS` skips one the
project lacks (its action is `skipped`) instead of refusing the call. msm
removes the object's statements from `_next.sql` and the breakout files; after
the first release its `DROP` is kept for the next update script automatically.
A `DROP` is refused for an object another one needs (a table a foreign key
references, a sequence a table uses, a trigger another one `FOLLOWS` or
`PRECEDES`): drop or change that one first.

### What the kept migration covers

After the first release, the migration statements of each call are kept in
the pending update script `development/<schema>_update_next.sql`, each under a
`-- msm.editSchema: ...` comment: table changes and the `DROP`s of tables,
sequences, views, triggers and events for section 240, routine `DROP`s for
260. A new or replaced view, routine, trigger or event needs none, since 150
creates it. The next `prepare_release` moves them into the new update script
(see `mariadb-schema-management-release`).

They take the schema along, not its data: a `NOT NULL` column added to a table
with rows gets the type's default (`0` for a number), not a valid reference,
so a backfill has to run before a foreign key on it. Changes you make by hand
(base data, a changed sequence, an edit of section 140) are not kept: their
migration is still yours to write at release time.

## REST endpoints in an MSM project

An MSM project's REST endpoints live in its section 180, which every
deployment runs in full. When the user wants endpoints in the project, put
them there with `msm.set_schema_statements`, not by running them on a server
(the project would not know them, and the next deployment would not create
them) and not with `msm.set_section_sql_content`. Running REST statements on
a server directly, when the user asks for that, is still fine; it only leaves
the project out. For the REST DDL itself (the
`CREATE REST VIEW` field mapping, options, `@` flags) read
`mariadb-rest-service-create`.

### Adding endpoints, step by step

1. **Make sure the objects exist in the project.** A `CREATE REST VIEW`,
   `PROCEDURE` or `FUNCTION` exposes a table, view or routine of this schema,
   so add those first (`msm.set_schema_statements`).
2. **Write the service, its schema and its objects** in one call, parents
   first. Every statement names its place, as a statement of its own (one
   relying on `USE REST ...` is refused): a schema `ON SERVICE /svc`, an
   object `ON SERVICE /svc SCHEMA /p` (one combined clause). Write the
   database schema's name as the project's schema. Give options such as
   `PUBLISHED` or `ADD AUTH APP "name"` in the `CREATE` itself, as an `ALTER`
   is refused:

   ```text
   msm.set_schema_statements(
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
3. **Change or rename** an endpoint by sending its new `CREATE` the same way;
   `replaces={"kind": "object", "service": ..., "schema": ..., "object":
   ...}` renames a REST object (not a service or schema).
4. **Remove** one by sending its `DROP`, naming its place the same way:

   ```text
   msm.set_schema_statements(
       statements=[
           'DROP REST VIEW /products FROM SERVICE /shop SCHEMA /v1',
           'DROP REST SCHEMA /v0 FROM SERVICE /shop',
       ],
   )
   ```

   (`DROP REST SERVICE /shop` drops a whole service.) The item's statements
   and everything on it go from section 180, so dropping the outermost item
   is enough.
   No `DROP` is written into the project: the next `msm.prepare_release`
   writes it into the update script's section 280.
5. **Show the endpoints on the diagram** (unless the user doesn't want a
   diagram): read the diagram with `msm.get_schema_diagrams(diagram=)`, add
   one `RestObjectFigure` per REST object (`restService`, `restSchema`,
   `restObject` exactly as section 180 writes them, and a `left`/`top` clear of
   the other figures, as the layout never places or moves them) and send the
   whole document back with `msm.set_schema_diagram`. Then end with the review
   link (see "Handing the project back" in `mariadb-schema-management`).

msm checks that nothing but the given items changed, writes everything or
nothing, and makes the snapshot again. `base_hash` is optional; leave
it out. Paths are compared as the server does:
case and quotes ignored, `anna, mike@/svc` the same as `mike,anna@/svc`.

### What stays outside section 180

For REST, `msm.set_schema_statements` takes only services, schemas and their
views, procedures and functions, and section 280 can only remove those and
auth app links. Keep the rest on the server, not in the project:

- `CONFIGURE REST METADATA`: once per server, before the first deployment
  that has REST endpoints. The deployment account needs its REST role active.
- Auth apps, REST users and REST roles (`mariadb-rest-service-authorization`):
  create them on each server. The project only links an app by name (`ADD AUTH
  APP` in `CREATE REST SERVICE`), so the app must exist on the server before
  the deployment.
- Content sets.

## What an agent can't do in a project

The MCP server serves some msm tools to the MariaDB VS Code extension only, so
an agent doesn't have them: the project settings (`msm.project.json`), renaming
the schema, splitting sections, structured edits, object templates, online
`ALTER TABLE`, and diagram pictures. When the user asks to change a project
setting or rename the schema, say that it is done in the MariaDB extension and
give the review link (see "Handing the project back" in
`mariadb-schema-management`). Never edit `msm.project.json` or section 160 by
hand, and don't run `mariadb-shell -- msm ...` from a shell instead: the
command line skips the check on which projects the user lets LLMs work on.

## Schema diagrams

Make and change the diagrams of section 160 through the tools, never in the SQL:

| Task | Tool |
| --- | --- |
| New diagram | `msm.create_schema_diagram(diagram, tables=, views=, sequences=, routines=, events=)`: all tables by default, laid out; the other objects only when named |
| Add objects, tidy up | `msm.layout_schema_diagram(diagram, tables=, views=, sequences=, routines=, events=, keep_placed=True)`: places the figures without a position; `keep_placed=False` lays all out again |
| Read | `msm.list_schema_diagrams`, `msm.get_schema_diagrams(diagram=)` (an image figure's picture is left out) |
| Change by hand | `msm.set_schema_diagram(document)`: an `msm-diagram/1` document; figure types `TableFigure` (its card lists the table's triggers unless `triggersExpanded` is false), `ViewFigure`, `SequenceFigure`, `RoutineGroupFigure` (`routines`), `EventGroupFigure` (`events`), `RestObjectFigure` (`restService`, `restSchema`, `restObject`: the paths as section 180 writes them), `NoteFigure`, `ImageFigure`; a figure without `left`/`top` is placed by the layout; an `ImageFigure` sent without its picture keeps the stored one |
| Rename | `msm.rename_schema_diagram(diagram, new_name)`: refused for a name another diagram has, compared case-insensitively |
| Remove | `msm.remove_schema_diagram(diagram)` |

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
`msm.layout_schema_diagram(diagram, tables=, views=, ...)`, which places them and
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
nearly always exceeds it), and the live-schema import for every large section.

To break a section out, write each breakout file (copyright header, then the
statements in the section's form), then replace the section body with its
`SOURCE ...[lnN:]` lines through `msm.set_section_sql_content`. Move each
statement with the comments above it, and keep the order the statements had.
`msm.set_schema_statements` edits the breakout files as well, so a broken-out
section stays editable through it.

### File naming convention

Name breakout files `<section-id>-<NN>_<topic>.sql` so they sort in load order
and map back to their section, e.g. `140-10_tables.sql`,
`140-30_inserts.sql`, `150-10_procedures_functions.sql`, `170_roles.sql`.
Split by object kind (the names msm's own splitting and the live-schema import
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
- `mariadb-schema-management-release` — snapshot the version and write the migration (including what `msm.set_schema_statements` kept).
- `mariadb-alter-table`, `mariadb-create-view`, `mariadb-create-procedure` — the DDL you edit here.
