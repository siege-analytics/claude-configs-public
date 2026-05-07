# GeoPandas I/O Formats

Format selection for spatial Python work. Defaults: GeoParquet for storage, GeoJSON for interchange.

## Format matrix

| Format | Extension | Reads needs | Writes needs | When to use |
|---|---|---|---|---|
| **GeoParquet** | `.parquet` | pyarrow (no GDAL) | pyarrow | **Default for Siege storage and pipelines.** Columnar, compressed, schema-stable, no GDAL. |
| **GeoJSON** | `.geojson`, `.json` | none (built-in) | none | Interchange, web APIs, small datasets. Verbose; large files OOM Pandas readers. |
| **GeoPackage** | `.gpkg` | GDAL (fiona/pyogrio) | GDAL | Multi-layer SQLite-based; good for desktop GIS handoff. |
| **Shapefile** | `.shp` (+ `.shx`, `.dbf`, `.prj`) | GDAL | GDAL | Legacy. Avoid for new work — column-name length limit (10 chars), no UTF-8 in attributes, multi-file. |
| **FlatGeobuf** | `.fgb` | GDAL | GDAL | Streaming, indexed format; useful for large mapping pipelines. |
| **CSV with WKT/WKB column** | `.csv` | none + Shapely WKT/WKB parser | manual | Easy debugging; no index; not for production storage. |
| **PostGIS** | (database) | psycopg2 + GeoAlchemy2 or pandas+sqlalchemy | same | Persistent, indexed, multi-user. See [skill:postgis]. |
| **Iceberg/Delta with geometry column** | (table format) | spark or polars | same | Lakehouse spatial. WKB-encoded columns. |

## GeoParquet — the default

```python
import geopandas as gpd

# Read
gdf = gpd.read_parquet("features.parquet")

# Write
gdf.to_parquet("features.parquet")

# Multiple files (Hive-style partitioning)
gdf.to_parquet("features/", partition_cols=["state"])

# From cloud
gdf = gpd.read_parquet("s3://bucket/features.parquet", storage_options={"key": "...", "secret": "..."})
```

GeoParquet (`.parquet` with WKB-encoded geometry column + GeoParquet metadata in column properties):

- No GDAL needed
- Columnar — selective reads of attribute columns are fast
- Compressed (Snappy by default; ZSTD for better ratio)
- Schema-stable across versions
- Round-trips through Polars, DuckDB, Spark/Sedona, BigQuery

The GeoParquet 1.0 spec is stable. Use it for any Siege pipeline that doesn't have a hard requirement for another format.

## GeoJSON

For HTTP APIs, web mapping, GeoJSON-shaped sources:

```python
gdf = gpd.read_file("places.geojson")  # uses pyogrio/fiona, but GeoJSON has a built-in fallback
gdf.to_file("places.geojson", driver="GeoJSON")
```

For small (< 100 MB) data without GDAL, you can hand-parse:

```python
import json
from shapely.geometry import shape
from siege_utilities.geo.crs import set_default_crs

with open("places.geojson") as f:
    data = json.load(f)

records = []
for feature in data["features"]:
    geom = shape(feature["geometry"])
    props = feature["properties"]
    records.append({"geometry": geom, **props})

import geopandas as gpd
gdf = gpd.GeoDataFrame(records, crs="EPSG:4326")  # GeoJSON is always 4326
```

This path requires only `shapely`, no GDAL/Fiona/pyogrio.

## Shapefile — when you have to

Inevitable for some sources (Census TIGER, state SOS files). Read, then immediately convert:

```python
gdf = gpd.read_file("tiger.shp")  # needs GDAL
gdf.to_parquet("tiger.parquet")   # save as GeoParquet for downstream
```

Don't keep shapefiles in pipelines. Convert at the boundary.

Pitfalls:
- Column names truncated to 10 chars on write.
- No UTF-8 by default — `encoding='utf-8'` reader option, but the original may be Latin-1.
- Multi-file: forgetting one of `.shx`/`.dbf`/`.prj` makes the file unusable. Carry as `.zip` or directory.
- `.prj` files with custom WKT can confuse pyproj. Set CRS explicitly after reading if needed.

## GeoPackage (GPKG)

Better than shapefile for handoff to QGIS/ArcGIS users:

```python
gdf.to_file("data.gpkg", driver="GPKG", layer="features")  # multi-layer support
gdf2 = gpd.read_file("data.gpkg", layer="features")
```

Single file, supports multiple layers, no column-name limit, UTF-8 native. Still needs GDAL.

## CSV with WKT — debug only

For inspection or quick handoff:

```python
gdf["geom_wkt"] = gdf.geometry.to_wkt()
gdf.drop(columns="geometry").to_csv("features.csv", index=False)

# Read back
import pandas as pd
from shapely import wkt
df = pd.read_csv("features.csv")
df["geometry"] = df["geom_wkt"].apply(wkt.loads)
gdf = gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")
```

Slow, no spatial index, large file size. Useful for `git diff` of small datasets.

## I/O performance

| Operation | GeoParquet | Shapefile (fiona) | Shapefile (pyogrio) | GPKG (pyogrio) | GeoJSON |
|---|---|---|---|---|---|
| Read 1M rows | ~2 s | ~30 s | ~5 s | ~6 s | ~20 s |
| Write 1M rows | ~3 s | ~45 s | ~7 s | ~8 s | ~30 s |
| File size (1M rows, simple geom) | ~80 MB | ~250 MB | ~250 MB | ~200 MB | ~400 MB |

(Order-of-magnitude; depends on geometry complexity.) GeoParquet wins consistently.

## Cloud I/O

```python
# Direct S3 read
gdf = gpd.read_parquet("s3://bucket/data.parquet", storage_options={...})

# With fsspec abstraction
import fsspec
with fsspec.open("s3://bucket/data.parquet", "rb") as f:
    gdf = gpd.read_parquet(f)
```

For partitioned datasets in cloud (Hive-style):

```python
gdf = gpd.read_parquet("s3://bucket/features/", filters=[("state", "=", "TX")])
```

`pyarrow` does predicate pushdown — only the matching partitions/files are read.

## What SU provides

- **Source readers** for Census/GADM/OSM boundaries return GeoDataFrames in EPSG:4326 — no I/O concern, just call `get_geographic_boundaries()`.
- **Format conversion** via `geo.spatial_transformations.SpatialDataTransformer.convert_format()` — supports shapefile, geojson, gpkg, kml, gml, wkt, wkb, postgis, duckdb.

What SU doesn't yet do (upstream PR candidates):
- **SU-1:** `read_geoparquet()` / `write_geoparquet()` using DuckDB-WKB without GDAL — major gap for GDAL-free environments.
- **SU-7:** `csv_to_geoparquet(csv_path, lat_col, lon_col)` convenience.

See [`siege-utilities-geopandas.md`](siege-utilities-geopandas.md) for the full SU map.
