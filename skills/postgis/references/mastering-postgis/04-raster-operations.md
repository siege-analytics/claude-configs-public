# Ch 4 — Working with Raster Data

The book's raster chapter covers `postgis_raster`: loading rasters, organizing tiles, pixel operations, raster + vector cross-cutting. Largely current, with one major change: as of PostGIS 3.x, `postgis_raster` is its own extension you load explicitly.

## What changed since the book

```sql
CREATE EXTENSION postgis;
CREATE EXTENSION postgis_raster;  -- now required separately (PostGIS 3.x+)
```

In PostGIS 2.x (the book's era), `raster` was bundled with core. The split happened in 3.0. Otherwise, the API is essentially unchanged.

## When to use `postgis_raster`

The book treats Postgres-as-raster-store as a default. **Modern practice tiles raster outside the database** — Cloud-Optimized GeoTIFFs (COGs) on S3, with a STAC catalog for metadata. Postgres reads them via FDW or DuckDB-spatial bridges when needed.

Use `postgis_raster` when:
- Raster is small enough to fit in Postgres without operational pain (< ~10 GB total)
- You need transactional consistency between raster and vector (rare in civic work)
- You're integrating raster into existing PostGIS pipelines and the alternative is complex out-of-band tooling
- Pixel-level analytics happen in SQL alongside vector work

Don't use it when:
- Raster is large (> 100 GB) — serve from object storage instead
- Workload is read-mostly — COGs on S3 with `rio-tiler` is faster + cheaper
- You're producing tiles for web maps — `pg_tileserv` produces vector tiles; raster tiles want a dedicated pipeline (TiTiler, GDAL2Tiles)

## Loading rasters

The book uses `raster2pgsql`:

```bash
raster2pgsql -s 4326 -I -t 100x100 -F input.tif public.elevation | psql -d mydb
```

Flags:
- `-s SRID` — same as `shp2pgsql`; required
- `-I` — create GIST index after load
- `-t 100x100` — tile size in pixels (smaller tiles = more rows but better query selectivity)
- `-F` — add a `filename` column (useful for multi-file raster collections)
- `-l 2,4,8` — generate overview/pyramid levels (faster low-zoom queries)

Tile size matters: too small = many tiny tiles (overhead); too large = each query reads more data than needed. 100x100 to 256x256 are common defaults. Match the typical query window.

## Raster operations

### `ST_Value` — pixel value at a point

```sql
SELECT
    p.id,
    ST_Value(r.rast, ST_Transform(p.geom, ST_SRID(r.rast))) AS elevation_m
FROM points p
JOIN elevation r ON ST_Intersects(r.rast, ST_Transform(p.geom, ST_SRID(r.rast)));
```

The CRS of the point and raster must match — `ST_Transform` the point to the raster's SRID (or vice versa, but transforming the smaller object is cheaper).

### `ST_Clip` — extract part of a raster by geometry

```sql
SELECT
    p.id,
    ST_Clip(r.rast, ST_Transform(p.geom, ST_SRID(r.rast))) AS clipped_rast
FROM polygons p
JOIN elevation r ON ST_Intersects(r.rast, ST_Transform(p.geom, ST_SRID(r.rast)));
```

Useful for "give me the raster within this county boundary."

### `ST_SummaryStats` — pixel statistics over a region

```sql
SELECT
    p.id,
    (ST_SummaryStats(ST_Clip(r.rast, ST_Transform(p.geom, ST_SRID(r.rast))))).*
FROM polygons p
JOIN elevation r ON ST_Intersects(r.rast, ST_Transform(p.geom, ST_SRID(r.rast)));
```

Returns count, sum, mean, stddev, min, max for the pixels within the polygon. The classic zonal-statistics operation.

### `ST_MapAlgebra` — pixel arithmetic

```sql
-- Compute NDVI from red and NIR bands
SELECT ST_MapAlgebra(
    nir_rast, 1,
    red_rast, 1,
    '([rast1.val] - [rast2.val]) / ([rast1.val] + [rast2.val])'
) AS ndvi_rast
FROM landsat;
```

Pixel-level math. The book covers this extensively. Modern alternative: pull rasters into Python with `rasterio` and use `numpy` directly — usually faster than `ST_MapAlgebra` for non-trivial expressions.

## Raster + vector workflows

The classic pattern: zonal statistics for each polygon.

```sql
-- Average elevation per county
SELECT
    c.geoid,
    AVG((ST_SummaryStats(ST_Clip(r.rast, ST_Transform(c.geom, ST_SRID(r.rast))))).mean) AS avg_elev_m
FROM counties c
JOIN elevation r ON ST_Intersects(r.rast, ST_Transform(c.geom, ST_SRID(r.rast)))
GROUP BY c.geoid;
```

This works but is verbose. For repeated zonal-stats workloads at scale, consider:

- **Sedona raster** — `RS_ZonalStats` is the same idea distributed across a Spark cluster (see [`coding/sedona/references/raster.md`](../../../sedona/references/raster.md))
- **`rasterio` + `rasterstats` Python** — for single-machine work, dramatically simpler than the SQL above

## Modern alternatives — when not to use postgis_raster

| Workload | Better tool |
|---|---|
| Serve raster tiles to a web map | TiTiler, GDAL2Tiles, MapServer |
| Read COGs from S3 in pipelines | `rasterio`, `xarray-io`, DuckDB-spatial |
| Time-series raster (Landsat, MODIS, weather) | `xarray` + Zarr / NetCDF; `STAC` for cataloging |
| Massive zonal-stats workloads | Sedona raster on a Spark cluster |
| Pixel-level ML training | `rasterio` + PyTorch / TensorFlow data loaders |

The book treats Postgres as the raster home. In 2026, Postgres is rarely the raster home. It's a *very-occasional* useful integration point when raster and vector live together.

## Pitfalls

- **Forgot `CREATE EXTENSION postgis_raster`** in PostGIS 3.x — `raster` type undefined.
- **Tile size mismatch** with query window — picking 1024x1024 when typical queries hit 100x100 areas reads 100x more data than needed.
- **No GIST index on rasters** — full table scan per query. `-I` flag at load time, or `CREATE INDEX ON elevation USING GIST (ST_ConvexHull(rast))`.
- **Mixed SRIDs** between raster and vector — must transform; transforming the larger object (raster) is expensive, so transform points/polygons to raster SRID.
- **Using `ST_Value` in a tight loop without joining on `ST_Intersects`** — scans every raster row for every point. Always pre-filter.
- **Not generating overviews (`-l`)** at load time — low-zoom queries (continental views) read full-resolution rasters. Slow.
- **Treating Postgres as the raster home** for large datasets — operational pain (backups, replication, vacuum on huge tables) exceeds value. Tile to S3 instead.

## Cross-links

- [`coding/sedona/references/raster.md`](../../../sedona/references/raster.md) — distributed raster on Spark
- [`../indexing-strategies.md`](../indexing-strategies.md) — index choices for raster columns
- [`../vacuuming-and-bloat.md`](../vacuuming-and-bloat.md) — raster tables get big fast; vacuum discipline matters

## Citation

Witkowski K., Chojnacki B., Mackiewicz M. *Mastering PostGIS*. Packt Publishing, 2017. Chapter 4 ("Working with Raster Data"). Paraphrase + commentary; not redistribution.
