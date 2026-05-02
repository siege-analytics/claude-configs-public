---
name: sedona
description: "Apache Sedona for distributed spatial work on Spark. TRIGGER: from sedona, SedonaContext, SedonaRegistrator, ST_* in Spark SQL, %scala spatial code on Databricks. Same skill for both PySpark and Scala scaffolding — spatial logic identical, scaffolding diverges in known ways. Stacks with `coding/spark/`, `coding/scala-on-spark/`, and `shelves/systems-architecture/data-intensive/`."
routed-by: coding-standards
user-invocable: false
paths: "**/*.py,**/*.scala,**/*.sql"
---

# Apache Sedona — Distributed Spatial on Spark

Use Sedona when:
- Data is bigger than one machine's RAM and a Spark cluster is available.
- Spatial work is part of a larger Spark pipeline already (joining spatial with non-spatial transforms in one DAG).
- You need distributed spatial joins on hundreds of millions to billions of points/polygons.

Don't use Sedona for:
- Single-node datasets (< 10 GB) — use **GeoPandas** ([`coding/geopandas/`](../geopandas/SKILL.md)) or **DuckDB-spatial** ([`coding/duckdb-spatial/`](../duckdb-spatial/SKILL.md)).
- Persistent multi-user query workloads — use **PostGIS** ([`coding/postgis/`](../postgis/SKILL.md)).

## Always-on companions

- [`coding/spark/`](../spark/SKILL.md) — Siege-specific Spark patterns (medallion, catalog rules, transform shape).
- [`coding/scala-on-spark/`](../scala-on-spark/SKILL.md) — when scaffolding is `.scala` or `%scala`.
- [`coding/python/`](../python/SKILL.md) — when scaffolding is PySpark.
- [`shelves/systems-architecture/data-intensive/`](../../shelves/systems-architecture/data-intensive/SKILL.md) — partitioning, replication, batch/stream theory.
- [`_jvm-rules.md`](../../_jvm-rules.md), [`_python-rules.md`](../../_python-rules.md), [`_data-trust-rules.md`](../../_data-trust-rules.md), [`_siege-utilities-rules.md`](../../_siege-utilities-rules.md).

## References

- [`partitioning-strategies.md`](references/partitioning-strategies.md) — KDB-tree / quad-tree, broadcast spatial joins
- [`spatial-joins-at-scale.md`](references/spatial-joins-at-scale.md) — range joins, distance joins, cost model, when to broadcast
- [`udf-vs-builtin.md`](references/udf-vs-builtin.md) — ST_* SQL vs Python UDF performance gap
- [`raster.md`](references/raster.md) — Sedona raster ops; when in scope vs out
- [`scaffolding-python-vs-scala.md`](references/scaffolding-python-vs-scala.md) — same logic, scaffolding diverges in 5–10 known ways
- [`pitfalls.md`](references/pitfalls.md) — skew, OOM on join, CRS lost across stages, Kryo registration
- [`siege-utilities-sedona.md`](references/siege-utilities-sedona.md) — ALWAYS call `resolve_spatial_runtime_plan()` first; encode/decode geometry for Spark safety

## Always start with: runtime detection (siege_utilities)

Before writing any Sedona code, ask SU what the runtime offers:

```python
from siege_utilities.geo.spatial_runtime import resolve_spatial_runtime_plan

plan = resolve_spatial_runtime_plan()
# Returns SpatialRuntimePlan with .engine in {"databricks_native", "sedona", "python"}
```

Three reasons:

1. **Databricks runtimes 13+ have native spatial.** `ST_*` SQL works without Sedona at all on those clusters. SU detects and recommends.
2. **Sedona presence varies.** SU's plan tells you whether `apache-sedona` is on the classpath without import-time crashes.
3. **Fallback is real.** If neither native spatial nor Sedona is available, push to a non-Spark path (DuckDB-spatial or single-node Sedona via PySpark local mode).

For Databricks specifically:

```python
from siege_utilities.geo.databricks_fallback import select_spatial_loader, SpatialLoaderPlan

loader = select_spatial_loader(
    ogr2ogr_available=False,
    sedona_available=True,
    native_spatial_available=False,
)
print(loader.engine, loader.method)
```

## Sedona session — PySpark

```python
from sedona.spark import SedonaContext

config = (
    SedonaContext.builder()
    .appName("spatial-pipeline")
    .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
    .config("spark.kryo.registrator", "org.apache.sedona.core.serde.SedonaKryoRegistrator")
    .getOrCreate()
)
sedona = SedonaContext.create(config)
```

Two settings always needed: KryoSerializer and the SedonaKryoRegistrator. Without them, geometry serialization across stages drops to Java default and breaks silently or wastes I/O.

## Sedona session — Scala

```scala
import org.apache.sedona.spark.SedonaContext
import org.apache.spark.sql.SparkSession

val config = SedonaContext
  .builder()
  .appName("spatial-pipeline")
  .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
  .config("spark.kryo.registrator", "org.apache.sedona.core.serde.SedonaKryoRegistrator")
  .getOrCreate()

val sedona = SedonaContext.create(config)
```

Same settings. Same registrator. The spatial logic that follows is identical between Python and Scala.

See [`scaffolding-python-vs-scala.md`](references/scaffolding-python-vs-scala.md) for the small differences (DataFrame creation, UDF registration, type imports).

## Read spatial data

```python
# WKT in a column
df = (
    sedona.read.format("csv")
        .option("header", True)
        .load("s3://bucket/data.csv")
)
df = df.withColumn("geom", expr("ST_GeomFromText(wkt_col, 4326)"))

# WKB binary column (the GeoParquet pattern)
df = sedona.read.format("parquet").load("s3://bucket/features.parquet")
df = df.withColumn("geom", expr("ST_GeomFromWKB(geometry_wkb)"))

# Direct GeoParquet (Sedona 1.5+)
df = sedona.read.format("geoparquet").load("s3://bucket/features.parquet")
```

## Spatial join — range join

```python
points = sedona.read.format("geoparquet").load("s3://bucket/donations.parquet")
counties = sedona.read.format("geoparquet").load("s3://bucket/counties.parquet")

points.createOrReplaceTempView("points")
counties.createOrReplaceTempView("counties")

result = sedona.sql("""
    SELECT p.donation_id, c.geoid, c.name
    FROM points p
    JOIN counties c
    ON ST_Within(p.geom, c.geom)
""")
```

Sedona's optimizer detects spatial joins from `ST_*` predicates and chooses a partitioning strategy (KDB-tree, quad-tree). See [`spatial-joins-at-scale.md`](references/spatial-joins-at-scale.md).

## Distance join

```python
result = sedona.sql("""
    SELECT a.id, b.id, ST_Distance(a.geom, b.geom) AS dist
    FROM places a
    JOIN places b
    ON ST_Distance(a.geom, b.geom) < 1000
       AND a.id != b.id
""")
```

For meter distances, both sides must be in a meter-based CRS. Project before the join (see [`pitfalls.md`](references/pitfalls.md) — CRS lost across stages).

## Broadcast a small spatial table

If one side fits comfortably in memory (~100 MB compressed) and the other is huge:

```python
from pyspark.sql.functions import broadcast

result = points.join(
    broadcast(counties),
    expr("ST_Within(points.geom, counties.geom)"),
    "left",
)
```

Eliminates the spatial shuffle. The biggest single optimization for "billions of points × thousand of polygons" workloads.

## ST_* SQL vs Python UDF

Always prefer ST_* SQL functions. They run in the JVM, are vectorized, and integrate with Sedona's spatial optimizer. Python UDFs serialize to Python per row and bypass the optimizer:

```python
# BAD — Python UDF
from pyspark.sql.functions import udf
from pyspark.sql.types import StringType
from shapely import wkb

@udf(returnType=StringType())
def get_geohash(wkb_bytes):
    return wkb.loads(wkb_bytes).geohash(...)

df = df.withColumn("geohash", get_geohash("geom"))  # row-by-row Python

# GOOD — Sedona builtin
df = sedona.sql("SELECT *, ST_GeoHash(geom, 9) AS geohash FROM df")
```

See [`udf-vs-builtin.md`](references/udf-vs-builtin.md) for the full performance comparison.

## CRS across stages

Sedona geometry columns don't carry CRS metadata in the schema. If you reproject in stage 1 and forget in stage 2, downstream reads see the projected coords without knowing they're projected. Discipline:

```python
# Stage 1 output
projected = points.withColumn("geom_5070", expr("ST_Transform(geom, 'EPSG:4326', 'EPSG:5070')"))
projected.write.format("geoparquet").save("s3://stage/projected/")

# Stage 2 input — explicitly rename the column to indicate projection
df = sedona.read.format("geoparquet").load("s3://stage/projected/")
df = df.withColumnRenamed("geom_5070", "geom_5070")  # already named — keep convention
```

Naming convention: `geom_<srid>` for any non-4326 geometry column. Catches the bug at column-name level.

## Common mistakes

See [`pitfalls.md`](references/pitfalls.md). Top three:

1. **Forgot Kryo registrator.** Geometry serialization falls back to Java default — silent perf loss.
2. **Distance comparison without projection.** `ST_Distance(geom1, geom2) < 1000` on EPSG:4326 = "less than 1000 degrees" — meaningless.
3. **Python UDF for ST_* operation.** 10-100× slower than the Sedona builtin equivalent.

## When Sedona is the wrong tool

- Single-node, < 10 GB → GeoPandas or DuckDB-spatial.
- Persistent multi-user → PostGIS.
- Sub-second-latency lookups → keep PostGIS in the picture as the serving layer.

Sedona is for *batch processing of large spatial joins.* Use it when that's the shape of the problem.
