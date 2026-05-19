# Capability Tiers — Vocabulary

`siege_utilities` defines four tiers describing the spatial capabilities available in an environment. Adopt this vocabulary across the spatial skills so the conversation about "what can we use here?" is consistent.

## The tiers

```python
from siege_utilities.geo.capabilities import geo_capabilities
caps = geo_capabilities()
caps["tier"]
# "geo" | "geo-lite" | "geodjango" | "none"
```

| Tier | What's installed | Use this when |
|---|---|---|
| **`geo`** | Shapely + pyproj + GeoPandas + Fiona/pyogrio + rtree | Default development environment; full file format support; rich spatial join APIs. |
| **`geo-lite`** | Shapely + pyproj only (no GDAL) | Cloud functions, slim images, GDAL-less envs. Pure-Python ops work; file I/O constrained to GeoParquet (via pyarrow) and JSON. |
| **`geodjango`** | `geo` tier + Django + django.contrib.gis | Django app with GeoDjango ORM and PostGIS backend. |
| **`none`** | None of the above | Absolute minimal env. Only pandas + math + (optionally) DuckDB-spatial. |

## What you can do per tier

### `geo` (the default)

Everything. GeoPandas with `read_file` for shapefile/GPKG/GeoJSON/GeoParquet/everything. Spatial joins via `gpd.sjoin`. Areal interpolation via `tobler`. Choropleth via SU's `create_choropleth`. PostGIS via psycopg2 + GeoAlchemy2.

### `geodjango` (`geo` + Django GIS)

Everything in `geo` plus Django ORM-style PostGIS queries via SU's GeoDjango models.

### `geo-lite` (no GDAL)

What works:
- Reading GeoParquet (via pyarrow)
- Reading GeoJSON (built-in JSON parser + `shapely.geometry.shape`)
- Reading CSV with WKT or WKB columns
- Reprojection via `pyproj.Transformer`
- Spatial predicates (Shapely)
- Spatial join via `shapely.STRtree` (manual loop)
- H3 indexing (no GDAL)
- All SU functions tagged for `geo-lite`

What doesn't:
- Reading shapefile, GeoPackage, FlatGeobuf, KML directly via GeoPandas
- True polygon overlay (`gpd.overlay` requires GEOS via GeoPandas; some ops missing in lite)
- `tobler.area_interpolate` (needs full geo tier)

For the missing pieces:
- **DuckDB-spatial** bundles its own GDAL → can read shapefile / GPKG / KML via `ST_Read`
- **Pre-convert** files to GeoParquet on a `geo` machine; ship Parquet to `geo-lite` env
- **PostGIS** if you can stand up a tiny Postgres

### `none`

Only pandas + numpy + math. For spatial work, install at least Shapely (gets you to `geo-lite`) or DuckDB-spatial.

If the env truly has nothing spatial:
- Approximate distance: Haversine formula on lat/lng columns
- Approximate point-in-polygon: bounding box check + winding-number algorithm in pure Python
- Reproject: skip (use only Web Mercator approximations or live with lat/lng errors)

This tier is for emergencies only. Add Shapely or DuckDB-spatial.

## When the tier is wrong for the task

| Tier vs need | Resolution |
|---|---|
| Need full GeoPandas, env is `geo-lite` | Switch to DuckDB-spatial OR pre-convert files OR install GDAL (sometimes possible) |
| Need to read shapefile in `geo-lite` | DuckDB-spatial `ST_Read` |
| Need overlay in `geo-lite` | PostGIS or Sedona, or accept H3 approximation |
| Need PostGIS but env is `none` | Install psycopg2 (no GDAL needed for client); add Shapely if you'll process results in Python |
| Need Sedona but no Spark cluster | DuckDB-spatial as single-node SQL alternative |

## Detecting and branching

```python
from siege_utilities.geo.capabilities import geo_capabilities

caps = geo_capabilities()
TIER = caps["tier"]

def load_spatial_file(path):
    """Load spatial file with tier-aware fallback."""
    if TIER in ("geo", "geodjango"):
        import geopandas as gpd
        return gpd.read_file(path)
    elif TIER == "geo-lite":
        if path.endswith(".parquet"):
            import geopandas as gpd
            return gpd.read_parquet(path)
        elif path.endswith(".geojson"):
            import json, geopandas as gpd
            from shapely.geometry import shape
            with open(path) as f:
                data = json.load(f)
            records = [{"geometry": shape(f["geometry"]), **f["properties"]} for f in data["features"]]
            return gpd.GeoDataFrame(records, crs="EPSG:4326")
        else:
            # Fall through to DuckDB
            import duckdb
            con = duckdb.connect()
            con.load_extension("spatial")
            df = con.execute(f"SELECT * FROM ST_Read('{path}')").df()
            # Wrap in GeoDataFrame
            ...
    else:
        raise RuntimeError(f"Tier {TIER} cannot load {path}")
```

For library code that supports multiple tiers, isolate tier-specific paths in adapter functions.

## Pre-deployment checklist

- [ ] Target env's tier known? (`geo` for dev laptops; usually `geo-lite` for cloud functions)
- [ ] All file readers use formats supported in target tier?
- [ ] Tested in a container matching target tier?
- [ ] DuckDB-spatial declared as dependency if tier is `none`/`geo-lite` and you need legacy formats?

## Pending SU upstream work

- **SU-10:** document the tier vocabulary in user-facing README. Until that lands, this file is the canonical reference.
