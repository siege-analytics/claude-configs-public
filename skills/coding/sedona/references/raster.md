# Sedona Raster — When and How

Sedona supports raster operations (Sedona 1.4+). When the task is "scale up raster work to a Spark cluster," it's the right tool. When it's "I have one COG and need to read it once," it's overkill.

## When raster on Sedona makes sense

- **Big raster, distributed compute** — terabyte-scale satellite imagery, climate data cubes, NLDAS time series.
- **Raster + vector at scale** — joining millions of polygons against pixel statistics (e.g., "average NDVI per Census tract over a year of Landsat scenes").
- **Pipelines already on Spark** — adding raster to an existing Spark job; avoiding cross-system data movement.

## When raster on Sedona doesn't make sense

- **One-off COG read** — use `rasterio` directly.
- **Raster with no vector cross-cutting** — `rasterio` or `xarray` on a single node is faster.
- **Web-tile generation** — `rio-tiler` + cloud-native raster (COG on S3) is the right shape.
- **Climate data cubes** — `xarray` + `dask` is the dominant ecosystem; only move to Sedona if the join with vector boundaries is the bottleneck.

## Setup

Same Sedona session as for vector (KryoSerializer + SedonaKryoRegistrator). Add the raster JAR to the classpath:

```python
config = (
    SedonaContext.builder()
    .config("spark.jars.packages", 
            "org.apache.sedona:sedona-spark-3.5_2.12:1.5.1,"
            "org.datasyslab:geotools-wrapper:1.5.1-28.2")
    .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
    .config("spark.kryo.registrator", "org.apache.sedona.core.serde.SedonaKryoRegistrator")
    .getOrCreate()
)
sedona = SedonaContext.create(config)
```

Sedona's raster ops require the GeoTools wrapper — it provides format readers (GeoTIFF, NetCDF, etc.) under the hood.

## Read raster

```python
df = sedona.read.format("binaryFile").load("s3://bucket/landsat/*.tif")
df = df.withColumn("rast", expr("RS_FromGeoTiff(content)"))
df = df.select("path", "rast")
```

`binaryFile` reads each file as a row with `content` (binary) and `path` columns. `RS_FromGeoTiff` parses the binary into a Sedona raster object.

For Cloud-Optimized GeoTIFFs (COG), reads stream the relevant byte ranges — efficient for large files.

## Raster operations

```sql
-- Get a pixel value at a point
SELECT path, RS_Value(rast, ST_Point(-98, 30), 1) AS pixel_val
FROM rasters

-- Compute statistics over a polygon
SELECT
    path,
    RS_ZonalStats(rast, polygon, 1, 'mean') AS mean_val,
    RS_ZonalStats(rast, polygon, 1, 'sum') AS sum_val
FROM rasters JOIN polygons ON ST_Intersects(RS_Envelope(rast), polygon)

-- Clip raster to polygon
SELECT path, RS_Clip(rast, polygon) AS clipped
FROM rasters JOIN polygons ON ST_Intersects(RS_Envelope(rast), polygon)
```

`RS_*` is the raster function namespace, parallel to `ST_*` for vector.

## Vector × raster join

The common pattern: compute pixel statistics for each polygon in a vector dataset.

```python
result = sedona.sql("""
    SELECT 
        c.geoid,
        AVG(RS_ZonalStats(r.rast, c.geom, 1, 'mean')) AS avg_ndvi
    FROM rasters r
    JOIN counties c
    ON ST_Intersects(RS_Envelope(r.rast), c.geom)
    GROUP BY c.geoid
""")
```

Sedona's optimizer handles the spatial intersect using each raster's bounding box envelope.

## Pitfalls

### CRS

Rasters carry CRS in their metadata. Vector CRS must match (or you must transform one):

```sql
SELECT *, RS_Value(rast, ST_Transform(point, 'EPSG:4326', RS_SRID(rast)), 1) AS val
FROM rasters JOIN points ON ST_Intersects(RS_Envelope(rast), ST_Transform(point, 'EPSG:4326', RS_SRID(rast)))
```

Verbose; better to project all sides to a common CRS before the join:

```python
counties_5070 = counties.withColumn("geom", expr("ST_Transform(geom, 'EPSG:4326', 'EPSG:5070')"))
# Pre-process rasters to EPSG:5070 with gdalwarp before ingest
```

### Memory

Each raster cell is a row. A 10000×10000 pixel image is 100M rows if exploded. Don't explode unless you have to:

- For zonal statistics, use `RS_ZonalStats` (stays at the polygon level).
- For pixel-level analysis, use `RS_PixelAsPoints` only when necessary, and limit by polygon first.

### File size and broadcast

If your vector side is small (< 100 polygons), broadcast it. Otherwise raster reads happen per-polygon-per-raster, which is expensive.

```python
result = sedona.sql("""
    SELECT c.geoid, AVG(RS_ZonalStats(r.rast, c.geom, 1, 'mean')) AS avg_ndvi
    FROM rasters r
    JOIN /*+ BROADCAST(c) */ counties c ON ST_Intersects(RS_Envelope(r.rast), c.geom)
    GROUP BY c.geoid
""")
```

Note: Sedona doesn't always honor the BROADCAST hint for spatial joins; explicit `broadcast()` in the DataFrame API is more reliable.

## Alternative: pre-aggregate with rasterio + dask

For large raster pipelines where the vector side is small, often faster to:

1. Use `rasterio` + `dask.array` to compute zonal statistics at single-node scale.
2. Write the per-polygon result as a small DataFrame.
3. Skip Spark entirely.

Sedona raster shines when the *raster-side* is huge and you need cluster-distributed processing.

## Output

```sql
SELECT path, RS_AsGeoTiff(rast) AS out_tif FROM rasters
```

Or write the per-polygon result as a regular DataFrame:

```python
result.write.format("parquet").save("s3://output/zonal_stats.parquet")
```

## Raster function reference

- Sedona docs: https://sedona.apache.org/latest-snapshot/api/sql/Raster-loader/

The function set is smaller than `ST_*` (raster is newer in Sedona) — check what's available before assuming.

## Honest assessment

Sedona raster works but isn't yet as battle-tested as the vector side. For Siege work in 2026:

- **Use it when** vector ops are already in Sedona and you need to add raster cross-cutting at scale.
- **Skip it when** raster is the only spatial work — `xarray` + `dask` or `rio-tiler` are more mature.
- **Avoid for now** as the *primary* raster path in a new pipeline; revisit as Sedona raster matures.
