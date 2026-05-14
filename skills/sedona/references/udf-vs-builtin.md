# Sedona ST_* SQL vs Python UDFs

The performance gap between Sedona's built-in `ST_*` functions and custom Python UDFs is huge — typically 10-100×. Understand why and prefer ST_* whenever possible.

## The cost difference

| | Sedona ST_* (JVM) | Python UDF |
|---|---|---|
| Per-row cost | ~µs (vectorized JVM) | ~ms (per-row Python serde) |
| Spatial optimizer integration | Yes (RangeJoin, broadcast, partitioning) | No (treated as opaque) |
| Memory | Geometry stays as JTS in JVM | Geometry serialized to Python (Shapely WKB) and back |
| Scalability | Linear in row count | Becomes the bottleneck at 10M+ rows |

For a 100M-row dataset, that's the difference between a 10-minute job and a 10-hour job.

## The catalog

Sedona ships hundreds of `ST_*` functions. Common ones used in Siege work:

### Construction

```sql
ST_Point(x, y)
ST_PointFromText('POINT(-98 30)', 4326)
ST_GeomFromWKT('POLYGON(...)', 4326)
ST_GeomFromWKB(wkb_binary)
ST_GeomFromGeoJSON('{"type": "Point", ...}')
```

### Predicates

```sql
ST_Within(a, b)
ST_Contains(a, b)
ST_Intersects(a, b)
ST_Covers(a, b)
ST_Touches(a, b)
ST_Crosses(a, b)
ST_Overlaps(a, b)
ST_Disjoint(a, b)
```

### Measurement

```sql
ST_Distance(a, b)            -- in CRS units
ST_DistanceSphere(a, b)      -- great-circle meters
ST_DistanceSpheroid(a, b)    -- spheroidal meters
ST_Area(geom)                -- in CRS units²
ST_Length(geom)              -- in CRS units
ST_Perimeter(geom)
```

### Transformation

```sql
ST_Transform(geom, 'EPSG:4326', 'EPSG:5070')
ST_Buffer(geom, 100)
ST_Centroid(geom)
ST_Envelope(geom)
ST_ConvexHull(geom)
ST_Simplify(geom, tolerance)
ST_MakeValid(geom)
ST_Subdivide(geom, max_vertices)
```

### Aggregates

```sql
ST_Union_Aggr(geom)          -- multi-row union
ST_Envelope_Aggr(geom)       -- bounding box of all rows
ST_Intersection_Aggr(geom)
```

### Indexing

```sql
ST_GeoHash(geom, precision)   -- 9-char geohash
ST_S2CellIDs(geom, level)     -- S2 cell IDs at level
```

### Output

```sql
ST_AsText(geom)              -- WKT
ST_AsBinary(geom)            -- WKB
ST_AsGeoJSON(geom)
ST_AsKML(geom)
```

If you need it, check the Sedona function reference first — there's almost always a builtin.

## When to use a UDF anyway

A Python UDF is acceptable when:

1. **The operation has no `ST_*` equivalent** and isn't easily decomposable. Rare.
2. **You're calling out to a non-spatial Python lib** (e.g., a custom geocoder, an ML model on geometry features). Even then, prefer Pandas UDFs (vectorized).
3. **One-off exploration** on a small DataFrame. Performance doesn't matter at < 1M rows.

For everything else, the ST_* SQL form is faster *and* easier to read.

## Pandas UDFs — when you must

If you do need a UDF, use a Pandas (vectorized) UDF, not a per-row UDF:

```python
from pyspark.sql.functions import pandas_udf
from pyspark.sql.types import StringType
import pandas as pd
from shapely import wkb

@pandas_udf(returnType=StringType())
def custom_geohash_batch(wkb_series: pd.Series) -> pd.Series:
    return wkb_series.apply(lambda b: wkb.loads(b).geohash())
```

Pandas UDFs serialize batches (default 10K rows) instead of individual rows. ~10× faster than per-row UDFs but still slower than the JVM equivalent.

## Anti-patterns to grep for

```python
# BAD — udf imports
from pyspark.sql.functions import udf

# BAD — Shapely operations on Spark Columns
from shapely import wkb
df = df.withColumn("centroid", udf(lambda b: wkb.loads(b).centroid.wkt)("geom_wkb"))

# GOOD — equivalent in Sedona SQL
df = df.withColumn("centroid", expr("ST_AsText(ST_Centroid(geom))"))
```

When reviewing PySpark spatial code, search for `from shapely`, `udf`, `pandas_udf`. Each occurrence near geometry columns is a candidate for replacement with `ST_*` SQL.

## ST_* + window functions

```python
result = sedona.sql("""
    WITH counted AS (
        SELECT 
            ST_GeoHash(geom, 5) AS geohash5,
            COUNT(*) AS n
        FROM points
        GROUP BY geohash5
    )
    SELECT geohash5, n,
           RANK() OVER (ORDER BY n DESC) AS rank
    FROM counted
    WHERE n > 100
""")
```

Combining ST_* with regular SQL aggregations and windowing is the most expressive shape — keep everything in SQL, no UDFs.

## Native spatial on Databricks 13+

Databricks 13+ runtimes ship with native spatial functions that don't require Sedona:

```sql
ST_Point(x, y)
ST_Within(a, b)
ST_Distance(a, b)
```

If `siege_utilities.geo.spatial_runtime.resolve_spatial_runtime_plan().engine == "databricks_native"`, you can use ST_* without importing Sedona at all. Performance is comparable (Databricks's spatial is also JVM-vectorized).

For portability across Databricks versions, prefer Sedona — same syntax, more functions, version-stable.

## Function reference

- Sedona docs: https://sedona.apache.org/latest-snapshot/api/sql/Function/
- Per-version function lists matter; Sedona 1.5+ has substantially more functions than 1.3.

## Quick test for "is this UDF necessary?"

```
1. What does the UDF do?
2. Is there an ST_* function that does the same thing? (Check the catalog above first.)
3. Can you decompose it into a chain of ST_* functions?
4. If genuinely no — vectorize it as a Pandas UDF.
5. If even that doesn't fit — push the operation outside Spark (e.g., process the geometry in a separate batch job, store the result, join back).
```
