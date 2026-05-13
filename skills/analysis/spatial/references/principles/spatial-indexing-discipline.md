# Principle: Spatial Indexing Discipline

A spatial column without a spatial index is a full-table-scan trap. Every spatial query against it is O(n×m) where naïve. The fix is universal: spatial columns get spatial indexes, always.

## The principle

Every engine has a spatial index family. The names differ; the function is the same: pre-compute bounding-box hierarchies so queries can prune the search space before testing exact predicates.

| Engine | Spatial index family |
|---|---|
| **PostGIS** | GIST (default), SP-GIST (point-heavy uniform), BRIN (spatially-clustered ingest order) |
| **GeoPandas / Shapely** | STRtree (R-tree) — built lazily on `gdf.sindex` access |
| **Sedona** | KDB-tree (default for spatial joins), quad-tree (alternative) |
| **DuckDB-spatial** | R-tree (built implicitly on join, or explicitly via `CREATE INDEX ... USING RTREE`) |

The discipline: **whenever you create or load a spatial column you'll filter or join on, build the spatial index in the same operation.**

## Per-engine implementation

### PostGIS

```sql
-- Always create
CREATE INDEX features_geom_idx ON features USING GIST (geom);

-- Verify usage
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM features WHERE ST_Within(geom, ...);
-- Look for "Bitmap Index Scan on features_geom_idx"

-- For partitioned tables, index every partition
CREATE INDEX ON donations_2024 USING GIST (geom);

-- After bulk loads, ANALYZE for planner stats
VACUUM (ANALYZE) features;
```

GIST is the default and works for all geometry types. SP-GIST and BRIN are situational (see [`coding/postgis/references/indexing-strategies.md`](../../../coding/postgis/references/indexing-strategies.md)).

### GeoPandas

The STRtree is built lazily — first access to `.sindex` builds; subsequent accesses reuse:

```python
counties.sindex  # eager build (optional but explicit)

# Subsequent operations reuse
joined1 = gpd.sjoin(points_today, counties, predicate="within")
joined2 = gpd.sjoin(points_yesterday, counties, predicate="within")
```

For frames you'll join against repeatedly, build eagerly so the latency hit is predictable. For one-off operations, lazy build is fine.

### Sedona

Spatial join optimizer auto-builds the spatial partitioning (KDB-tree by default). Explicit configuration:

```python
sedona.conf.set("spark.sedona.join.gridtype", "kdbtree")  # or "quadtree"
sedona.conf.set("spark.sedona.global.partitionnum", "200")
```

For broadcast spatial joins (small right side), Sedona builds an in-memory STRtree on the broadcast side automatically. See [`coding/sedona/references/partitioning-strategies.md`](../../../coding/sedona/references/partitioning-strategies.md).

### DuckDB-spatial

Implicit R-tree on join:

```sql
-- DuckDB builds an in-memory R-tree when it sees ST_Within in a join condition
SELECT * FROM points p JOIN counties c ON ST_Within(p.geom, c.geom);
```

Explicit, persistent index for repeated queries:

```sql
CREATE INDEX counties_geom_idx ON counties USING RTREE (geom);
```

## What "the index is being used" looks like

PostGIS:
```
Bitmap Heap Scan on features
  Recheck Cond: (geom && bbox)
  Filter: ST_Within(geom, bbox)
  ->  Bitmap Index Scan on features_geom_idx
        Index Cond: (geom && bbox)
```

GeoPandas: `gpd.sjoin` always uses `.sindex`; if performance is bad, the index isn't the issue (likely CRS mismatch, predicate confusion, or right-side too small).

Sedona: `result.explain()` shows `RangeJoin` or `BroadcastIndexJoin`. `CartesianProduct` means no index.

DuckDB: `EXPLAIN ANALYZE` shows `RTREE_INDEX_JOIN` or `RANGE_JOIN`. `NESTED_LOOP_JOIN` means no index.

## Index creation timing

The two main patterns:

### Bulk load → index after

For large initial loads, drop indexes (or load into an unindexed staging table), then create:

```sql
-- Stage 1: load
CREATE UNLOGGED TABLE features_staging (...);
\COPY features_staging FROM 'data.csv' WITH CSV HEADER;

-- Stage 2: validate, transform
UPDATE features_staging SET geom = ST_MakeValid(geom) WHERE NOT ST_IsValid(geom);

-- Stage 3: promote
INSERT INTO features SELECT * FROM features_staging;

-- Stage 4: index
CREATE INDEX features_geom_idx ON features USING GIST (geom);
ANALYZE features;
```

Per-row index updates during bulk insert are catastrophic; load first, index after.

### Continuous insert → index always present

For tables receiving continuous writes (live data ingestion), keep the index. The per-insert cost is acceptable; the alternative is "queries are slow, ad-hoc rebuild, repeat" indefinitely.

## Index health

Indexes bloat over time, especially under update/delete workloads. Monitor:

```sql
SELECT
    schemaname || '.' || relname AS table,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
    pg_size_pretty(pg_relation_size(relid)) AS table_size
FROM pg_stat_user_indexes
WHERE indexrelname LIKE '%geom%'
ORDER BY pg_relation_size(indexrelid) DESC;
```

A GIST index larger than the table itself is bloated. `REINDEX CONCURRENTLY`.

For Sedona / DuckDB, indexes are in-memory and rebuilt per session; bloat doesn't accumulate. For GeoPandas STRtree, the index is also per-session and rebuilt on `.sindex` access.

PostGIS-specific deep dive: [`coding/postgis/references/vacuuming-and-bloat.md`](../../../coding/postgis/references/vacuuming-and-bloat.md).

## When the index doesn't help

Cases where adding a spatial index doesn't speed things up:

- **Tiny right side (< 1000 rows)** — sequential scan is faster than building/using the index
- **Predicate that can't use the index** (`ST_Distance < d`, `ST_Equals`, custom UDFs) — index can't help; rewrite the predicate
- **Function on the indexed column** (`ST_Transform(geom, ...)`) — blocks the index; materialize a transformed column
- **Cross-CRS comparisons** — forces implicit reprojection per row, blocks index
- **Highly selective non-spatial predicate** that already narrows to few rows — spatial index overhead exceeds benefit

For each of these, the fix is upstream of the index (rewrite predicate, materialize column, etc.).

## Functional indexes (and why they're usually a smell)

Tempting:

```sql
-- Index on transformed geometry
CREATE INDEX bad_idx ON features USING GIST (ST_Transform(geom, 5070));
```

Doesn't work. The optimizer can use this index *only* when the query has the exact same expression. `WHERE ST_Within(ST_Transform(geom, 5070), ...)` works; `WHERE ST_Within(geom, ...)` doesn't.

Better: materialize the transformed geometry as a column, index that column.

```sql
ALTER TABLE features ADD COLUMN geom_5070 geometry(Geometry, 5070);
UPDATE features SET geom_5070 = ST_Transform(geom, 5070);
CREATE INDEX features_geom_5070_idx ON features USING GIST (geom_5070);
```

Trade storage for query speed. Almost always worth it for hot queries.

## Compound indexes — spatial + attribute

Real workloads filter on more than geometry:

```sql
SELECT * FROM features WHERE state = 'TX' AND ST_Within(geom, bbox);
```

Two indexes work:

```sql
CREATE INDEX features_state_idx ON features (state);
CREATE INDEX features_geom_idx ON features USING GIST (geom);
```

The planner picks the more selective. Sometimes a partial spatial index is the right answer:

```sql
CREATE INDEX features_geom_tx_idx ON features USING GIST (geom)
WHERE state = 'TX';
```

PostGIS-specific. For Sedona / GeoPandas / DuckDB, partial indexes don't exist; partition or filter manually.

## Pitfalls

- **No index on the spatial column** — every query is a sequential scan.
- **Index on a column that's never used in WHERE/JOIN** — wasted storage and write overhead.
- **Functional index without exact-expression query match** — index never used.
- **Forgot `ANALYZE` after bulk load** — planner uses default 1000-row estimates; bad plans.
- **Index bloat** unmonitored — queries get slower over months without an obvious cause. Check periodically.
- **`ST_Transform` in the indexed query** — blocks the index. Materialize the projected geometry.
- **Compound condition where attribute filter is more selective** — spatial index is correct but not the best plan; check both work.
- **Tiny tables** — index overhead exceeds benefit; planner correctly chooses Seq Scan; not a bug.

## Cross-links

- [`bbox-pre-filter.md`](bbox-pre-filter.md) — what the index enables
- [`subdivide-complex-polygons.md`](subdivide-complex-polygons.md) — subdivided polygons need their own index
- [`../../coding/postgis/references/indexing-strategies.md`](../../../coding/postgis/references/indexing-strategies.md) — PostGIS-specific GIST / SP-GIST / BRIN deep dive
- [`../../coding/postgis/references/vacuuming-and-bloat.md`](../../../coding/postgis/references/vacuuming-and-bloat.md) — PostGIS-specific bloat management
- [`../../coding/sedona/references/partitioning-strategies.md`](../../../coding/sedona/references/partitioning-strategies.md) — Sedona equivalent
