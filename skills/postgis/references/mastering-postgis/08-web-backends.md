# Ch 8 — PostGIS as a Web Backend

The book covers Postgres as the data layer for web maps and APIs — pre-MVT, mostly via GeoJSON endpoints and pre-rendered tiles. The 2026 landscape is dramatically different: vector tiles via `pg_tileserv` + `ST_AsMVT` is now the default web pattern.

## What's changed since the book

Three major additions:

1. **`ST_AsMVT`** (PostGIS 2.4+, 2017 — released same year as book) — server-side vector tile generation
2. **`pg_tileserv`** (Crunchy Data, ~2019) — auto-publishing PostGIS tables as MVT tile services
3. **`pg_featureserv`** (Crunchy Data, ~2019) — auto-publishing as OGC Features API (REST GeoJSON)

Combined, these obviate most of the book's web-backend code. You no longer write Flask endpoints for GeoJSON; you point `pg_featureserv` at your database and it serves the API. You no longer pre-render tiles; you query with `ST_AsMVT` on demand.

## The MVT vector-tile pattern

### Server-side tile generation

```sql
WITH tile_features AS (
    SELECT
        id,
        name,
        category,
        ST_AsMVTGeom(
            ST_Transform(geom, 3857),               -- Web Mercator
            ST_TileEnvelope(z, x, y),              -- Tile bounds
            4096, 64, true                         -- Resolution / buffer / clip
        ) AS geom
    FROM features
    WHERE geom && ST_Transform(ST_TileEnvelope(z, x, y), ST_SRID(geom))
)
SELECT ST_AsMVT(tile_features, 'features') AS mvt
FROM tile_features
WHERE geom IS NOT NULL;
```

Returns a binary MVT blob. The browser-side library (Mapbox GL, MapLibre) decodes and renders.

Critical detail: **filter with `&&` against the tile envelope before `ST_AsMVTGeom`**. Without it, you process the whole table per tile. With it, only features intersecting the tile.

### `pg_tileserv` — automatic tile services

Install once, point at your Postgres:

```bash
docker run -e DATABASE_URL=postgres://user:pw@host/db -p 7800:7800 pramsey/pg_tileserv
```

Now every spatial table in the database is auto-published at:

```
http://localhost:7800/public.features/{z}/{x}/{y}.pbf
```

The MVT generation SQL above is what `pg_tileserv` runs internally. You don't write it.

For attribute filtering, parameters, custom queries, define a function:

```sql
CREATE OR REPLACE FUNCTION public.features_by_state(z integer, x integer, y integer, state text)
RETURNS bytea AS $$
DECLARE
    mvt bytea;
BEGIN
    SELECT ST_AsMVT(tile, 'features', 4096, 'geom') INTO mvt
    FROM (
        SELECT id, name, ST_AsMVTGeom(
            ST_Transform(geom, 3857),
            ST_TileEnvelope(z, x, y), 4096, 64, true
        ) AS geom
        FROM features
        WHERE state_fips = state
          AND geom && ST_Transform(ST_TileEnvelope(z, x, y), 4326)
    ) AS tile
    WHERE geom IS NOT NULL;

    RETURN mvt;
END;
$$ LANGUAGE plpgsql STABLE PARALLEL SAFE;
```

`pg_tileserv` exposes the function at:

```
http://localhost:7800/public.features_by_state/{z}/{x}/{y}.pbf?state=TX
```

## `pg_featureserv` — REST GeoJSON

For when the consumer wants OGC Features API (most modern GIS clients) instead of vector tiles:

```bash
docker run -e DATABASE_URL=postgres://user:pw@host/db -p 9000:9000 pramsey/pg_featureserv
```

Auto-publishes:

```
http://localhost:9000/collections/public.features/items?limit=100&filter=state_fips='48'
```

Returns GeoJSON. Pagination, filtering, bounding-box queries built in.

When to use vs `pg_tileserv`:
- **`pg_tileserv`** for web maps (Mapbox GL, MapLibre) where you render in the browser
- **`pg_featureserv`** for GIS clients (QGIS, ArcGIS), data scientists pulling sets, OGC-compliant integrations

Often both run side-by-side against the same database.

## Tile-rendering performance

The performance pattern for `ST_AsMVT`:

```sql
-- BAD: scans the whole table per tile
SELECT ST_AsMVT(tile, 'features')
FROM (SELECT ST_AsMVTGeom(geom, ST_TileEnvelope(z, x, y), 4096, 64, true) AS geom FROM features) tile;

-- GOOD: pre-filter
SELECT ST_AsMVT(tile, 'features')
FROM (
    SELECT ST_AsMVTGeom(geom, ST_TileEnvelope(z, x, y), 4096, 64, true) AS geom
    FROM features
    WHERE geom && ST_Transform(ST_TileEnvelope(z, x, y), 4326)
) tile
WHERE geom IS NOT NULL;
```

The `WHERE geom &&` uses GIST. Without it, every tile request is a full table scan.

For tables > 1M rows, also consider:

- **Materialized vector tile cache** — a separate table with pre-rendered MVTs at common zoom levels
- **Generalization at low zoom** — `ST_Simplify(geom, tolerance)` based on zoom; show coarser geometries when zoomed out
- **Database-level cache** — Redis or CDN in front of the tile service

`pg_tileserv` doesn't cache by default. Production deployments put a CDN in front.

## Generalization for zoom levels

A continental view shouldn't render every vertex of every county polygon. Generalize:

```sql
CREATE FUNCTION public.features_zoom(z integer, x integer, y integer)
RETURNS bytea AS $$
DECLARE
    tolerance double precision;
    mvt bytea;
BEGIN
    -- Tolerance scales with zoom
    tolerance := 78000.0 / (2 ^ z);  -- meters per pixel approximation

    SELECT ST_AsMVT(tile, 'features') INTO mvt
    FROM (
        SELECT
            id,
            name,
            ST_AsMVTGeom(
                ST_Simplify(ST_Transform(geom, 3857), tolerance),
                ST_TileEnvelope(z, x, y), 4096, 64, true
            ) AS geom
        FROM features
        WHERE geom && ST_Transform(ST_TileEnvelope(z, x, y), 4326)
    ) tile
    WHERE geom IS NOT NULL;

    RETURN mvt;
END;
$$ LANGUAGE plpgsql STABLE;
```

At z=0 (whole world), tolerance is large; at z=18 (street level), tolerance is essentially zero.

For repeated rendering, pre-compute a column of generalized geometry and serve that:

```sql
ALTER TABLE features ADD COLUMN geom_simplified_z8 geometry;
UPDATE features SET geom_simplified_z8 = ST_Simplify(geom, 305);  -- ~305m tolerance for z=8
CREATE INDEX features_geom_simp_idx ON features USING GIST (geom_simplified_z8);
```

Trades storage for query speed. Almost always worth it for tile-serving workloads.

## Modern alternatives — when not to use postgis_web

For very large or static datasets:

- **PMTiles** — static vector tile bundles served from S3. No database in the request path. Fastest possible web rendering for static data.
- **MapTiler / Mapbox / similar** — managed vector-tile services. No infrastructure.
- **Tegola** — Go-based tile server, alternative to `pg_tileserv` (handles non-Postgres sources too).

Postgres-as-tile-source is the right pattern when:
- Data updates frequently (live precinct results, real-time traffic)
- Filtering by user / parameter (per-state, per-category)
- The data already lives in Postgres for other reasons

Static reference layers (state boundaries, tract geometries) belong in PMTiles, not a tile server.

## Pitfalls

- **`ST_AsMVT` without `&&` filter** — every tile is a full table scan.
- **No GIST index on the geometry column** — same problem.
- **Using GeoJSON for high-volume tile rendering** — MVT is 5-10× smaller and renders 10-100× faster in the browser.
- **No CDN in front of the tile service** — every browser request hits Postgres.
- **Generalization tolerance too small at low zoom** — tiles are huge and slow; client struggles to render.
- **Generalization tolerance too large at high zoom** — features look chunky and wrong.
- **Mixing MVT and GeoJSON endpoints in one app** — code duplication; pick one per use case (web map vs API).
- **`pg_tileserv` exposed publicly without auth** — anyone can query any spatial table. Always front with auth + rate limiting.

## Cross-links

- [`05-exporting-data.md`](05-exporting-data.md) — `ST_AsMVT` covered there too; this file is the web-backend specifics
- [`07-plpgsql-programming.md`](07-plpgsql-programming.md) — `PARALLEL SAFE` annotation for tile functions
- [`../query-optimization.md`](../query-optimization.md) — query performance basics that matter here

## Citation

Witkowski K., Chojnacki B., Mackiewicz M. *Mastering PostGIS*. Packt Publishing, 2017. Chapter 8 ("PostGIS Backend for Web Apps"). Paraphrase + commentary; not redistribution.

`pg_tileserv` documentation: https://access.crunchydata.com/documentation/pg_tileserv/
`pg_featureserv` documentation: https://access.crunchydata.com/documentation/pg_featureserv/
PMTiles specification: https://protomaps.com/docs/pmtiles
