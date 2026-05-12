# Sedona Pitfalls

Bugs that don't error and silently produce wrong results, plus the operational footguns.

## 1. Forgot KryoSerializer + SedonaKryoRegistrator

```python
# Missing both — geometry serialization falls back to Java default
config = SedonaContext.builder().appName("oops").getOrCreate()
sedona = SedonaContext.create(config)
```

Symptom: jobs run but slowly; geometry shuffle is huge; no error. Fix:

```python
config = (
    SedonaContext.builder()
    .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
    .config("spark.kryo.registrator", "org.apache.sedona.core.serde.SedonaKryoRegistrator")
    .getOrCreate()
)
```

Both settings always.

## 2. Distance comparison without projection

```sql
SELECT a.id, b.id FROM places a JOIN places b ON ST_Distance(a.geom, b.geom) < 1000
```

If `geom` is in EPSG:4326 (lat/lng), `ST_Distance` returns degrees. `1000 degrees` wraps the planet several times. Either:

```sql
-- Use spheroidal distance
WHERE ST_DistanceSphere(a.geom, b.geom) < 1000  -- meters

-- Or project first
WHERE ST_Distance(
    ST_Transform(a.geom, 'EPSG:4326', 'EPSG:5070'),
    ST_Transform(b.geom, 'EPSG:4326', 'EPSG:5070')
) < 1000  -- now meters
```

For repeated work, materialize the projected column rather than transforming per query.

## 3. Python UDF in the spatial predicate — optimizer skips

```python
@udf(returnType=BooleanType())
def my_predicate(a, b):
    return a.intersects(b)

result = points.join(counties, my_predicate("points.geom", "counties.geom"))
```

Sedona's optimizer doesn't see inside UDFs — falls back to nested-loop join. Use `ST_Intersects` SQL.

## 4. `ST_Distance(geom, geom) < d` instead of `ST_DWithin`

`ST_Distance < d` requires computing distance for every pair (no index). `ST_DWithin(geom1, geom2, d)` uses spatial partitioning with bbox expansion — index-aware.

## 5. CRS lost across stages

Sedona DataFrame schemas don't carry CRS metadata. If stage 1 reprojects to EPSG:5070 and stage 2 forgets, downstream reads see projected coords without knowing it. Treat them as 4326 → wrong distances/areas.

Convention: name geometry columns by SRID. `geom_4326`, `geom_5070`. Catches the bug at column-name level.

## 6. Skew — one task takes 10× longer than others

Spatial data is almost always skewed (NY > Wyoming). Symptom in Spark UI: "straggler task" 10× the runtime of peers.

Mitigations (in order of cost):
- KDB-tree partitioner is adaptive; usually handles moderate skew automatically.
- Increase `spark.sedona.global.partitionnum`.
- Salt the heavy side and explode the small side. See [`partitioning-strategies.md`](partitioning-strategies.md).
- Subdivide complex polygons with `ST_Subdivide(geom, 256)`.

## 7. Broadcast hint ignored by spatial join

Sedona's spatial join optimizer doesn't always honor `/*+ BROADCAST(b) */` hints. Use `broadcast()` in the DataFrame API instead:

```python
from pyspark.sql.functions import broadcast
result = points.join(broadcast(counties), expr("ST_Within(points.geom, counties.geom)"))
```

## 8. AutoBroadcastJoinThreshold too low

Default `spark.sql.autoBroadcastJoinThreshold` is 10 MB. Most county/state polygon datasets are 50-200 MB compressed; auto-broadcast is skipped. Either bump:

```python
sedona.conf.set("spark.sql.autoBroadcastJoinThreshold", "200m")
```

Or use explicit `broadcast()`.

## 9. AQE interfering with spatial joins

Spark 3.x AQE can dynamically coalesce partitions and handle skew at runtime. But its skew-handler doesn't fully understand Sedona's spatial partitioning — sometimes makes things worse.

Test with both:

```python
sedona.conf.set("spark.sql.adaptive.enabled", "true")
# vs
sedona.conf.set("spark.sql.adaptive.enabled", "false")
```

Pick whichever gives faster runtime on your representative workload.

## 10. Reading shapefile via `binaryFile` and forgetting to parse

```python
df = sedona.read.format("binaryFile").load("s3://bucket/*.shp")
# df has columns: path, modificationTime, length, content (binary)
# But no geometry — you forgot to parse the .shp content
```

Sedona doesn't have a built-in shapefile reader from `binaryFile`. Either:
- Convert to GeoParquet/CSV+WKT on a single node first.
- Use `sedona.read.format("shapefile")` with the GeoTools wrapper JAR (heavier setup).

## 11. NULL geometries silently filter rows

`ST_Within(NULL, polygon)` returns NULL, not FALSE. Spark's join filter is "true" — NULL fails. Rows with NULL geom silently drop.

Filter explicitly if you want to keep them:

```sql
WHERE points.geom IS NOT NULL AND ST_Within(points.geom, counties.geom)
```

Or use `LEFT JOIN` and check post-join.

## 12. Empty geometries

Different from NULL. `ST_GeomFromText('POINT EMPTY')` is a valid empty geometry. Most predicates return FALSE on empties; some return TRUE. Test:

```sql
WHERE NOT ST_IsEmpty(points.geom) AND ST_Within(points.geom, counties.geom)
```

## 13. Driver OOM on `.collect()` of geometries

```python
result_df.collect()  # OOM if results have many large polygons
```

Geometry objects in Python are heavyweight. `.collect()` brings everything to driver memory; multi-MB geometries × many rows = OOM.

Stream to disk:

```python
result_df.write.format("geoparquet").save("s3://output/")
```

Or convert to WKT/WKB on the executor before collect:

```python
result_df.withColumn("geom_wkb", expr("ST_AsBinary(geom)")).drop("geom").collect()
```

WKB bytes are smaller than parsed Shapely objects.

## 14. `ST_Subdivide` in the WHERE clause

```sql
SELECT * FROM districts WHERE ST_Contains(ST_Subdivide(geom, 256), point)
```

Per-query subdivision — slow. Pre-process once:

```python
districts_sub = sedona.sql("SELECT id, name, ST_Subdivide(geom, 256) AS geom FROM districts").cache()
```

## 15. Sedona JAR version mismatch with Spark version

Sedona JARs are tied to specific Spark/Scala major versions. `sedona-spark-3.5_2.12` works with Spark 3.5 + Scala 2.12. Mismatched JARs fail at session creation with `NoSuchMethodError` or similar JVM errors.

Always check: Spark major version × Scala major version × Sedona version compatibility before installing JARs.

## 16. Forgetting to register UDFs in Scala

PySpark `SedonaContext.create(config)` registers ST_* automatically. Scala — you must call `SedonaContext.create()` to register the SQL functions. Without it, `ST_Within` is undefined.

## 17. EXPLAIN shows `CartesianProduct` on a spatial join

The optimizer didn't recognize the predicate. Causes:
- Predicate wrapped in a UDF.
- Predicate in `WHERE` instead of `ON`.
- Mixed CRSs (one side casts).
- Sedona JARs not loaded (silent — no spatial functions, falls back to scalar predicate evaluation).

If `CartesianProduct` appears, halt the job (it'll OOM) and investigate.

## Quick checklist when a Sedona job is slow or wrong

- [ ] KryoSerializer + SedonaKryoRegistrator both set
- [ ] Both sides of spatial join in same CRS, projected if distance/area work
- [ ] `EXPLAIN` shows `RangeJoin` or `BroadcastIndexJoin` (not `CartesianProduct`)
- [ ] Complex polygons subdivided
- [ ] Small side broadcast (or explicit `broadcast()`)
- [ ] No Python UDFs in spatial predicate
- [ ] No NULL/empty geometries lurking
- [ ] AQE tested both on and off
- [ ] Naming convention `geom_<srid>` to track CRS across stages
