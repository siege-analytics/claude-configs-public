---
name: duckdb-spatial
description: "DuckDB spatial extension — single-node SQL spatial queries on Parquet/CSV without Postgres or GDAL. TRIGGER: import duckdb with INSTALL spatial / LOAD spatial, ST_Read in DuckDB SQL, GeoParquet without GDAL, parquet → spatial-query workflows. Stacks with `coding/sql/`, `analysis/spatial/`, and `_siege-utilities-rules.md`."
routed-by: coding-standards
user-invocable: false
paths: "**/*.py,**/*.sql"
---

# DuckDB Spatial

DuckDB's `spatial` extension ships GEOS, GDAL, and PROJ inside a single in-process binary. It gives you SQL spatial queries on Parquet/CSV files without standing up a server, and — critically — it's the **strongest single tool for GDAL-less environments**. The DuckDB binary bundles its own spatial libraries; the host system doesn't need GDAL installed.

## When DuckDB-spatial is the right tool

| Situation | Use DuckDB-spatial |
|---|---|
| You have a Parquet/CSV with geometry, want SQL spatial queries, no Postgres available | ✓ |
| GDAL not available in the environment | ✓ — bundles its own |
| Single-node analysis on data 1 GB to ~100 GB | ✓ |
| You want a SQL idiom but data fits in one machine | ✓ |
| Cloud function / Lambda / Databricks notebook spatial work that doesn't justify Postgres | ✓ |

## When DuckDB-spatial is NOT the right tool

| Situation | Use instead |
|---|---|
| Persistent multi-user query workload | **PostGIS** ([`coding/postgis/`](../postgis/SKILL.md)) |
| Pandas-style operations, lots of joins with non-spatial dataframes | **GeoPandas** ([`coding/geopandas/`](../geopandas/SKILL.md)) |
| Data > one machine's RAM × 4 (DuckDB spills but eventually fails) | **Sedona on Spark** ([`coding/sedona/`](../sedona/SKILL.md)) |
| Spatial work is one step in a larger Spark DAG | **Sedona** (don't introduce a single-node bottleneck) |

## References

- [`when-to-use.md`](references/when-to-use.md) — vs PostGIS / vs GeoPandas / vs Sedona, decision criteria
- [`geoparquet-without-gdal.md`](references/geoparquet-without-gdal.md) — WKB-encoded geometry columns; the SU gap; how to read/write GeoParquet entirely without GDAL
- [`spatial-extension-cookbook.md`](references/spatial-extension-cookbook.md) — `INSTALL spatial`, `ST_Read`, `ST_AsWKB`, `ST_Distance_Sphere`, partition pruning
- [`pitfalls.md`](references/pitfalls.md) — extension version drift, WKB endianness, single-process ceiling
- [`siege-utilities-duckdb-spatial.md`](references/siege-utilities-duckdb-spatial.md) — SU's current DuckDB integration is thin (format conversion only); pending SU-1 / SU-7 / SU-9 will close most inline-SQL gaps

## Always-on companions

- [`coding/sql/`](../sql/SKILL.md) — DuckDB is SQL-first
- [`coding/python/`](../python/SKILL.md) — when scaffolding via `import duckdb`
- [`_principles-rules.md`](../../_principles-rules.md), [`_python-rules.md`](../../_python-rules.md), [`_data-trust-rules.md`](../../_data-trust-rules.md), [`_siege-utilities-rules.md`](../../_siege-utilities-rules.md)

## Setup

```python
import duckdb

con = duckdb.connect()  # in-memory; pass a path for persistence
con.install_extension("spatial")
con.load_extension("spatial")
```

That's it. No GDAL install, no Postgres, no Spark cluster. The extension auto-downloads on first install (~50 MB) and persists across `connect()` calls when using a file-backed database.

## Quick-start patterns

### Read GeoParquet, query, write

```python
import duckdb

con = duckdb.connect()
con.load_extension("spatial")  # already installed

result = con.execute("""
    SELECT
        county_geoid,
        COUNT(*) AS n_donations,
        SUM(amount) AS total_amount
    FROM read_parquet('s3://bucket/donations.parquet') d
    JOIN read_parquet('s3://bucket/counties.parquet') c
      ON ST_Within(d.geom, c.geom)
    GROUP BY county_geoid
""").df()  # returns pandas DataFrame
```

S3 reads work natively; no `boto3` boilerplate.

### CSV with lat/lng → GeoParquet

```python
con.execute("""
    COPY (
        SELECT *,
               ST_Point(longitude, latitude) AS geom
        FROM read_csv_auto('donations.csv')
    ) TO 'donations.parquet' (FORMAT PARQUET)
""")
```

Common pipeline shape — the `ST_Point` call is fast even for millions of rows.

### Spatial join with index

```python
result = con.execute("""
    -- DuckDB builds an in-memory R-tree implicitly when ST_Within is in the join condition
    SELECT *
    FROM points p
    JOIN counties c ON ST_Within(p.geom, c.geom)
""").df()
```

For very large joins, materialize an R-tree explicitly:

```python
con.execute("CREATE INDEX counties_geom_idx ON counties USING RTREE (geom)")
```

## Read shapefiles / GeoPackage / KML — DuckDB does it without GDAL host install

```python
con.execute("""
    SELECT *
    FROM ST_Read('s3://bucket/data.shp')
""").df()
```

`ST_Read` uses GDAL bundled inside the spatial extension. The host doesn't need GDAL installed. This is the **other** big GDAL-less win: legacy formats become readable in environments where you'd otherwise have to pre-convert.

## Pyspark-style data flow

For pandas-DataFrame in/out with DuckDB spatial in the middle:

```python
import pandas as pd
import geopandas as gpd

points_df = pd.read_csv("donations.csv")
counties_gdf = gpd.read_parquet("counties.parquet")

con.register("points_df", points_df)
con.register("counties_gdf", counties_gdf)

result = con.execute("""
    SELECT d.donation_id, c.county_geoid
    FROM points_df d
    JOIN counties_gdf c
      ON ST_Within(ST_Point(d.longitude, d.latitude), c.geom)
""").df()
```

DuckDB sees Pandas/GeoPandas DataFrames as queryable views without copying data. The result comes back as Pandas.

## What `siege_utilities` does and doesn't do

SU pulls `duckdb>=0.7.0` as a `performance` extra but currently uses it only for format conversion (`spatial_transformations.SpatialDataTransformer`) — *not* for the in-process query patterns above.

**SU obviates:** nothing yet on the spatial query side.

**SU upstream PR candidates** (pending the other agent's tickets):

- **SU-1:** `read_geoparquet()` / `write_geoparquet()` using DuckDB-WKB without GDAL — would wrap the GeoParquet patterns above behind a SU function.
- **SU-9:** DuckDB spatial-query helpers — `INSTALL spatial; LOAD spatial; ST_Read(...)` wrapper that returns a GeoDataFrame.
- **SU-7:** `csv_to_geoparquet(csv_path, lat_col, lon_col, output_path)` — the pipeline shape above as a one-liner.

Until they land, write the inline DuckDB SQL. See [`references/siege-utilities-duckdb-spatial.md`](references/siege-utilities-duckdb-spatial.md) for the full per-task interop map.

## Common mistakes

See [`pitfalls.md`](references/pitfalls.md). Top three:

1. **Forgot `LOAD spatial`** — `ST_*` functions undefined; "Catalog Error: Scalar Function ST_Within does not exist."
2. **Computing distance in degrees** — same gotcha as PostGIS; use `ST_Distance_Sphere` or project first.
3. **Single-process ceiling** — DuckDB is great up to ~100 GB on a beefy machine; beyond that, push to Sedona.
