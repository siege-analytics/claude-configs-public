# Principle: Bounding-Box Pre-Filter

Every fast spatial operation decomposes into two steps:

1. **Cheap pre-filter** using bounding-box intersection (`a.bbox && b.bbox`) — index-aware
2. **Exact predicate** test (`ST_Within`, `ST_Intersects`, etc.) — per-vertex cost

Make the pre-filter explicit (or trust your engine to generate it), and ensure it can use a spatial index. **The exact predicate without a pre-filter is a Cartesian product.**

## The principle

A naive `WHERE ST_Within(a.geom, b.geom)` on two large tables tests every row pair for exact containment. Each test walks every vertex of both polygons. Catastrophic at scale.

The same query *with* a bounding-box pre-filter:

1. The bounding-box of `b.geom` is checked against the bounding-box of `a.geom` using the spatial index — O(log n) per row, returns a small candidate set
2. `ST_Within` runs only on the candidates — exact but limited to a manageable subset

The total cost is dominated by the pre-filter (cheap) rather than the exact test (expensive).

## What "bounding box" means

For any geometry, the bounding box is the smallest axis-aligned rectangle containing it. Always 2 numbers (xmin, ymin) + 2 numbers (xmax, ymax). Spatial indexes (GIST in PostGIS, R-tree in DuckDB / GeoPandas / Sedona) store bounding boxes, not full geometries.

```
Geometry: complex polygon with 5,000 vertices
Bounding box: 4 numbers
Index lookup against bbox: ~microseconds
Exact predicate against full geometry: ~milliseconds (per vertex)
```

The ratio matters: for large polygons (Census tracts, congressional districts), the exact predicate is 1000× the cost of the bbox check. That's the entire performance optimization.

## Per-engine implementation

### PostGIS

The optimizer auto-generates the pre-filter when you use index-aware predicates:

```sql
-- ST_Within calls && internally; planner uses GIST
SELECT p.id, c.geoid
FROM points p JOIN counties c ON ST_Within(p.geom, c.geom);
```

`EXPLAIN` shows two stages: `Bitmap Index Scan` (the pre-filter) followed by the exact predicate.

When the predicate doesn't auto-generate the pre-filter, use `&&` explicitly:

```sql
-- ST_Distance doesn't use index — won't pre-filter
SELECT * FROM features WHERE ST_Distance(a.geom, b.geom) < 1000;  -- BAD

-- Make the pre-filter explicit via ST_DWithin (uses index expansion)
SELECT * FROM features WHERE ST_DWithin(a.geom, b.geom, 1000);  -- GOOD
```

Index-using predicates: `ST_Intersects`, `ST_Contains`, `ST_Within`, `ST_Covers`, `ST_CoveredBy`, `ST_DWithin`, `ST_Touches`, `ST_Overlaps`, `&&`, `<->` (KNN).

Not index-using: bare `ST_Distance` in WHERE, `ST_Equals`, custom UDFs.

### GeoPandas

`gpd.sjoin` uses the right side's spatial index automatically (STRtree):

```python
counties.sindex  # build the index eagerly (optional)
joined = gpd.sjoin(points, counties, predicate="within", how="left")
```

Internally: STRtree query (bbox check) → candidate list → exact predicate. The two-stage pattern.

For raw Shapely (no GeoDataFrame), the same pattern manually:

```python
from shapely.strtree import STRtree

tree = STRtree(polygons)
for point in points:
    candidates = tree.query(point)  # bbox pre-filter
    matches = [polygons[i] for i in candidates if polygons[i].contains(point)]  # exact
```

### Sedona

The spatial-join optimizer uses bbox pre-filter automatically when it recognizes the predicate:

```python
result = sedona.sql("""
    SELECT * FROM points p JOIN counties c ON ST_Within(p.geom, c.geom)
""")
# EXPLAIN shows RangeJoin (which uses bbox + spatial partitioning)
```

If the optimizer generates a `CartesianProduct` instead of `RangeJoin`, the predicate isn't being recognized — usually because it's inside a UDF or in `WHERE` instead of `ON`. Refactor to expose the spatial predicate directly.

### DuckDB-spatial

DuckDB builds an in-memory R-tree implicitly when it sees `ST_Within` / `ST_Intersects` in a join condition:

```python
con.execute("""
    SELECT p.id, c.geoid
    FROM 'donations.parquet' p
    JOIN 'counties.parquet' c ON ST_Within(p.geom, c.geom)
""")
# EXPLAIN ANALYZE shows RTREE_INDEX_JOIN
```

For repeated queries against the same right-side, materialize:

```sql
CREATE INDEX counties_geom_idx ON counties USING RTREE (geom);
```

## Diagnostic — is the pre-filter happening?

**PostGIS:** `EXPLAIN (ANALYZE, BUFFERS)`. Look for `Bitmap Index Scan on <table>_geom_idx`. If you see `Seq Scan` instead, the index isn't being used.

**GeoPandas:** check `gdf.sindex` exists; verify with `cProfile` that `STRtree.query` dominates over the exact predicate.

**Sedona:** `result.explain(extended=True)`. Look for `RangeJoin` or `BroadcastIndexJoin`. If you see `CartesianProduct`, the optimizer didn't recognize the predicate.

**DuckDB:** `EXPLAIN ANALYZE`. Look for `RTREE_INDEX_JOIN` or `RANGE_JOIN`. `NESTED_LOOP_JOIN` on a spatial predicate means the optimizer didn't use the index.

## When pre-filter doesn't help

Some workloads can't use bbox pre-filter effectively:

- **Many-to-many full overlay** (`ST_Intersection` of two large polygon sets) — the bbox pre-filter narrows candidates, but the exact intersection is still expensive per pair.
- **Predicates with no bbox interpretation** — `ST_Equals`, exact-coordinate matching.
- **Distance threshold larger than bbox dimensions** — pre-filter returns most of the right-side.
- **Right-side too small to benefit from index** (< ~1000 rows) — sequential scan is faster than building/querying the index.

For these cases, accept that the workload is expensive and move it to a more capable engine (Sedona for distributed) or pre-aggregate.

## When the pre-filter is broken

The bbox pre-filter assumes the bbox is correct. It can be wrong if:

- **Geometry is invalid** — bowtie polygons may have a bbox that doesn't enclose the geometry's true extent
- **Geometry has 3D / M dimensions** — bbox might be 2D-only, missing the Z extent
- **Mixed SRIDs** — bboxes from different CRSs don't compare meaningfully

All three trace back to the [`validate-on-ingest`](validate-on-ingest.md) and [`crs-is-meaning`](crs-is-meaning.md) principles. Pre-filter assumes prior hygiene.

## Pitfalls

- **`WHERE ST_Distance(...) < d`** instead of `ST_DWithin(...)` — no pre-filter, full table scan.
- **Function on the indexed column** — `ST_Transform(geom, 5070)` blocks the index because the bbox is for the original SRID, not the transformed one. Materialize the transformed geometry as a separate column.
- **`ST_Subdivide` on a complex polygon at query time** — recomputes per query; no useful index. Pre-process; see [`subdivide-complex-polygons.md`](subdivide-complex-polygons.md).
- **Spatial join predicate inside a UDF** — optimizer can't see inside; falls back to nested loop.
- **`OR` in spatial predicates** — `ON ST_Within(a, b) OR ST_Within(b, a)` — the optimizer handles this with mixed success across engines. Split into two queries with `UNION` if performance suffers.
- **Tiny right side, building the index doesn't pay** — < 1000 rows; just sequential.
- **Trusting bbox on invalid geometry** — see above; fix geometry first.

## Cross-links

- [`spatial-indexing-discipline.md`](spatial-indexing-discipline.md) — bbox pre-filter requires the index; this principle is what indices enable
- [`subdivide-complex-polygons.md`](subdivide-complex-polygons.md) — large polygons make the exact predicate expensive even with pre-filter; subdivision is the further optimization
- [`../../coding/postgis/references/spatial-joins-performance.md`](../../../coding/postgis/references/spatial-joins-performance.md) — PostGIS-specific deep dive on join performance
- [`../../coding/sedona/references/spatial-joins-at-scale.md`](../../../coding/sedona/references/spatial-joins-at-scale.md) — Sedona equivalent
