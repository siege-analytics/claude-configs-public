# Spatial Joins at Scale

How Sedona executes spatial joins, when each strategy applies, and how to read the plan.

## The cost model

Sedona spatial joins decompose into:

1. **Spatial partitioning** — both sides repartitioned by spatial location (KDB-tree by default; see [`partitioning-strategies.md`](partitioning-strategies.md)). Cost: shuffle proportional to total data volume.
2. **Local spatial join** — within each matched partition pair, an in-memory STRtree-backed predicate test. Cost: bounding-box pre-filter (cheap) + exact predicate (per-vertex cost).

For small-on-large patterns, **broadcast** instead — see below.

## Range join (containment, intersection)

```sql
SELECT p.donation_id, c.geoid
FROM points p
JOIN counties c
ON ST_Within(p.geom, c.geom)
```

Sedona detects `ST_Within` (also `ST_Contains`, `ST_Intersects`, `ST_Covers`, `ST_CoveredBy`, `ST_Overlaps`, `ST_Touches`, `ST_Crosses`) as a spatial predicate and triggers spatial partitioning + local STRtree.

EXPLAIN shows `RangeJoin` or `BroadcastIndexJoin` (when one side is broadcast). Without a recognized spatial predicate, you get a Cartesian product + filter — almost always catastrophic.

## Distance join

```sql
SELECT a.id, b.id, ST_Distance(a.geom, b.geom) AS dist
FROM places a
JOIN places b
ON ST_Distance(a.geom, b.geom) < 1000
```

Sedona partitions both sides spatially with **expansion** — partition boundaries are widened by the distance threshold so cross-boundary matches aren't missed.

For meter distances, both sides must be in a meter CRS:

```python
df = df.withColumn("geom_5070", expr("ST_Transform(geom, 'EPSG:4326', 'EPSG:5070')"))
```

Then `ST_Distance(a.geom_5070, b.geom_5070) < 1000` is meters.

For great-circle distance without projection:

```sql
WHERE ST_DistanceSphere(a.geom, b.geom) < 1000
```

Slower per row (spheroidal math) but no projection step.

## Broadcast spatial join — the highest-leverage optimization

When one side is small enough to fit in memory (< ~500 MB compressed parquet), explicit broadcast:

```python
from pyspark.sql.functions import broadcast

result = points.join(
    broadcast(counties),
    expr("ST_Within(points.geom, counties.geom)"),
    "left",
)
```

Sedona builds an in-memory STRtree on the broadcast side and probes from each executor. No shuffle on the large side. Eliminates the most expensive part of the spatial join.

Increase the auto-broadcast threshold for larger broadcasts:

```python
sedona.conf.set("spark.sql.autoBroadcastJoinThreshold", "200m")
```

Beyond ~500 MB, the broadcast itself becomes a bottleneck (each executor copies the full small side). Switch back to spatial partitioning.

## kNN join

For "for each row in A, find the k nearest in B":

```python
from sedona.sql.st_functions import ST_Distance

# Method 1: cross join + filter (small data only)
result = (
    a.crossJoin(b)
     .withColumn("dist", expr("ST_Distance(a.geom, b.geom)"))
     .where(...)
)
```

This doesn't scale. For scalable kNN, use Sedona's KNN_join (Sedona 1.4+):

```python
result = sedona.sql("""
    SELECT a.id, b.id, b_dist
    FROM a JOIN b
    ON ST_Knn(a.geom, b.geom, 5, false)
""")
```

Or fall back to PostGIS if you have it (better KNN ergonomics with `<->` operator).

## When the optimizer doesn't kick in

If `EXPLAIN` shows a `BroadcastNestedLoopJoin` or `CartesianProduct` on a spatial predicate:

- **Predicate is wrapped in a UDF**: `WHERE my_udf(a.geom, b.geom)` — optimizer can't see inside. Inline the predicate as `ST_*`.
- **Predicate is in `WHERE`, not `ON`**: For Spark SQL inner joins this is usually equivalent, but for spatial joins some versions only optimize when in `ON`. Move it to `ON`.
- **Mixed predicate**: `ON ST_Within(a.geom, b.geom) AND a.id != b.id` — Sedona handles this. `ON ST_Within(a.geom, b.geom) OR ...` — may not.

## Materialize intermediate joins

If the same spatial join feeds multiple downstream queries, materialize:

```python
points_with_county = sedona.sql("""
    SELECT p.*, c.geoid AS county_geoid
    FROM points p
    JOIN counties c
    ON ST_Within(p.geom, c.geom)
""")

points_with_county.write.format("geoparquet").mode("overwrite").save("s3://staging/joined/")
```

Subsequent queries are simple SQL joins, no spatial work.

## Subdivide complex polygons

If a few polygons (state boundaries, complex Census tracts with thousands of vertices) dominate the join time:

```python
counties_sub = sedona.sql("""
    SELECT geoid, name, ST_Subdivide(geom, 256) AS geom
    FROM counties
""")
counties_sub.cache()

result = sedona.sql("""
    SELECT DISTINCT p.donation_id, c.geoid
    FROM points p
    JOIN counties_sub c
    ON ST_Within(p.geom, c.geom)
""")
```

`DISTINCT` because each county becomes multiple rows (subdivision pieces). 10-100× speedup on point-in-polygon against complex boundaries.

## Reading the plan

```python
result.explain(extended=True)
```

What to look for:

- **`RangeJoin`** — spatial join optimizer kicked in. Good.
- **`BroadcastIndexJoin`** — broadcast spatial join. Good.
- **`BroadcastNestedLoopJoin`** with spatial predicate — optimizer didn't recognize the predicate. Bad.
- **`CartesianProduct`** — full N×M product. Almost always wrong.
- **`Exchange hashpartitioning`** — non-spatial shuffle. Means you're shuffling on a non-geometry key.
- **`Exchange spatialpartitioning`** — spatial shuffle. Expected for non-broadcast spatial joins.

For interactive plan analysis, the Spark UI's SQL tab is more readable than text plans.

## When Spark is the wrong tool

Spatial joins on data that fits in 32 GB RAM run faster in DuckDB-spatial than in Spark + Sedona. The Spark overhead (driver, scheduler, serialization) is significant; Sedona makes sense at terabyte scale, not gigabyte.

If you find yourself running Sedona on a single-node Spark cluster, consider DuckDB-spatial instead — see [skill:duckdb-spatial].

## Checklist for slow spatial joins

- [ ] Plan shows `RangeJoin` or `BroadcastIndexJoin`, not `CartesianProduct`
- [ ] Both sides in the same (and meter, for distance) CRS
- [ ] One side broadcast if < 500 MB compressed
- [ ] Complex polygons subdivided
- [ ] Partition count appropriate (~50K rows per points partition)
- [ ] No Python UDFs in the spatial predicate
- [ ] `KryoSerializer` + `SedonaKryoRegistrator` configured
- [ ] AQE settings tested both on and off
