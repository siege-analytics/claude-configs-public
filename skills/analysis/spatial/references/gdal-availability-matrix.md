# GDAL Availability Matrix

Which spatial paths work, per engine, when GDAL is or isn't available. Adopt SU's tier vocabulary (`geo` / `geo-lite` / `geodjango` / `none`) to classify environments.

## Tier definitions (from `siege_utilities`)

```python
from siege_utilities.geo.capabilities import geo_capabilities

caps = geo_capabilities()
caps["tier"]
# "geo"        → full stack: Shapely + pyproj + GeoPandas + Fiona + Rtree
# "geo-lite"   → Shapely + pyproj only (no GDAL)
# "geodjango"  → "geo" + Django GIS
# "none"       → none of the above
```

| Tier | What's installed | Implications |
|---|---|---|
| `geo` | Shapely, pyproj, GeoPandas, Fiona/pyogrio, rtree | Full GeoPandas-style spatial stack. All file formats readable. |
| `geo-lite` | Shapely, pyproj | Pure-Python; no GDAL-dependent file readers. GeoParquet via pyarrow still works. |
| `geodjango` | `geo` tier + Django + django.contrib.gis | Adds GeoDjango ORM for PostGIS-backed Django apps. |
| `none` | Neither | Fall back to pandas + math + DuckDB-spatial. |

DuckDB and Sedona don't fit this tier vocabulary cleanly — they bundle their own spatial libs (DuckDB extension binary; JVM-side GEOS for Sedona) and aren't reflected in `caps`. Check independently with `caps["duckdb"]` and `caps["sedona"]`.

## Operations × engines × GDAL

| Operation | PostGIS | GeoPandas (geo) | GeoPandas (geo-lite) | DuckDB-spatial | Sedona |
|---|---|---|---|---|---|
| Read Shapefile | ✓ via `shp2pgsql` | ✓ | ✗ | ✓ via `ST_Read` (bundled GDAL) | ✓ via JAR |
| Read GeoPackage | ✓ via `ogr2ogr` | ✓ | ✗ | ✓ via `ST_Read` | ✓ via JAR |
| Read GeoJSON | ✓ | ✓ | ✓ (manual JSON parse + Shapely) | ✓ | ✓ |
| Read GeoParquet | n/a | ✓ | ✓ (pyarrow only) | ✓ | ✓ |
| Read CSV + WKT | ✓ | ✓ | ✓ | ✓ | ✓ |
| Write GeoParquet | n/a | ✓ | ✓ (pyarrow only) | ✓ | ✓ |
| Write Shapefile | ✓ | ✓ | ✗ | ✓ via `COPY` + GDAL bundled | ✓ via JAR |
| Spatial join | ✓ ST_Within | ✓ sjoin (rtree) | ✓ (Shapely STRtree manually) | ✓ ST_Within | ✓ ST_Within |
| Reproject | ✓ ST_Transform | ✓ to_crs | ✓ pyproj.Transformer | ✓ ST_Transform | ✓ ST_Transform |
| Areal interpolation | ✓ via SQL | ✓ tobler | ✗ approximate via H3 | ✗ approximate | ✗ approximate |
| Validity (`ST_MakeValid`) | ✓ | ✓ | ✓ Shapely make_valid | ✓ | ✓ |
| H3 indexing | ✓ via `h3-pg` | ✓ via `h3` (no GDAL) | ✓ via `h3` (no GDAL) | ✓ via `INSTALL h3` | ✗ (needs custom UDF) |

**Symbol key:** ✓ works, ✗ requires GDAL or specific stack not present in this tier.

## Decision: "I'm in environment X, what do I use?"

### AWS Lambda / Cloud Functions (no GDAL)

- **Tier likely:** `geo-lite` or `none`
- **Default:** **DuckDB-spatial** for any spatial work; bundle DuckDB in the deployment package.
- **For pre-converted Parquet only:** GeoPandas + pyarrow (geo-lite tier).

### Slim Docker images (`python:3.12-slim` etc.)

- **Tier likely:** `geo-lite`
- **Default:** **DuckDB-spatial**.
- Add Fiona/pyogrio if you need broader file format support, but every package install is overhead.

### Databricks (varies)

- **Tier:** depends on runtime. DBR 13+ has native spatial; older runtimes have Sedona via JAR.
- **Default:** Use `siege_utilities.geo.spatial_runtime.resolve_spatial_runtime_plan()` to pick.

### Developer laptop (full stack)

- **Tier:** `geo` or `geodjango`
- **Default:** GeoPandas for ad-hoc; PostGIS for shared / persistent; whatever the project uses for production.

### CI / test environments

- **Tier:** depends on CI image. Often `geo-lite` or `none`.
- **Default:** Use DuckDB-spatial in tests; mock the GDAL-dependent paths or skip them. Pre-convert any test fixtures to GeoParquet so the tests don't depend on GDAL.

## Branching code on tier

```python
from siege_utilities.geo.capabilities import geo_capabilities

caps = geo_capabilities()

if caps["tier"] in ("geo", "geodjango"):
    # Full GeoPandas path
    import geopandas as gpd
    gdf = gpd.read_file("source.shp")
elif caps["tier"] == "geo-lite":
    # Convert via DuckDB then load
    import duckdb
    con = duckdb.connect()
    con.load_extension("spatial")
    df = con.execute("SELECT * FROM ST_Read('source.shp')").df()
    # Convert to GeoDataFrame manually if needed
elif caps["tier"] == "none":
    # Cannot proceed without at least Shapely
    raise RuntimeError("Spatial work requires geo-lite tier or DuckDB at minimum")
```

For library code that supports multiple tiers, isolate the tier-specific paths in adapter functions and inject the engine.

## Pre-deployment checklist

Before deploying spatial code to a constrained environment:

- [ ] `geo_capabilities()` checked locally; tier matches expected target
- [ ] If target is `geo-lite` or `none`, all file-format readers use GeoParquet (not shapefile/GPKG)
- [ ] Areal interpolation replaced with H3 if not in `geo` tier
- [ ] Smoke test runs in a container matching the target environment
- [ ] DuckDB-spatial dependency declared if the env is `none`/`geo-lite`

## Pending SU upstream PRs

- **SU-1** — `read_geoparquet()`/`write_geoparquet()` without GDAL (DuckDB-WKB path). Closes the geo-lite gap most cleanly.
- **SU-6** — pyogrio fallback for Fiona. Smaller install footprint when Fiona isn't available.
- **SU-10** — document the capability tier vocabulary in user-facing README. Until this lands, this file is the canonical reference.
