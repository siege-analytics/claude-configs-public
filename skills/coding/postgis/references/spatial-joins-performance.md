# Spatial Joins — Performance

The expensive operations and how to make them tractable.

## The cost model

Spatial joins are O(N×M) without indexes. With indexes, the planner does:

1. **Bounding-box pre-filter** (`&&` operator) using GIST. Cheap, returns superset.
2. **Exact predicate test** (`ST_Contains`, `ST_Intersects`, `ST_DWithin` distance) on the candidate set. Per-vertex cost.

Big polygons (Census tracts, congressional districts, oblong precincts) make step 2 slow because each test walks the polygon's vertices. Subdivision (below) is the canonical fix.

## Operators that use the index

| Operator | Meaning | Index? |
|---|---|---|
| `&&` | Bounding boxes intersect | yes |
| `<->` | KNN distance (use with `ORDER BY ... LIMIT`) | yes |
| `<#>` | KNN bounding-box distance | yes |
| `ST_Intersects(a, b)` | True intersection (calls `&&` internally) | yes |
| `ST_Contains(a, b)` | b is inside a (calls `&&` internally) | yes |
| `ST_DWithin(a, b, d)` | Within distance d (uses index expansion) | yes |
| `ST_Distance(a, b) < d` | Distance literal in WHERE | **no** |

The last one is a common bug: `WHERE ST_Distance(a.geom, b.geom) < 1000` does a sequential scan. Always use `ST_DWithin`.

## Subdivide complex polygons (the canonical 10-100× speedup)

Complex polygons slow point-in-polygon to a crawl. Pre-process once:

```sql
CREATE TABLE districts_subdivided AS
SELECT
    district_id,
    state,
    (ST_Subdivide(geom, 256)).geom AS geom
FROM districts;

CREATE INDEX ON districts_subdivided USING GIST (geom);
ANALYZE districts_subdivided;
```

`ST_Subdivide(geom, 256)` splits each polygon into pieces with at most 256 vertices. Each piece keeps the original `district_id`. Point-in-polygon now tests small pieces individually.

The join needs `DISTINCT` to dedupe matches across pieces of the same district:

```sql
SELECT DISTINCT d.id, d.amount, b.district_id
FROM donations AS d
INNER JOIN districts_subdivided AS b
    ON ST_Contains(b.geom, d.geom);
```

Paul Ramsey has documented 10-100× speedups on real Census-tract / congressional-district data. This is the highest-ROI optimization in PostGIS.

## KNN — nearest neighbor

For "nearest 5 features to this point," use the `<->` operator:

```sql
SELECT name, geom <-> ST_SetSRID(ST_Point(-98, 30), 4326) AS dist
FROM places
ORDER BY geom <-> ST_SetSRID(ST_Point(-98, 30), 4326)
LIMIT 5;
```

The repetition of the operator in `SELECT` and `ORDER BY` is necessary — the planner uses the `ORDER BY` form to drive the index. Aliasing breaks it; keep the literal expressions identical.

For nearest neighbors **per row** (find the nearest place for each donor), use a `LATERAL` join:

```sql
SELECT d.id, d.geom, p.name, p.geom <-> d.geom AS dist
FROM donors AS d,
LATERAL (
    SELECT name, geom
    FROM places
    ORDER BY places.geom <-> d.geom
    LIMIT 1
) AS p;
```

LATERAL re-executes the inner query per outer row but with the spatial index available. Without LATERAL, this is an N×M nightmare.

## Distance-within (range)

`ST_DWithin` uses the index by expanding the query geometry's bounding box by the distance:

```sql
-- All places within 5km of a point — index-aware
SELECT name FROM places
WHERE ST_DWithin(
    geom::geography,
    ST_SetSRID(ST_Point(-98, 30), 4326)::geography,
    5000  -- meters
);
```

For high-volume distance work in meters, store geography or projected-geometry columns to avoid casts. Or use `ST_DWithin(ST_Transform(geom, 32614), ST_Transform(target, 32614), 5000)` if you've stored projected geometries.

## Reading EXPLAIN

The plan you want to see:

```
Bitmap Heap Scan on districts d
  Filter: ((d.geom && donations.geom) AND _st_contains(d.geom, donations.geom))
  Heap Blocks: exact=...
  ->  Bitmap Index Scan on districts_geom_idx
      Index Cond: (d.geom && donations.geom)
```

Two stages: index returns candidates (`Bitmap Index Scan`), then exact filter (`_st_contains`). If you see `Seq Scan` instead of `Bitmap Index Scan`, the index isn't being used.

Common reasons:

- **Function on the indexed column:** `ST_Transform(geom, ...)` blocks the index. Materialize a transformed column.
- **Type mismatch:** geometry on one side, geography on the other → implicit cast, no index.
- **Tiny tables:** the planner may choose Seq Scan for tables under a few thousand rows because the I/O cost calculation favors it. Not a bug.
- **Stale stats:** `VACUUM ANALYZE` and re-run.

## Parallel query

PostGIS functions are progressively `PARALLEL SAFE` in PG 11+. Check:

```sql
SELECT proname, proparallel FROM pg_proc
WHERE proname LIKE 'st_%'
ORDER BY proname;
```

`s` = safe, `r` = restricted, `u` = unsafe. To encourage parallelism:

```sql
SET max_parallel_workers_per_gather = 4;
SET parallel_tuple_cost = 0.001;
SET parallel_setup_cost = 50;
```

In `EXPLAIN`, look for `Gather` and `Parallel Bitmap Heap Scan` nodes.

## Materialization for repeated joins

If the same spatial join runs in multiple queries (donor-to-district matching for several reports), materialize the assignment:

```sql
CREATE TABLE donation_district AS
SELECT DISTINCT d.id AS donation_id, b.district_id
FROM donations AS d
INNER JOIN districts_subdivided AS b
    ON ST_Contains(b.geom, d.geom);

CREATE INDEX ON donation_district (donation_id);
CREATE INDEX ON donation_district (district_id);
```

Refresh on a schedule. Subsequent queries are pure relational joins, no PostGIS overhead.

## When PostGIS is the wrong tool

If your spatial join is a single query against parquet files, no Postgres in the picture, consider DuckDB-spatial — see [`coding/duckdb-spatial/`](../../duckdb-spatial/SKILL.md).

If your data is bigger than one Postgres node can hold or the join exceeds memory, move to Sedona on Spark — see [`coding/sedona/`](../../sedona/SKILL.md).
