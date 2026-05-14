# CRS Decision Tree

Cross-engine projection rules. Same principles apply whether you're in PostGIS, GeoPandas, Sedona, or DuckDB-spatial.

## The two questions

For any spatial operation, ask:

1. **What units do I need the result in?** (degrees, meters, square meters, etc.)
2. **Is my data in a CRS where the operation makes sense in those units?**

If the answers don't align, project before computing.

## The decision tree

```
START: I'm about to compute something on geometry.
  │
  ├─ Is it a predicate (within / intersects / contains)?
  │     ├─ YES → CRS doesn't matter for the predicate result, but BOTH sides
  │     │       must share the same CRS. Reproject if mixed.
  │     └─ NO → continue (you're computing a measurement)
  │
  ├─ Is it area / distance / length / perimeter?
  │     │
  │     ├─ Are coordinates in lat/lng (EPSG:4326 or 4269)?
  │     │     │
  │     │     ├─ YES → reproject to a meter CRS first.
  │     │     │       Pick by region:
  │     │     │       - US national: EPSG:5070 (Conus Albers Equal Area)
  │     │     │       - US local: UTM zone for the area
  │     │     │       - Global: EPSG:6933 (EASE-Grid 2.0)
  │     │     │       OR use ST_Distance_Sphere / geography type for distance only
  │     │     │
  │     │     └─ NO → check the CRS units (probably meters; verify)
  │     │            Operation is meaningful as-is.
  │     │
  │     └─ END
  │
  ├─ Is it a transformation (buffer / centroid / convex hull)?
  │     │
  │     ├─ The geometric output is fine in any CRS, but the size of the
  │     │  buffer is in CRS units. ST_Buffer(geom_4326, 100) buffers by
  │     │  100 degrees — wrong if you want 100 meters.
  │     │
  │     └─ Reproject first; transform back if you need to store in 4326.
  │
  └─ END
```

## Standard CRS choices

| EPSG | Name | Use for |
|---|---|---|
| 4326 | WGS 84 (lat/lng) | **Storage / interchange.** Everyone reads it. |
| 3857 | Web Mercator | **Tile rendering only.** Areas/distances are distorted; never compute on this. |
| 5070 | NAD83 / Conus Albers Equal Area | **Continental US area calculations.** |
| 26915 | NAD83 / UTM zone 15N | Local distance work (Texas etc.). Pick the zone for your area. |
| 32614 | WGS 84 / UTM zone 14N | Global UTM equivalent of 26915. |
| 4269 | NAD83 (lat/lng) | **US federal source files.** Convert to 4326 for interop. |
| 6933 | WGS 84 / EASE-Grid 2.0 Global | Global equal-area calculations. |

For projections elsewhere: https://epsg.io/ (find by city/region).

## Cross-engine syntax

The same operation in each engine:

### PostGIS

```sql
SELECT ST_Area(ST_Transform(geom, 5070)) AS area_m2 FROM districts;
SELECT ST_Distance(
    ST_Transform(a.geom, 5070),
    ST_Transform(b.geom, 5070)
) FROM places a JOIN places b ON a.id < b.id;
```

### GeoPandas

```python
gdf_5070 = gdf.to_crs("EPSG:5070")
gdf_5070["area_m2"] = gdf_5070.geometry.area
```

### Sedona

```sql
SELECT
    ST_Area(ST_Transform(geom, 'EPSG:4326', 'EPSG:5070')) AS area_m2
FROM districts
```

### DuckDB-spatial

```sql
SELECT
    ST_Area(ST_Transform(geom, 'EPSG:4326', 'EPSG:5070')) AS area_m2
FROM 'districts.parquet'
```

## Storage convention

| Stage | CRS | Why |
|---|---|---|
| Storage / interchange | EPSG:4326 | Universal compatibility |
| Computation (area/distance/length) | Projected (5070, UTM, etc.) | Meaningful units |
| Display (web maps) | EPSG:3857 | What tiles use |
| Computed columns kept on disk | Whichever CRS the consumer needs | Don't re-project per query |

The naming convention `geom_<srid>` (e.g., `geom_4326`, `geom_5070`) makes the CRS visible in the column name. Across stages and engines, this catches the "I forgot to reproject" bug at column-name level.

## When to use `geography` (PostGIS) vs project-then-`geometry`

- `geography` type pays per-row spheroidal math cost. Fine for one-off queries; expensive in hot loops.
- For high-volume work, materialize a projected `geometry` column and index it.

DuckDB has `ST_Distance_Sphere` (spheroidal meters) without a separate type. Sedona has `ST_DistanceSphere` and `ST_DistanceSpheroid`. GeoPandas does not — project explicitly.

## CRS in the wild — what to expect

| Source | CRS you'll find |
|---|---|
| Census TIGER (current) | EPSG:4269 (NAD83) — convert to 4326 |
| OpenStreetMap | EPSG:4326 (WGS 84) |
| GADM | EPSG:4326 |
| Mapbox tiles | EPSG:3857 (Web Mercator) |
| State / local GIS files | varies — check the `.prj` |
| Random shapefile from the internet | might have no `.prj` — refuse to compute area/distance until you set it |

## Validating CRS at boundaries

Before any spatial operation in code you don't control:

```python
def assert_crs_for_distance(gdf, name="dataframe"):
    if gdf.crs is None:
        raise ValueError(f"{name} has no CRS — set it before distance/area work")
    if str(gdf.crs).lower() in ("epsg:4326", "epsg:4269"):
        raise ValueError(f"{name} is in lat/lng — reproject before distance/area work")
```

The general SU upstream PR candidate **SU-2** (`crs_distance_operations_safe`, `crs_to_projection_family`, `crs_is_cartesian`) would centralize this.

## Pitfalls — same across engines

- **Computing area in degrees** — returns a tiny number that looks reasonable. Always project first.
- **Mixing CRSs in a join predicate** — most engines either error or implicitly reproject one side (silently slow).
- **`set_crs` vs `to_crs`** in GeoPandas — `set_crs` labels without reprojecting. Used incorrectly = silent corruption.
- **`ST_Transform` on the indexed column in PostGIS** — blocks the index. Materialize the projected geometry as a separate column.
- **Coordinate axis order** — Shapely / GeoPandas / DuckDB / Sedona all use `(x, y) = (lng, lat)`. Source data may store `(lat, lng)`. Misorder = points in wrong hemisphere. Always verify.
- **CRS not stored in DuckDB GEOMETRY type** — track externally via column naming or sidecar.

## The general principle

Project deliberately, store in 4326, name columns by SRID, and refuse to compute area/distance on lat/lng. Consistency across engines comes from following the same CRS discipline regardless of which engine runs the query.
