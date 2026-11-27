---
name: mariadb-laravel-vector
description: "MariaDB Vector in a Laravel (PHP) application: vector columns, VECTOR INDEX, the AsVector Eloquent cast and similarity search with the query builder. Use when building semantic search, RAG or embedding storage on MariaDB with Laravel or Eloquent."
---

# MariaDB Vector with Laravel

Requires **MariaDB 11.7+** (11.8 LTS recommended) and **Laravel 13**, on the `mariadb`
driver — see `mariadb-laravel-connector`. Vector support is native to the framework:
no Composer package is needed to store or query vectors.

## Migration

```php
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

Schema::create('documents', function (Blueprint $table) {
    $table->id();
    $table->string('title');
    $table->text('content');
    $table->vector('embedding', 1536);
    $table->timestamps();

    $table->vectorIndex('embedding');
});
```

`vector('embedding', 1536)` emits `vector(1536) not null`. `vectorIndex('embedding')`
emits:

```sql
alter table `documents` add vector index `documents_embedding_vectorindex` (`embedding`) M=6 DISTANCE=cosine
```

`$table->vector('embedding', 1536)->index()` is equivalent — on a vector column, the
fluent `index()` is routed to `vectorIndex()`.

To drop it, pass the index name, not the column:

```php
$table->dropVectorIndex('documents_embedding_vectorindex');
```

### Never call `Schema::ensureVectorExtensionExists()` on MariaDB

That helper exists for PostgreSQL's `pgvector` extension and throws on any other
connection:

```
RuntimeException: Extensions are only supported by Postgres.
```

MariaDB needs no extension — `VECTOR` is a built-in column type. Migrations that must run
on both engines should guard it:

```php
if (DB::connection() instanceof Illuminate\Database\PostgresConnection) {
    Schema::ensureVectorExtensionExists();
}
```

### Index constraints to respect

- The indexed column must be `NOT NULL`. Laravel's `vector()` is `NOT NULL` by default —
  do not add `->nullable()` on a column you intend to index.
- **One vector index per table.** Two indexed vector columns on the same table are rejected
  by the server.
- `M` (graph degree, 3–200, default 6) and `DISTANCE` (`cosine` or `euclidean`) are fixed at
  creation time. Changing them means dropping and recreating the index.
- The index is only used when the query's distance function matches the index's `DISTANCE`.
  An index created with `DISTANCE=cosine` does nothing for a `VEC_DISTANCE_EUCLIDEAN` query —
  the server falls back to a full scan and still returns correct rows, just slowly.

## Eloquent cast

```php
use Illuminate\Database\Eloquent\Casts\AsVector;

class Document extends Model
{
    protected function casts(): array
    {
        return ['embedding' => AsVector::class];
    }
}
```

Assign a plain PHP array of floats; the cast writes `vec_fromtext('[...]')` and reads back
MariaDB's little-endian float32 bytes as an array of floats. Never write the raw binary or a
JSON string to the column yourself.

```php
Document::create([
    'title' => 'Napa Valley',
    'content' => $content,
    'embedding' => $embedding,   // array<int, float>, exactly as many values as the column's dimensions
]);
```

A dimension mismatch is rejected by the server at insert time.

## Querying

```php
$documents = Document::query()
    ->whereVectorSimilarTo('embedding', $queryEmbedding, minSimilarity: 0.6)
    ->limit(10)
    ->get();
```

`whereVectorSimilarTo` filters on **cosine similarity** (`0.0`–`1.0`, `1.0` identical) and
orders by similarity. It is a wrapper: similarity `s` becomes `vec_distance_cosine(...) <= 1 - s`.

Lower-level methods, when the threshold and the ordering must be controlled separately:

```php
Document::query()
    ->select('*')
    ->selectVectorDistance('embedding', $queryEmbedding, as: 'distance')
    ->whereVectorDistanceLessThan('embedding', $queryEmbedding, maxDistance: 0.3)
    ->orderByVectorDistance('embedding', $queryEmbedding)
    ->limit(10)
    ->get();
```

All four compile to `vec_distance_cosine(<column>, vec_fromtext(?))` on MariaDB (see
[Query vector sent as text](#query-vector-sent-as-text-mdev-42201) for its cost).

### Passing a string instead of a vector

Every one of these methods also accepts a plain string, which is embedded on the fly:

```php
Document::query()
    ->whereVectorSimilarTo('embedding', 'best wineries in Napa Valley')
    ->limit(10)
    ->get();
```

This calls `Str::of($query)->toEmbeddings(cache: true)`, a macro provided by the
**`laravel/ai`** package. Without that package installed and an embeddings provider
configured, pass an array of floats instead.

### Filtering vector searches

The optimizer does not yet choose by cost between the vector index and other indexes
([MDEV-33412](https://jira.mariadb.org/browse/MDEV-33412), open). Measured on 50,000
passages, 768 dims, one laptop ([benchmarks](https://github.com/Rhaima96/laravel-mariadb-vector#benchmarks)),
`WHERE tenant_id = ? ORDER BY distance LIMIT 10`:

- **No normal index on `tenant_id`:** the vector index was used even for a filter keeping 0.1%
  of rows — 3.7 to 4.8 s per query, 70 to 76% recall, sometimes fewer than 10 rows. The same
  query with `IGNORE INDEX` on the vector index: about 22 ms, exact.
- **BTREE index on `tenant_id`:** the optimizer switched to it for selective filters (0.5 to
  1.6 ms, exact). The switch happened between 10% and 1% of rows kept. One exception: a filter
  keeping about 3% of rows still used the vector index (19 ms, 96.6% recall, against 4.2 ms and
  exact with the BTREE).

So: add a normal index on every column used to filter vector searches (tenant, category,
language), check `EXPLAIN` with a realistic filter value, and use `ignoreIndex()` on the vector
index when a filter is known to be very selective.

```php
$table->index('tenant_id');   // migration: normal index on the filter column

Document::query()
    // ->ignoreIndex('documents_embedding_vectorindex')   // very selective filter: exact scan
    ->where('tenant_id', $tenantId)
    ->orderByVectorDistance('embedding', $queryEmbedding)
    ->limit(10)
    ->get();
```

### Query vector sent as text (MDEV-42201)

MariaDB converts a constant `VEC_FromText('[...]')` again **for every row** when it is in the
SELECT list or in `ORDER BY`, and only once in `WHERE`
([MDEV-42201](https://jira.mariadb.org/browse/MDEV-42201): confirmed, not fixed yet as of
26 Nov 2026). Laravel sends every query vector this way. Same rows returned, but on 768 dims,
one laptop ([benchmarks](https://github.com/Rhaima96/laravel-mariadb-vector#benchmarks)):
exact search without vector index took about 950 ms instead of 24 ms on 20,000 rows, and
2,725 ms instead of 58 ms on 50,000 rows; with an `M=16` vector index, 2.6 ms instead of 0.7 ms.

It matters most without a vector index, on small tables searched exactly, and with filters that
fall back to a scan. Two workarounds:

```php
// 1. Convert once into a user variable, then use it on the SAME connection.
DB::statement('SET @q = VEC_FromText(?)', [json_encode($queryEmbedding)]);
$docs = Document::query()->orderByRaw('vec_distance_cosine(embedding, @q)')->limit(10)->get();

// 2. Send float32 little-endian bytes as a hex literal, built from floats only.
$hex = bin2hex(pack('g*', ...array_map('floatval', $queryEmbedding)));
$docs = Document::query()->orderByRaw("vec_distance_cosine(embedding, x'{$hex}')")->limit(10)->get();
```

With read/write connections, `DB::statement()` runs on the write connection and the select on
a read one, so `@q` is not set there: add `->useWritePdo()` to the query, or use the hex
literal. The `rhaima96/laravel-vector-metrics` package (v0.2.0+) sends the vector as a binary
literal on MariaDB in its `orderByVectorDistanceUsing()` and `whereVectorDistanceUsing()` macros.

## Pitfalls

- **Cosine only in the framework.** `compileVectorDistanceExpression()` always emits
  `vec_distance_cosine`. For `VEC_DISTANCE_EUCLIDEAN`, use `whereRaw()`/`selectRaw()` with a
  matching `DISTANCE=euclidean` index, or a community package that adds the metric
  (e.g. `rhaima96/laravel-vector-metrics`).
- **Normalize consistently.** Cosine distance ignores magnitude, but mixing embeddings from
  different models or versions in one column makes distances meaningless. Store the model
  name alongside the vector and re-embed the whole table when it changes.
- **`M=6` costs recall.** `vectorIndex()` always writes `M=6`, MariaDB's default. On 50,000
  passages, 768 dims, one laptop ([benchmarks](https://github.com/Rhaima96/laravel-mariadb-vector#benchmarks)),
  at the default `mhnsw_ef_search` (20), recall@10 was 82 to 86% with `M=6` and 99 to 100%
  with `M=16`, both at about 2 to 3 ms per query. The `M=16` index took 3 to 4 times longer to
  build (38 s against 9 to 10 s for 50,000 rows). Create it with a raw statement, or with the
  `vectorIndexUsing()` macro of `rhaima96/laravel-vector-metrics`:

```php
DB::statement('alter table documents add vector index documents_embedding_vectorindex (embedding) M=16 DISTANCE=cosine');

// or, inside Schema::table() / Schema::create():
$table->vectorIndexUsing('embedding', 'cosine', m: 16);
```

  To raise recall without rebuilding, raise the search effort on the session with
  `DB::statement('SET SESSION mhnsw_ef_search = 100')` (`M=6` with 500 gave 96 to 98% on the
  same data, at a higher query time).

- **Load first, index second.** Inserting 50,000 rows into a table that already had the vector
  index took 87 s (`M=16`) / 30 s (`M=6`). A plain load followed by `ALTER TABLE ... ADD VECTOR
  INDEX` took 5.9 + 38 = 44 s / 6.3 + 9.3 = 16 s (same benchmark). For a large import or a
  re-embedding, drop the index, load, then create it again.
- **Check the index is actually used** before blaming the server:

```sql
EXPLAIN SELECT id FROM documents
ORDER BY VEC_DISTANCE_COSINE(embedding, VEC_FROMTEXT('[...]')) LIMIT 10;
```

A `LIMIT` and an `ORDER BY` on the matching distance function are what let the optimizer pick
the vector index.

## Related skills

- `mariadb-laravel-connector` — driver and version setup.
- `mariadb-vector` / `mariadb-vector-functions` — the server-side reference.
