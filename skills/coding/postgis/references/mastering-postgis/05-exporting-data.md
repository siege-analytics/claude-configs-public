# Ch 5 — Exporting Spatial Data

The book covers `ST_AsText`, `ST_AsBinary`, `ST_AsGeoJSON`, and `ogr2ogr` for export. Modern PostGIS adds `ST_AsMVT` (vector tiles) and FDW-based read-only exposure.

## Format-conversion functions

The base set, all current:

```sql
SELECT ST_AsText(geom)         FROM features;  -- WKT
SELECT ST_AsBinary(geom)       FROM features;  -- WKB (binary)
SELECT ST_AsEWKT(geom)         FROM features;  -- WKT with embedded SRID
SELECT ST_AsEWKB(geom)         FROM features;  -- WKB with embedded SRID
SELECT ST_AsGeoJSON(geom)      FROM features;  -- GeoJSON
SELECT ST_AsKML(geom)          FROM features;  -- KML
SELECT ST_AsGML(geom)          FROM features;  -- GML
SELECT ST_AsX3D(geom)          FROM features;  -- 3D web format
SELECT ST_AsLatLonText(point)  FROM features;  -- "DD MM SS.S N/S, DD MM SS.S E/W"
```

For most modern work, **WKB and GeoJSON are the only two that matter**:
- **WKB** — efficient binary format for inter-system transfer (Postgres → DuckDB, Postgres → GeoPandas via `psycopg2`)
- **GeoJSON** — human-readable, widely supported, the standard for HTTP APIs

WKT is fine for debugging but verbose. KML and GML are largely legacy.

## EWKT vs WKT (a book-emphasized distinction)

PostGIS extends standard WKT with embedded SRID:

```sql
SELECT ST_AsText(geom)   FROM features;  -- "POINT(-98 30)" — no SRID
SELECT ST_AsEWKT(geom)   FROM features;  -- "SRID=4326;POINT(-98 30)" — with SRID
```

**EWKT round-trips losslessly through PostGIS.** Standard WKT loses the SRID. If you're piping geometry to a non-PostGIS system, decide:
- Target understands EWKT (DuckDB, Sedona) → use `ST_AsEWKT`
- Target wants standard WKT (most GIS tools) → use `ST_AsText` + carry SRID separately
- Target wants WKB → `ST_AsBinary` (also loses SRID; use `ST_AsEWKB` to preserve)

The book's strongest take: **don't lose the SRID at the export boundary.** Whatever happens downstream, the receiver needs to know what coordinates mean.

## ST_AsMVT — vector tiles (post-book; load-bearing)

The single most important addition since the book. Mapbox Vector Tiles (MVT) are the modern web-mapping standard:

```sql
WITH tile_features AS (
    SELECT
        id,
        name,
        ST_AsMVTGeom(
            ST_Transform(geom, 3857),               -- Web Mercator
            ST_TileEnvelope(z, x, y),              -- Tile bounding box
            4096,                                  -- Resolution (default)
            64,                                    -- Buffer (default)
            true                                   -- Clip geometries
        ) AS geom
    FROM features
    WHERE geom && ST_Transform(ST_TileEnvelope(z, x, y), 4326)
)
SELECT ST_AsMVT(tile_features, 'features') AS mvt
FROM tile_features
WHERE geom IS NOT NULL;
```

Returns a binary MVT blob ready to serve to a web client. Combined with `pg_tileserv` (see [`08-web-backends.md`](08-web-backends.md)), this is how modern PostGIS-backed web maps work.

Pre-MVT, the book era required pre-rendering tiles (raster) or generating client-side from GeoJSON (slow on large data). MVT solved both.

## Foreign Data Wrappers — read-only export

A different shape of "export" — letting other systems query Postgres without ingesting:

```sql
-- On the consumer side
CREATE EXTENSION postgres_fdw;

CREATE SERVER siege_pg FOREIGN DATA WRAPPER postgres_fdw
    OPTIONS (host 'pg.siege.internal', dbname 'spatial');

CREATE USER MAPPING FOR current_user SERVER siege_pg
    OPTIONS (user 'reader', password 'secret');

IMPORT FOREIGN SCHEMA public LIMIT TO (counties)
FROM SERVER siege_pg INTO local_schema;

-- Now query the remote table as if local
SELECT * FROM local_schema.counties WHERE state_fips = '48';
```

Filters push down across the network. For "we have authoritative spatial data in Postgres and N consumers need read access," FDW is the modern alternative to bulk export.

## Exporting to Parquet / GeoParquet

The book predates GeoParquet entirely. The modern path:

### Via DuckDB-spatial bridge

```python
import duckdb
con = duckdb.connect()
con.load_extension("spatial")
con.load_extension("postgres")

con.execute("ATTACH 'host=localhost dbname=spatial user=reader' AS pg (TYPE POSTGRES)")
con.execute("""
    COPY (SELECT * FROM pg.public.counties)
    TO 'counties.parquet' (FORMAT PARQUET)
""")
```

DuckDB reads from Postgres, writes GeoParquet. The Postgres geometry column round-trips through WKB. Single command.

### Via Python (psycopg2 + pyarrow)

```python
import psycopg2
import pandas as pd
import pyarrow.parquet as pq
from shapely import wkb

with psycopg2.connect(dsn) as conn:
    df = pd.read_sql("SELECT id, name, ST_AsBinary(geom) AS geom_wkb FROM features", conn)

df["geometry"] = df["geom_wkb"].apply(wkb.loads)
gdf = gpd.GeoDataFrame(df.drop(columns="geom_wkb"), geometry="geometry", crs="EPSG:4326")
gdf.to_parquet("features.parquet")
```

Slower than DuckDB but works without DuckDB available.

## `ogr2ogr` for everything else

For shapefile / GeoPackage / KML / etc. exports, `ogr2ogr` is still the universal tool:

```bash
ogr2ogr -f "ESRI Shapefile" output.shp \
        PG:"host=localhost dbname=spatial" \
        -sql "SELECT * FROM features WHERE state = 'TX'" \
        -t_srs EPSG:4326
```

Useful for handoff to GIS users on QGIS/ArcGIS who expect shapefile or GeoPackage.

## COPY for CSV-with-WKT export

```sql
\copy (SELECT id, name, ST_AsText(geom) AS geom_wkt FROM features) TO 'features.csv' WITH CSV HEADER;
```

For inspection / diff-friendly export. Slow at scale; not recommended for production handoff.

## Export decision matrix

| Target | Format | Tool |
|---|---|---|
| Web map (modern) | MVT | `ST_AsMVT` + `pg_tileserv` |
| Web API (REST) | GeoJSON | `ST_AsGeoJSON` + Flask/FastAPI |
| Other Postgres | (no transfer) | postgres_fdw |
| GeoPandas / Python pipeline | GeoParquet | DuckDB bridge or psycopg2 + pyarrow |
| Spark / Sedona | GeoParquet | DuckDB bridge |
| QGIS / ArcGIS user | GeoPackage or Shapefile | `ogr2ogr` |
| Cloud data lake | GeoParquet on S3 | DuckDB COPY |
| Inspection / diff | CSV with WKT | `\copy` |

The book's `ogr2ogr`-as-default answer covers the bottom-half rows. The top-half rows (web, FDW, GeoParquet pipelines) are post-book modern paths.

## Pitfalls

- **Losing SRID at export.** Use `ST_AsEWKT`/`ST_AsEWKB` if the consumer understands it; otherwise carry SRID in a sidecar.
- **`ST_AsGeoJSON` without `precision`** — default precision is 15 decimals, which is GPS-survey-equipment precision. For most uses, 6 decimals (≈ 10cm at the equator) is enough and produces 30% smaller output. Use `ST_AsGeoJSON(geom, 6)`.
- **Exporting raw geometry without transforming to a target CRS** — consumer may expect WGS 84 always.
- **Forgetting to filter before `ST_AsMVT`** — generating a tile from a 10M-row table is slow. Always pre-filter with `geom && ST_TileEnvelope(...)`.
- **`ogr2ogr` to shapefile** truncates column names to 10 chars, drops UTF-8. Use GPKG when the target tool supports it.

## Cross-links

- [`08-web-backends.md`](08-web-backends.md) — `pg_tileserv` + `ST_AsMVT` for serving tiles
- [`coding/duckdb-spatial/references/geoparquet-without-gdal.md`](../../../duckdb-spatial/references/geoparquet-without-gdal.md) — DuckDB as the GeoParquet bridge
- [`../siege-utilities-postgis.md`](../siege-utilities-postgis.md) — SU helpers for PostGIS round-trips

## Citation

Witkowski K., Chojnacki B., Mackiewicz M. *Mastering PostGIS*. Packt Publishing, 2017. Chapter 5 ("Exporting Spatial Data"). Paraphrase + commentary; not redistribution.
