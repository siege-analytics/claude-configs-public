# Principle: CRS is Meaning, Not Annotation

A coordinate is a number with no relationship to physical space until it has an SRID. The SRID is what turns `(-98, 30)` from "two numbers" into "longitude -98°, latitude 30° on the WGS 84 ellipsoid."

This is the most-violated and most-corruptive principle in spatial work. Every other principle assumes CRS hygiene.

## The principle, three statements

1. **A geometry without an SRID is meaningless.** Operations on it return numbers, but those numbers don't refer to anything physical.
2. **Operations on geometries in different CRSs return wrong results.** Predicates may silently miss; measurements come back in mixed units; spatial joins drop matches without warning.
3. **Project before measuring.** Distance, area, length on lat/lng coordinates return values in degrees. Always project to a meter-based CRS first.

## Per-engine implementation

### PostGIS

```sql
-- Always type the column with an SRID
CREATE TABLE features (
    id BIGSERIAL,
    geom geometry(Point, 4326)  -- type AND SRID
);

-- Validate at ingest
SELECT id FROM features WHERE ST_SRID(geom) != 4326;  -- should be empty

-- Project for measurement
SELECT ST_Area(ST_Transform(geom, 5070)) AS area_m2 FROM districts;
SELECT ST_Distance(
    ST_Transform(a.geom, 5070),
    ST_Transform(b.geom, 5070)
) AS dist_m FROM places a JOIN places b ON a.id < b.id;
```

For repeated measurement work, materialize a projected column with its own GIST index.

### GeoPandas

```python
import geopandas as gpd
from siege_utilities.geo.crs import set_default_crs, reproject_if_needed

set_default_crs("EPSG:4326")  # session-wide default

# Always check CRS at boundary
gdf = gpd.read_file("source.shp")
if gdf.crs is None:
    raise ValueError("Source has no CRS — refusing to proceed")
gdf = reproject_if_needed(gdf, "EPSG:4326")

# Project for measurement
gdf_5070 = gdf.to_crs("EPSG:5070")
gdf_5070["area_m2"] = gdf_5070.geometry.area  # square meters
```

### Sedona

```python
df = sedona.read.format("geoparquet").load("s3://bucket/data.parquet")
# Sedona doesn't store SRID in schema — track via column name
df = df.withColumn("geom_4326", expr("ST_GeomFromWKB(geom_wkb)"))
df = df.withColumn("geom_5070", expr("ST_Transform(geom_4326, 'EPSG:4326', 'EPSG:5070')"))

result = sedona.sql("""
    SELECT id, ST_Area(geom_5070) AS area_m2 FROM df
""")
```

Sedona's geometry type doesn't carry CRS. Compensate with column naming; see [`name-by-srid.md`](name-by-srid.md).

### DuckDB-spatial

```python
con.execute("""
    SELECT
        id,
        ST_Area(ST_Transform(geom, 'EPSG:4326', 'EPSG:5070')) AS area_m2
    FROM 'features.parquet'
""")
```

DuckDB's GEOMETRY type also doesn't carry SRID. Same compensation: track via column naming.

## Why violations are silent

Unlike a SQL syntax error, CRS violations don't raise:

- `ST_Distance(point_4326, point_4326)` returns degrees — a small positive number that *looks* reasonable for "distance" but isn't meters.
- `ST_Area(polygon_4326)` returns square degrees — looks like an area; isn't square meters / acres / anything meaningful.
- A spatial join across mismatched SRIDs may return zero rows OR may silently reproject one side and become slow OR may error in some engines and silently pass in others.
- A 4326-stored geometry compared to a Web Mercator (3857) bounding box returns zero matches because the bounding-box numbers don't overlap.

The pipeline runs. The output looks plausible. The conclusions are wrong.

## Standard CRS choices

| EPSG | Name | Use for |
|---|---|---|
| 4326 | WGS 84 (lat/lng) | **Storage / interchange** — universal compatibility |
| 3857 | Web Mercator | **Tile rendering only** — distorted distances/areas; never compute on this |
| 5070 | NAD83 / Conus Albers Equal Area | **Continental US area calculations** |
| 26915 | NAD83 / UTM zone 15N | Local distance work (Texas etc.); pick zone for region |
| 32614 | WGS 84 / UTM zone 14N | Global UTM equivalent |
| 4269 | NAD83 (lat/lng) | US federal source files; convert to 4326 for interop |
| 6933 | EASE-Grid 2.0 Global | Global equal-area calculations |

For other regions: https://epsg.io/

## Engine-specific gotchas that look universal but aren't

**Don't assume:** every engine handles CRS the same way.

| Engine | CRS storage | Implication |
|---|---|---|
| PostGIS `geometry` | SRID stored per-row | Type-constrained columns enforce; mixed SRIDs raise on operations |
| PostGIS `geography` | Always EPSG:4326 | Operations always spheroidal-meters |
| GeoPandas | `.crs` attribute on GeoDataFrame | Per-frame, not per-row; mixing within a frame is undefined |
| Shapely (raw) | None | Geometry has no CRS; track externally |
| Sedona | None | Track via column naming |
| DuckDB-spatial | None | Track via column naming |
| GeoParquet | CRS stored in column metadata | Round-trips cleanly through pyarrow / DuckDB / Sedona |

The GeoParquet metadata exception is why GeoParquet is the strongest interchange format — it's the only widely-supported file format that carries CRS *with* the binary geometry data.

## Defensive coding

Refuse to compute distance/area on lat/lng:

```python
def safe_area_m2(gdf, target_crs="EPSG:5070"):
    """Compute area in square meters with explicit projection."""
    if gdf.crs is None:
        raise ValueError("GeoDataFrame has no CRS — refusing to compute area")
    if str(gdf.crs).lower() in ("epsg:4326", "epsg:4269"):
        gdf = gdf.to_crs(target_crs)
    return gdf.geometry.area
```

Or in SQL:

```sql
CREATE OR REPLACE FUNCTION safe_area_m2(g geometry) RETURNS double precision AS $$
    SELECT CASE
        WHEN ST_SRID(g) IN (4326, 4269) THEN ST_Area(ST_Transform(g, 5070))
        WHEN ST_SRID(g) = 0 THEN -1.0  -- sentinel for "no SRID"
        ELSE ST_Area(g)  -- assume already projected
    END;
$$ LANGUAGE SQL IMMUTABLE PARALLEL SAFE;
```

These functions exist precisely because CRS errors are silent without them.

## Cross-links

- [`name-by-srid.md`](name-by-srid.md) — naming convention to track CRS across stages where engines don't store it
- [`../crs-decision-tree.md`](../crs-decision-tree.md) — operational decision tree for picking the right CRS per task
- [`validate-on-ingest.md`](validate-on-ingest.md) — pairs with this principle: validate CRS *and* geometry at the boundary
- [`../../coding/postgis/references/geometry-vs-geography.md`](../../../coding/postgis/references/geometry-vs-geography.md) — PostGIS-specific deep dive on the `geometry` vs `geography` choice
- [`../siege-utilities-spatial.md`](../siege-utilities-spatial.md) — `siege_utilities.geo.crs` helpers
