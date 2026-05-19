# `geometry` vs `geography` + SRID Hygiene

## Decision rule

| Type | Use when | Don't use when |
|---|---|---|
| `geometry(Type, SRID)` | 99% of cases. You know your CRS. You'll project to a planar CRS (e.g. EPSG:5070 for the continental US, UTM for local) for area/distance work. | Your data spans the globe and you need accurate great-circle distance without picking projections. |
| `geography(Type, 4326)` | True great-circle distance over long distances. Global datasets where projection choice is itself the problem. | High-volume area work; complex polygon clipping; anything where the per-row spheroid math cost matters. |

`geography` is *not* a "more accurate version of geometry." It's a different coordinate space (spheroidal vs planar) with different operators and a different cost model. Pick at the column level and stick with it.

## SRID hygiene — what to enforce

### 1. Always declare SRID at column creation

```sql
-- BAD — implicit SRID 0
CREATE TABLE features (id SERIAL, geom geometry);

-- GOOD — explicit type and SRID
CREATE TABLE features (
    id SERIAL,
    geom geometry(Point, 4326)
);
```

The typed declaration adds a constraint: any insert with the wrong SRID errors at write time, not silently at query time.

### 2. Validate SRID on ingest

If your data source is mixed (CSVs from multiple producers, shapefiles with `.prj` files of unknown providence):

```sql
-- After bulk load, find anything with the wrong SRID
SELECT id, ST_SRID(geom) AS actual_srid
FROM features
WHERE ST_SRID(geom) != 4326
LIMIT 20;
```

Then `ST_SetSRID` for known-correct projections, or `ST_Transform` if you need to reproject:

```sql
-- The data was already in 4326 but came in as SRID 0 (someone forgot)
UPDATE features SET geom = ST_SetSRID(geom, 4326)
WHERE ST_SRID(geom) = 0;

-- The data was in NAD83 (4269); we want WGS84
UPDATE features SET geom = ST_Transform(ST_SetSRID(geom, 4269), 4326)
WHERE ST_SRID(geom) = 4269;
```

`ST_SetSRID` *labels* (no coordinate change). `ST_Transform` *reprojects* (coordinates change). Confusing them silently corrupts data.

### 3. Store in 4326, compute in projected

Standard pattern:

- **Storage:** EPSG:4326 (lossless interchange, every tool understands it).
- **Computation:** project on demand to an equal-area or equal-distance CRS appropriate to the operation.

```sql
-- Area in square meters (continental US — Albers Equal Area)
SELECT id, ST_Area(ST_Transform(geom, 5070)) AS area_m2 FROM districts;

-- Distance in meters (local — UTM zone)
SELECT a.id, b.id, ST_Distance(ST_Transform(a.geom, 32614), ST_Transform(b.geom, 32614)) AS dist_m
FROM places a JOIN places b ON a.id < b.id;
```

For **performance-critical** distance work, materialize the projected geometry as a column and index it (see [`indexing-strategies.md`](indexing-strategies.md)). Per-query `ST_Transform` is index-blocking.

## Common SRID choices

| EPSG | What | When |
|---|---|---|
| 4326 | WGS 84 (lat/lng) | Storage, web mapping, GeoJSON, Mapbox |
| 3857 | Web Mercator | Tile rendering, only for visualization — distorted distances |
| 5070 | NAD83 / Conus Albers Equal Area | Continental US area calculations |
| 26915 | NAD83 / UTM zone 15N | Local distance calculations (Texas, etc.) — pick zone for your area |
| 4269 | NAD83 (lat/lng) | US federal data files; convert to 4326 for interop |

## Why `geography` exists at all

`geography(Point, 4326)` lets you write:

```sql
SELECT ST_Distance(a.geog, b.geog) AS meters_great_circle
FROM places a JOIN places b ON a.id < b.id;
```

…and get true great-circle distance in meters without thinking about projections. That's the entire feature.

Cost: every operation pays the spheroidal math overhead. For a once-a-day query, fine. For a high-volume API, materialize a projected `geometry` column and use `ST_Distance` on it.

## When to mix — almost never

Casting `geometry::geography` per row blocks the spatial index and pays the conversion cost on every comparison. If you find yourself doing this:

```sql
-- BAD — per-row cast
SELECT * FROM features WHERE ST_DWithin(geom::geography, $1::geography, 1000);
```

Either:
- Add a `geog` column populated once (`ALTER TABLE ... ADD COLUMN geog geography(Point, 4326)`) and index it, or
- Use the planar geometry with a projected CRS for the distance: `ST_DWithin(ST_Transform(geom, 32614), ST_Transform($1, 32614), 1000)` — and store the projected geometry too if this is hot.

## Pitfall: signed vs unsigned distances

`ST_Distance` is always non-negative. If you need *signed* distance (point-on-which-side-of-line, "is this inside or outside the polygon by how much"), use `ST_DistanceSphere` for spheroidal cases or `ST_Distance(point, polygon)` combined with `ST_Within(point, polygon)` to determine sign.
