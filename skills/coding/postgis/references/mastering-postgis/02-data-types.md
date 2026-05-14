# Ch 2 — Spatial Data Types

The book's chapter on "Structures that Make up Spatial Data" covers `geometry`, `geography`, `box*`, and `raster`. The conceptual treatment is timeless; the operational details are stable through PostGIS 3.x.

For the operational decision rules between `geometry` and `geography`, see [`../geometry-vs-geography.md`](../geometry-vs-geography.md). This file is the principle-level distillation.

## The mental model the book gets right

A **geometry** is coordinates plus a meaning. The meaning is the SRID — without it, a coordinate is a number with no relationship to physical space. The book hammers this point repeatedly, and it's the first thing every PostGIS user gets wrong.

```
Point(-98, 30)        ← could be anywhere
ST_SetSRID(Point(-98, 30), 4326)    ← longitude -98, latitude 30, on WGS 84
```

The SRID changes every spatial operation's interpretation. `ST_Distance` on EPSG:4326 returns degrees. On EPSG:5070, it returns meters. Same coordinates, different numbers, different meanings.

## The four type families

### `geometry` — planar coordinates in any CRS

The default. Every operation (`ST_Distance`, `ST_Area`, `ST_Buffer`) treats coordinates as planar (Euclidean) within the column's SRID.

Subtypes worth knowing:
- `geometry(Point, 4326)` — typed and SRID-constrained
- `geometry(MultiPolygon, 4326)` — for boundaries that may have islands or holes
- `geometry(LineString, 4326)` — for routes / streets
- `geometry(GeometryCollection, 4326)` — heterogeneous; rare in practice

**Always type the column.** `geometry geometry` (untyped) accepts anything; you'll discover months later that someone inserted points into your polygon column and `ST_Area` returns 0 for those rows.

### `geography` — coordinates on a spheroid

Stores in WGS 84 always. Operations use spheroidal math (great-circle distance, geodesic area). Returns meters / square meters always.

```sql
CREATE TABLE places (id BIGSERIAL, geog geography(Point, 4326));
SELECT ST_Distance(a.geog, b.geog) FROM places a JOIN places b ON a.id < b.id;
-- Returns meters
```

Cost: spheroidal math is per-row expensive. Use for one-off queries or where projection choice itself is the problem. Use a projected `geometry` column with index for hot loops.

The book's point: `geography` isn't "more accurate." It's a different coordinate space with a different cost model. Choose deliberately.

### `box2d` / `box3d` — bounding boxes

Lightweight rectangles used internally by GIST and the `&&` operator. Almost never directly instantiated by users; commonly returned from `ST_Envelope(geom)` and `ST_3DEnvelope(geom)`.

Useful for spatial pre-filters when you want bounding-box-only tests:

```sql
SELECT * FROM features WHERE geom && ST_MakeEnvelope(-100, 30, -97, 32, 4326);
```

`&&` returns true if bounding boxes intersect — much cheaper than `ST_Intersects` (which does the full predicate). Sometimes the right answer is "approximately intersects."

### `raster` — pixel grids

A `raster` is a tiled pixel grid with georeferencing. Lives in `postgis_raster`, a separate extension as of PostGIS 3.x.

```sql
CREATE EXTENSION postgis_raster;
CREATE TABLE elevation (id BIGSERIAL, rast raster);
```

For raster operations, see [`04-raster-operations.md`](04-raster-operations.md). For most Siege civic work, raster is rarely the right tool — vector polygons + Census tabular data carry the analysis.

## Dimensions — XY / XYZ / XYM / XYZM

PostGIS supports up to 4D coordinates:
- **XY** — normal 2D. Default.
- **XYZ** — adds Z (elevation, building height, depth).
- **XYM** — adds M (linear measure, mile-marker distance).
- **XYZM** — both.

Most operations work transparently in all dimensions, but a few quirks:

- `ST_Area`, `ST_Length` are 2D-only by default. Use `ST_3DLength` for 3D length.
- WKT for 3D: `'POINT Z (-98 30 100)'`. Standard WKT (`'POINT(-98 30)'`) is 2D.
- `ST_NDims(geom)` reports the dimension count.
- Stripping Z: `ST_Force2D(geom)`.

**The 3D footgun.** Some shapefile loaders silently add a Z dimension of 0 to all points. You won't notice until something downstream complains. Check on ingest:

```sql
SELECT DISTINCT ST_NDims(geom) FROM features;
-- If you see 3 when you expected 2, force 2D
UPDATE features SET geom = ST_Force2D(geom);
```

## SRIDs — the meaning layer

The book's strongest contribution: SRIDs aren't an annoyance, they're the *semantic layer* that turns numbers into geography.

### `spatial_ref_sys` — the catalog

PostGIS ships with the EPSG catalog in `spatial_ref_sys`. ~7000 SRIDs. Look one up:

```sql
SELECT srid, auth_name, srtext FROM spatial_ref_sys WHERE srid = 4326;
```

If you need a non-EPSG CRS (custom local grid, historical projection), insert it into `spatial_ref_sys` with a SRID > 900000 (the "user-defined" range).

### Choosing an SRID — the book's advice, current

For US work specifically, the book recommends:
- **Storage:** EPSG:4326 (WGS 84, lat/lng) for interoperability
- **Continental US measurements:** EPSG:5070 (Conus Albers Equal Area) for area; UTM zone for local distance
- **Outside US:** UTM by zone, or country-specific equal-area

This is still right. See [`../geometry-vs-geography.md`](../geometry-vs-geography.md) for the full SRID matrix.

### `Find_SRID` and `UpdateGeometrySRID`

Useful diagnostics:

```sql
-- What SRID does this column claim?
SELECT Find_SRID('public', 'features', 'geom');

-- Update SRID metadata without reprojecting (use when you trust the coordinates but the catalog is wrong)
SELECT UpdateGeometrySRID('public', 'features', 'geom', 4326);
```

`UpdateGeometrySRID` is `ST_SetSRID` for the whole column — same caveat: it labels, doesn't reproject.

## What the book is missing — modern type additions

### H3 hexagonal cells

Not a PostGIS type per se, but the `h3-pg` extension adds `h3index` columns and ST_*-style functions for hexagonal aggregation:

```sql
CREATE EXTENSION h3;
SELECT h3_lat_lng_to_cell(point::geography, 9) AS cell FROM places;
```

Excellent for binning at scale (hexagons aren't subject to the rectangular-grid distortion problem) and for approximate joins when full PostGIS overlay is overkill. See [`../indexing-strategies.md`](../indexing-strategies.md) and [`duckdb-spatial`](../../../../coding/duckdb-spatial/SKILL.md) (DuckDB also supports H3).

### `geomval` — value at a location

PostGIS 3.x added `geomval`, a record type pairing a geometry with a value. Useful for raster zonal statistics:

```sql
SELECT (ST_DumpAsPolygons(rast)).*
FROM rasters
LIMIT 5;
-- Returns geomval rows: (geom, val)
```

The book predates this. See [`04-raster-operations.md`](04-raster-operations.md).

### `topology` types

`postgis_topology` adds `topogeometry` and a structured topology layer. Covered separately in [`../topology.md`](../topology.md). Rarely the right tool — see that file.

## Pitfalls

- **Untyped `geometry` column** — accepts anything; mixed types break `ST_Area` etc. Always type: `geometry(Polygon, 4326)`.
- **SRID 0** — geometry has no projection metadata; spatial operations against indexed columns may not match. Validate on ingest.
- **Z dimension drift** — silent contamination from shapefile loaders. `ST_Force2D` to scrub.
- **`geometry::geography` casts in hot loops** — per-row spheroidal conversion is expensive. Materialize a `geography` column or pre-project `geometry`.
- **Mixing dimensions** — `ST_Distance(point_2d, point_3d)` returns 2D distance; the Z is silently dropped.
- **Custom SRID that pyproj doesn't understand** — PostGIS can use it via the `proj4text` column, but downstream tools (GeoPandas, QGIS, browsers) may fail. Convert to a standard EPSG before exporting.

## Cross-links

- [`../geometry-vs-geography.md`](../geometry-vs-geography.md) — full operational decision tree
- [`../pitfalls.md`](../pitfalls.md) — SRID mismatch debugging
- [`../indexing-strategies.md`](../indexing-strategies.md) — index choice by data type
- [`04-raster-operations.md`](04-raster-operations.md) — raster type details
