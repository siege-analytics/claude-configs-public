# Ch 1 — Importing Spatial Data

The book's first chapter covers `shp2pgsql`, `ogr2ogr`, and COPY-based loads. All still current; the modern additions are FDW for "import without ingesting" and DuckDB's `ST_Read` for GDAL-less environments.

## The book's tools, still current

### `shp2pgsql` for shapefile → PostGIS

```bash
shp2pgsql -s 4326 -I -W LATIN1 source.shp public.features | psql -d mydb
```

Flags worth knowing:
- `-s SRID` — set the SRID. **Always specify**; default is 0 (no projection info).
- `-I` — create a GIST index on the geometry column after the load.
- `-W ENCODING` — source file encoding. Old shapefiles often `LATIN1`; modern ones `UTF8`.
- `-d` — drop and recreate the table. Use `-a` to append.
- `-D` — dump format (faster for large loads); pipes through `psql` straight to COPY.

For 10M+ row shapefiles, the dump format with `-D` is dramatically faster than the default insert format.

### `ogr2ogr` for everything else

```bash
ogr2ogr -f PostgreSQL "PG:dbname=mydb" source.gpkg \
        -nln features -nlt MULTIPOLYGON -lco GEOMETRY_NAME=geom \
        -t_srs EPSG:4326
```

Universal: shapefile, GeoPackage, GeoJSON, FlatGeobuf, KML, FileGDB, MapInfo, etc. The `ogr2ogr` Postgres driver writes via `INSERT` (slower than `COPY`) but handles every format.

For very large GPKG / GeoJSON files, convert to shapefile or use `-clipsrc` / `-progress` for sanity.

### COPY for CSV with WKT

```sql
CREATE TABLE features_staging (id BIGINT, geom_wkt TEXT, attrs JSONB);
\COPY features_staging FROM '/path/to/file.csv' WITH CSV HEADER;

INSERT INTO features (id, geom, attrs)
SELECT id, ST_GeomFromText(geom_wkt, 4326), attrs
FROM features_staging;

DROP TABLE features_staging;
```

For high-volume ingest, `COPY` is the fastest path. The two-step (staging table + INSERT) lets you parse the WKT in SQL and validate before promotion.

For CSVs with separate `lat`/`lng` columns:

```sql
INSERT INTO features (id, geom)
SELECT id, ST_SetSRID(ST_MakePoint(lng, lat), 4326)
FROM features_staging;
```

`ST_MakePoint(x, y)` not `(y, x)` — the axis-order trap.

### `psql \copy` for client-side loads

`\copy` (lowercase, no semicolon) is a `psql` command that reads from the *client* filesystem instead of the *server*. Useful when you don't have file access on the database host.

```
\copy features_staging FROM '/local/path/data.csv' WITH CSV HEADER;
```

The book uses `COPY` extensively; `\copy` is the same syntax with the client-vs-server distinction.

## What the book is missing — modern import paths

### Foreign Data Wrappers (FDW)

The book treats data import as a one-way ingestion. Modern PostGIS lets you query external data **without ingesting** via FDW:

```sql
CREATE EXTENSION postgres_fdw;

CREATE SERVER source_db FOREIGN DATA WRAPPER postgres_fdw
    OPTIONS (host 'remote.example.com', dbname 'sourcedb');

CREATE USER MAPPING FOR current_user SERVER source_db
    OPTIONS (user 'reader', password 'secret');

IMPORT FOREIGN SCHEMA public LIMIT TO (features) FROM SERVER source_db INTO local_schema;

-- Now query:
SELECT * FROM local_schema.features WHERE state = 'TX';
```

FDW pushes filters across the network, so `WHERE` clauses execute remotely. No ingestion, no staleness.

For Parquet on S3 (the modern data lake pattern):

```sql
CREATE EXTENSION parquet_s3_fdw;
-- ...similar setup...
SELECT * FROM external_features WHERE state = 'TX';
```

### DuckDB-spatial as ingestion gateway (GDAL-less envs)

Where `ogr2ogr` requires GDAL on the host, DuckDB-spatial bundles its own and can read shapefile / GPKG / KML / etc. then write Parquet, which Postgres can ingest via FDW or COPY:

```python
import duckdb
con = duckdb.connect()
con.load_extension("spatial")

con.execute("""
    COPY (SELECT * FROM ST_Read('input.shp')) TO 'output.parquet' (FORMAT PARQUET)
""")
```

Then in Postgres, ingest the Parquet via `parquet_s3_fdw` or COPY-from-Parquet (PG 17+).

See [skill:duckdb-spatial] for the GDAL-less path.

### siege_utilities for source-fetching

For Census TIGER, GADM, OSM data — don't `wget` shapefiles. `siege_utilities.geo.spatial_data.get_geographic_boundaries()` returns a GeoDataFrame ready to push to PostGIS via `gdf.to_postgis(...)`. See [`../siege-utilities-postgis.md`](../siege-utilities-postgis.md).

## The book's bulk-load advice — still current

- **Drop indexes before bulk inserts; recreate after.** GIST index updates per-insert kill ingest speed.
- **`UNLOGGED` table for staging.** Skips WAL; much faster. Promote with INSERT into the logged table.
- **Single transaction wraps the load.** All-or-nothing; rollback on failure.
- **`VACUUM (ANALYZE)` after the load.** Planner needs fresh stats; without it, every query plan is wrong for the next hour.

```sql
BEGIN;
CREATE UNLOGGED TABLE features_staging (LIKE features INCLUDING ALL);
\COPY features_staging FROM '/path/data.csv' WITH CSV HEADER;
INSERT INTO features SELECT * FROM features_staging;
DROP TABLE features_staging;
COMMIT;

VACUUM (ANALYZE, VERBOSE) features;
```

## What's stale — `ogr2ogr` for everything

The book treats `ogr2ogr` as the universal answer. In 2026, modern alternatives exist for specific cases:

| Source | Book's advice | Modern alternative |
|---|---|---|
| Shapefile | `shp2pgsql` or `ogr2ogr` | Either still fine. DuckDB-spatial if no GDAL. |
| GeoPackage | `ogr2ogr` | Same. DuckDB-spatial if no GDAL. |
| GeoJSON | `ogr2ogr` | DuckDB read + COPY-from-Parquet, or psycopg2 + `ST_GeomFromGeoJSON`. |
| GeoParquet | n/a | DuckDB → Parquet → FDW or COPY. The whole modern path. |
| Cloud-hosted | n/a | FDW (`parquet_s3_fdw`, `postgres_fdw`). |
| Census TIGER | manual `wget` + `shp2pgsql` | `siege_utilities.geo.spatial_data.get_geographic_boundaries()`. |

Use `ogr2ogr` when nothing else works — it's the universal fallback. Don't reach for it first.

## Pitfalls (the book's + modern additions)

- **Forgot `-s SRID`.** Default is 0; nothing matches in spatial joins.
- **Forgot `-I`.** Loaded data without index; first query takes hours.
- **Encoding mismatch.** Old US Census shapefiles often `LATIN1`; modern ones `UTF8`. Wrong flag → garbled attribute strings.
- **`COPY` from CSV with multi-line WKT.** WKT for a complex polygon can be huge; wrap in quotes and double up internal quotes per CSV spec.
- **Server-side `COPY` requires file access on the DB host.** Use `\copy` (psql client-side) when working through cloud-managed Postgres.
- **`ogr2ogr` + Postgres driver writes per-row.** For 10M+ rows, slow. Use COPY-based intermediate format (CSV with WKT) instead.
- **No staging table.** Bulk-loading directly into the production table with indexes intact = hours of index updates.

## Cross-links

- [skill:duckdb-spatial] — GDAL-less ingestion gateway
- [`../siege-utilities-postgis.md`](../siege-utilities-postgis.md) — boundary sourcing via SU
- [`../indexing-strategies.md`](../indexing-strategies.md) — when to create indexes during ingest
- [`../vacuuming-and-bloat.md`](../vacuuming-and-bloat.md) — why `VACUUM ANALYZE` after bulk loads matters
