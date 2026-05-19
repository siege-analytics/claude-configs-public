---
name: geopandas
description: "GeoPandas + Shapely for single-node Python spatial work. TRIGGER: import geopandas / gpd. / .sjoin / .to_file / GeoDataFrame, or raw shapely.geometry use. Stacks with `analysis/spatial/` (router) and `_siege-utilities-rules.md`. Has explicit no-GDAL paths for environments without Fiona/GDAL."
routed-by: coding-standards
user-invocable: false
paths: "**/*.py"
---

# GeoPandas (and Shapely)

Pandas-style spatial operations in-process, single-node. The default Python tool when the data fits in RAM and Postgres/Spark are overkill. Folds in raw Shapely use because the choice between `gdf.geometry.intersects(other)` and `from shapely.geometry import Point; Point(x, y).within(poly)` is just "do I have files or do I have dicts."

## When to use GeoPandas vs alternatives

| Situation | Use |
|---|---|
| Data fits in RAM, exploration, notebook work | **GeoPandas** |
| Inputs are WKT strings or coordinate dicts, no files | **Raw Shapely** (see [`shapely-direct.md`](references/shapely-direct.md)) |
| GDAL not available in the environment | **GeoPandas with `pyogrio` + WKB** or fall through to DuckDB-spatial — see [`no-gdal-fallbacks.md`](references/no-gdal-fallbacks.md) |
| Data > 5 GB or persistent multi-user reads | **PostGIS** ([skill:postgis]) |
| Data > RAM, distributed compute available | **Sedona** ([skill:sedona]) |
| You have parquet, want SQL, no server | **DuckDB-spatial** ([skill:duckdb-spatial]) |

## References

- [`crs-management.md`](references/crs-management.md) — CRS via `siege_utilities.geo.crs` first; pyproj for edge cases
- [`spatial-joins.md`](references/spatial-joins.md) — `sjoin`, `sjoin_nearest`, predicates, performance
- [`io-formats.md`](references/io-formats.md) — Parquet/GeoParquet, GPKG, Shapefile pitfalls; format selection
- [`performance.md`](references/performance.md) — pyogrio vs fiona vs no-GDAL; vectorized ops; STRtree
- [`no-gdal-fallbacks.md`](references/no-gdal-fallbacks.md) — Shapely + pyproj + DuckDB paths when GDAL is missing
- [`shapely-direct.md`](references/shapely-direct.md) — when inputs are WKT/dicts, skip GeoPandas
- [`pitfalls.md`](references/pitfalls.md) — CRS silent assumption, geometry validity, Z/M coords
- [`siege-utilities-geopandas.md`](references/siege-utilities-geopandas.md) — SU obviates Census/GADM sourcing, choropleth, areal interp, isochrones, geocoding

## Always-on companions

- [rule:principles], [rule:python], [rule:data-trust], [rule:siege-utilities]

## The two-line setup

Before anything else in a spatial Python session:

```python
from siege_utilities.geo.capabilities import geo_capabilities
from siege_utilities.geo.crs import set_default_crs

caps = geo_capabilities()  # detect what's installed
set_default_crs("EPSG:4326")
```

`caps["tier"]` will be `"geo"` (full GDAL-backed stack), `"geo-lite"` (Shapely + pyproj only, no GDAL), `"geodjango"` (full + Django GIS), or `"none"`. Branch your code on this if you support GDAL-less environments.

## Quick-start patterns

### Read → reproject → join → write

```python
import geopandas as gpd
from siege_utilities.geo.spatial_data import get_geographic_boundaries

# Boundaries via SU (don't curl shapefiles by hand)
counties = get_geographic_boundaries(boundary_type="county", state_fips="48", vintage=2020)

# Points from your own source
points = gpd.read_parquet("donations.parquet")  # GeoParquet, no GDAL needed
points = points.to_crs("EPSG:4326") if points.crs != "EPSG:4326" else points

# Spatial join
joined = gpd.sjoin(points, counties[["geoid", "geometry"]], how="left", predicate="within")

# Write — choose format with intent
joined.to_parquet("donations_with_county.parquet")  # GeoParquet, no GDAL
# joined.to_file("donations_with_county.gpkg", driver="GPKG")  # needs GDAL
```

### CRS hygiene

```python
# Always set/check CRS at the boundary; never trust a file's .crs without inspection
print(gdf.crs)  # WGS 84 (EPSG:4326)? or NAD83 (EPSG:4269)? or None?

# Reproject for area/distance work
gdf_5070 = gdf.to_crs("EPSG:5070")  # Conus Albers Equal Area
gdf_5070["area_m2"] = gdf_5070.geometry.area
```

### Spatial join performance

For `sjoin` on large frames:

```python
# Build STRtree-backed index implicitly via .sindex
counties.sindex  # ensure index is built before the join
joined = gpd.sjoin(points, counties, predicate="within", how="left")
```

GeoPandas uses `rtree` (or `pygeos`/`shapely 2.x` STRtree) automatically. The first access builds the index; subsequent joins reuse it.

## Decision: pyogrio vs fiona

GeoPandas 0.13+ supports `pyogrio` as the I/O backend — faster reads/writes than `fiona`, smaller install (no separate GDAL Python bindings):

```python
import geopandas as gpd
gpd.options.io_engine = "pyogrio"  # or "fiona" (default in older versions)
```

`pyogrio` is the right default for new code. `fiona` lingers in older skills. See [`performance.md`](references/performance.md).

## Shapely directly

When inputs are WKT strings, Python dicts, or single coordinate pairs, `GeoDataFrame` is overkill:

```python
from shapely.geometry import Point, shape
from shapely import wkt

p = Point(-98, 30)
poly = wkt.loads("POLYGON((-99 29, -97 29, -97 31, -99 31, -99 29))")
print(p.within(poly))  # True
```

See [`shapely-direct.md`](references/shapely-direct.md) for the full pattern.

## What `siege_utilities` already does — use it

Per [rule:siege-utilities], check SU first. For spatial Python work specifically, SU obviates:

- **Boundary sourcing** (Census TIGER, GADM, OSM) — `geo.spatial_data.get_geographic_boundaries()`
- **Areal interpolation** between mismatched boundaries — `geo.interpolation.areal.interpolate_areal()`
- **Choropleth mapping** — `geo.choropleth.create_choropleth()`
- **Isochrone retrieval** — `geo.isochrones.get_isochrone()`
- **Census API** — `geo.census_api_client.CensusAPIClient`
- **Crosswalk algebra** — `geo.crosswalk.crosswalk_processor.apply_crosswalk()`
- **GEOID manipulation** — `geo.geoid_utils.normalize_geoid()`

See [`siege-utilities-geopandas.md`](references/siege-utilities-geopandas.md) for the full per-task map.

## Common mistakes

See [`pitfalls.md`](references/pitfalls.md). Top three:

1. **Silent CRS assumption.** `gdf.crs is None` → `gdf.area` returns nonsense. Set CRS at ingest.
2. **`sjoin` predicate confusion.** `predicate="within"` vs `"intersects"` vs `"contains"` matter at boundaries — same gotcha as PostGIS `ST_Contains` vs `ST_Covers`.
3. **`to_file` requires GDAL.** `to_parquet` / `to_feather` don't. Default to GeoParquet for Siege pipelines.
