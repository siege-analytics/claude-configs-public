# siege_utilities + Sedona — Interop Map

When working with Sedona in Siege projects, [`siege_utilities`](https://github.com/siege-analytics/siege_utilities) provides **runtime detection** and **geometry encoding** but does *not* wrap Sedona's spatial operations. The pattern: ask SU what runtime is available, use SU's encoder/decoder for cross-stage geometry safety, write the spatial logic directly in Sedona SQL.

## Always start with: runtime detection

Before writing any Sedona code, call SU:

```python
from siege_utilities.geo.spatial_runtime import resolve_spatial_runtime_plan, SpatialRuntimePlan

plan = resolve_spatial_runtime_plan()
# plan.engine ∈ {"databricks_native", "sedona", "python"}
# plan.reason: human-readable explanation
# plan.fallback_chain: ordered list of engines tried
```

Three reasons this matters:

1. **Databricks runtimes 13+ ship native spatial.** ST_* SQL works without Sedona at all — same syntax. SU detects the runtime version and recommends the right path.
2. **Sedona JAR presence is uncertain.** Importing `sedona.spark` crashes if the JAR isn't on the classpath. SU checks safely without import-time crashes.
3. **The fallback is explicit.** If neither native nor Sedona is available, SU surfaces the "fall back to single-node Python" recommendation rather than letting the job fail mid-DAG.

## Databricks-specific loader plan

For Databricks workflows that may or may not have GDAL / ogr2ogr available:

```python
from siege_utilities.geo.databricks_fallback import select_spatial_loader, SpatialLoaderPlan

loader = select_spatial_loader(
    ogr2ogr_available=False,        # check via shutil.which("ogr2ogr") if uncertain
    sedona_available=True,
    native_spatial_available=False,  # set True for DBR 13+
)
print(loader.engine)   # 'sedona' (in this example)
print(loader.method)   # 'sedona_st_geomfromwkb' or similar
```

Use this *before* deciding whether to use Sedona or to push the work to a non-distributed path.

## Encode/decode geometry across Spark stages

Sedona geometry columns serialize OK between executors but can drop CRS metadata or get serde-mangled across stage boundaries (especially when intermediate results round-trip through Parquet). SU provides a payload format:

```python
from siege_utilities.geo.spatial_runtime import (
    GeometryPayload,
    encode_geometry,
    decode_geometry,
    payload_to_spark_row,
    spark_row_to_payload,
)

# In an executor, encode for downstream stage:
payload: GeometryPayload = encode_geometry(shapely_geom)
# payload is WKB-bytes + SRID + dim flags — Spark-safe

# In the next stage, decode:
geom = decode_geometry(payload)
```

For Spark-side use:

```python
from pyspark.sql.functions import udf
from pyspark.sql.types import BinaryType

# UDF that returns the WKB payload — better than `geom.wkt` (loses precision) or pickling
@udf(BinaryType())
def to_payload(geom):
    return encode_geometry(geom).wkb_bytes
```

When you do need a custom UDF (rare — prefer ST_*), use SU's payload format for cross-stage safety.

## What SU does NOT do — write directly

### Spatial joins

SU has no `sedona_spatial_join(left, right, predicate, how)` helper. Use Sedona SQL or DataFrame API directly:

```python
result = sedona.sql("""
    SELECT p.id, c.geoid
    FROM points p JOIN counties c
    ON ST_Within(p.geom, c.geom)
""")
```

This is **upstream PR candidate SU-4** (sedona spatial-join wrappers). Until it lands, write the join directly.

### ST_* function wrappers

No `siege_sedona_buffer(geom, dist)` or similar. Use ST_* SQL.

### Partition tuning

SU doesn't pre-set partitioner config. Set in your session:

```python
sedona.conf.set("spark.sedona.global.partitionnum", "200")
sedona.conf.set("spark.sedona.join.gridtype", "kdbtree")  # or "quadtree"
```

### Raster operations

SU has no Sedona raster wrappers. Use `RS_*` SQL directly — see [`raster.md`](raster.md).

## Checklist when starting Sedona work

- [ ] Called `resolve_spatial_runtime_plan()` to confirm runtime
- [ ] If on Databricks, checked `select_spatial_loader()` for the loader plan
- [ ] KryoSerializer + SedonaKryoRegistrator configured in session
- [ ] CRS strategy decided up-front (which stage projects to which SRID)
- [ ] Naming convention `geom_<srid>` to track CRS across stages
- [ ] If using UDFs (rare), encoding via `encode_geometry()` for cross-stage safety
- [ ] Spatial joins written as ST_* SQL, not Python predicate functions

## Pending SU upstream PRs that close gaps here

- **SU-4:** Sedona spatial-join wrappers + broadcast helper. Eliminates the most-common boilerplate.
- **SU-9:** DuckDB spatial-query helpers (relevant when falling through from Sedona to DuckDB-spatial as the single-node alternative).

Until they land, the patterns above are the workaround.

## Mental model

Treat SU as the **runtime planner** and the **cross-stage geometry safety net**, and Sedona as the **spatial execution engine**. The two complement; neither replaces the other. Most pipeline code looks like:

1. SU detects runtime
2. Sedona session created with appropriate config
3. Sedona SQL does the spatial work
4. SU encodes/decodes geometries when crossing stages
5. Sedona writes results
