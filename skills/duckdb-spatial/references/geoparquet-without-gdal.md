# GeoParquet Without GDAL — The DuckDB Path

This is the load-bearing pattern for spatial work in GDAL-less environments. If you remember nothing else from this skill, remember this file.

## The problem

You have spatial data. The environment doesn't have GDAL. GeoPandas's `to_file`/`read_file` for shapefile/GPKG/etc. requires GDAL. You can't install it (Lambda, slim image, locked-down corporate env).

GeoParquet is the answer: WKB-encoded geometry column in a Parquet file, with metadata describing CRS and geometry type. **Reading and writing it requires no GDAL.**

DuckDB does it best: `INSTALL spatial` bundles GEOS + PROJ + GDAL inside the extension binary, then provides full SQL ST_* operations on Parquet files entirely in-process.

## The minimal pattern

```python
import duckdb

con = duckdb.connect()
con.install_extension("spatial")
con.load_extension("spatial")

# Read GeoParquet
gdf = con.execute("SELECT * FROM 'features.parquet'").df()
# 'gdf' is a Pandas DataFrame; geometry column is WKB bytes (or GEOMETRY type)

# Write GeoParquet
con.execute("""
    COPY (
        SELECT id, name, ST_GeomFromWKB(geom_wkb) AS geom
        FROM source_table
    ) TO 'output.parquet' (FORMAT PARQUET)
""")
```

That's it. Works in any environment that can `pip install duckdb`.

## Reading WKB columns into Shapely

If you want Shapely geometry objects in Python (for further processing without DuckDB):

```python
from shapely import wkb

df = con.execute("SELECT id, ST_AsBinary(geom) AS geom_wkb FROM 'features.parquet'").df()
df["geometry"] = df["geom_wkb"].apply(wkb.loads)
```

`ST_AsBinary` returns the canonical WKB encoding. Shapely's `wkb.loads` is fast (C-backed).

## Round-trip via GeoPandas

Even when GeoPandas is available, DuckDB is the faster path for filter-then-load:

```python
import geopandas as gpd
import duckdb

con = duckdb.connect()
con.load_extension("spatial")

# Filter first in DuckDB, then convert
df = con.execute("""
    SELECT id, name, ST_AsBinary(geom) AS geom_wkb
    FROM 'huge_dataset.parquet'
    WHERE state = 'TX'
""").df()

from shapely import wkb
df["geometry"] = df["geom_wkb"].apply(wkb.loads)
gdf = gpd.GeoDataFrame(df.drop(columns="geom_wkb"), geometry="geometry", crs="EPSG:4326")
```

DuckDB's columnar Parquet read + predicate pushdown is faster than `gpd.read_parquet` + Pandas filter for selective queries.

## Writing GeoParquet from a CSV (no GDAL needed)

```python
con.execute("""
    COPY (
        SELECT *,
               ST_Point(longitude, latitude) AS geom
        FROM 'addresses.csv'
    ) TO 'addresses.parquet' (FORMAT PARQUET)
""")
```

The `geom` column is GEOMETRY-typed in the output. It can be read by other GeoParquet-compatible tools (GeoPandas, Sedona, BigQuery GIS) since DuckDB writes the GeoParquet metadata into the column properties.

## Reading shapefile / GeoPackage without GDAL on host

```python
df = con.execute("SELECT * FROM ST_Read('input.shp')").df()
df = con.execute("SELECT * FROM ST_Read('input.gpkg')").df()
df = con.execute("SELECT * FROM ST_Read('input.kml')").df()
```

`ST_Read` invokes the GDAL bundled inside DuckDB's spatial extension. The host system has no GDAL. This is the killer feature for legacy-format ingest in modern cloud environments.

## CRS handling

DuckDB doesn't currently store full CRS metadata in the GEOMETRY type — geometries are coordinate-only. Track CRS externally:

```python
# Convention: filename suffix or sidecar metadata
con.execute("""
    COPY (
        SELECT
            id,
            name,
            ST_Point(longitude, latitude) AS geom_4326  -- column name carries SRID
        FROM 'addresses.csv'
    ) TO 'addresses_4326.parquet' (FORMAT PARQUET)
""")
```

For reprojection inside DuckDB:

```sql
SELECT
    id,
    ST_Transform(geom_4326, 'EPSG:4326', 'EPSG:5070') AS geom_5070
FROM 'addresses_4326.parquet'
```

## What about S3 / cloud reads?

DuckDB does S3 directly:

```python
con.execute("INSTALL httpfs")
con.execute("LOAD httpfs")
con.execute("SET s3_region = 'us-east-1'")
con.execute("SET s3_access_key_id = '...'")
con.execute("SET s3_secret_access_key = '...'")

df = con.execute("""
    SELECT * FROM 's3://bucket/features.parquet'
    WHERE state = 'TX'
""").df()
```

Or use IAM-role credentials in cloud:

```python
con.execute("CREATE SECRET (TYPE S3, PROVIDER CREDENTIAL_CHAIN)")
df = con.execute("SELECT * FROM 's3://bucket/features.parquet' LIMIT 10").df()
```

Predicate pushdown to S3 means only the matching row groups are downloaded.

## Pure-pyarrow alternative (no DuckDB)

If you can't install DuckDB but have pyarrow + shapely:

```python
import pyarrow.parquet as pq
import pandas as pd
from shapely import wkb

table = pq.read_table("features.parquet")
df = table.to_pandas()

# If geometry is stored as WKB binary column
df["geometry"] = df["geometry"].apply(wkb.loads)

# Filter
df_tx = df[df["state"] == "TX"]
```

Slower than DuckDB (no SQL optimizer, no predicate pushdown without explicit filters), but works with just pyarrow + shapely. Good fallback when even DuckDB isn't available.

## The SU upstream PR opportunity (SU-1)

`siege_utilities` doesn't yet have `read_geoparquet()` / `write_geoparquet()` helpers using this DuckDB-WKB path. This is the highest-priority **SU-1** in the spatial-overhaul plan §10. Until it lands, write the inline DuckDB SQL above.

If you find yourself writing the `con.execute("COPY (...) TO ... FORMAT PARQUET")` pattern in a third Siege project, that's the trigger to file the SU PR (or check if it's been merged in the meantime).

## Mental model

For Siege spatial work in 2026, treat GeoParquet + DuckDB-spatial as the **default file format and query layer when GDAL is uncertain**. Falling back to GeoPandas+pyogrio is fine when GDAL is available; pre-converting to GeoParquet is the universal bridge.

| Format | GDAL needed | Recommendation |
|---|---|---|
| GeoParquet | **no** | **Default for storage** |
| Shapefile | yes (or DuckDB ST_Read) | Convert at ingest, don't keep |
| GeoPackage | yes (or DuckDB ST_Read) | Same — convert |
| GeoJSON | no (built-in JSON) | OK for small data; verbose at scale |
| FlatGeobuf | yes | Niche; convert to GeoParquet |
| CSV + WKT/lat-lng | no | OK for ingest; convert to GeoParquet for storage |
