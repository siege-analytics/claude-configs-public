# CRS Management in GeoPandas

CRS bugs are silent and corruptive. A `GeoDataFrame` with the wrong CRS won't error — it'll just give wrong areas, wrong distances, wrong joins.

## Lead with siege_utilities

```python
from siege_utilities.geo.crs import set_default_crs, get_default_crs, reproject_if_needed

set_default_crs("EPSG:4326")  # session-wide default for SU functions

# When loading a GeoDataFrame from a source you don't control:
gdf = reproject_if_needed(gdf, "EPSG:4326")
```

`reproject_if_needed` is idempotent — no-op if already in the target CRS, transforms otherwise. Cheaper than calling `to_crs` defensively.

## Standard CRS choices for Siege work

| EPSG | Name | Use for |
|---|---|---|
| 4326 | WGS 84 (lat/lng) | **Storage / interchange** — every tool reads it |
| 3857 | Web Mercator | Tile rendering only — distorted distances/areas |
| 5070 | NAD83 / Conus Albers Equal Area | **Continental US area calculations** |
| 26915 | NAD83 / UTM zone 15N | Local distance work (Texas) — pick zone for region |
| 4269 | NAD83 (lat/lng) | US federal source files; convert to 4326 for interop |
| 6933 | EASE-Grid 2.0 Global | Global equal-area calculations |

For projections elsewhere: https://epsg.io/ (find by city/region).

## Set CRS vs reproject

Two distinct operations, easy to confuse:

```python
# Set: label the CRS without changing coordinates (you trust the source coords)
gdf = gdf.set_crs("EPSG:4326")

# Reproject: transform coordinates from one CRS to another
gdf_5070 = gdf.to_crs("EPSG:5070")
```

Use `set_crs` only when the GeoDataFrame has no CRS (`gdf.crs is None`) but you know what it should be. Use `to_crs` when you need to actually transform.

`set_crs(allow_override=True)` overwrites an existing CRS without reprojecting — almost always wrong; if you think you need it, you actually wanted `to_crs`.

## Check before computing

Always verify CRS before area/distance/length:

```python
def safe_area_m2(gdf, target_crs="EPSG:5070"):
    """Compute area in square meters with explicit projection."""
    if gdf.crs is None:
        raise ValueError("GeoDataFrame has no CRS — refusing to compute area")
    if str(gdf.crs).lower() in ("epsg:4326", "epsg:4269"):
        # lat/lng — must project for meaningful area
        gdf = gdf.to_crs(target_crs)
    return gdf.geometry.area
```

For the general "is this CRS safe for distance/area work" question, see SU upstream PR candidate **SU-2** (`crs_distance_operations_safe(crs)`) — until then, the manual check above.

## Reading from sources with unreliable .crs

Shapefiles ship with a `.prj` file but it's often missing, wrong, or in a non-standard format:

```python
import geopandas as gpd

gdf = gpd.read_file("source.shp")
print(gdf.crs)  # might be None, might be wrong

# If you know it should be 4326 but the file lost its .prj:
gdf = gdf.set_crs("EPSG:4326")

# If it's in some custom projection the .prj names but pyproj can't parse:
gdf = gdf.set_crs("EPSG:32614", allow_override=True)  # UTM zone 14N
```

GeoJSON files are always WGS84 by spec; explicit `.crs` may still be missing — set to `EPSG:4326`.

GeoParquet files store CRS in column metadata; `gpd.read_parquet` reads it correctly. If a file has no metadata, the GeoSeries's `.crs` is None.

## Mixing CRS in one frame

Don't. GeoPandas allows it but operations are nondeterministic. If you have multiple sources in different CRSs, reproject each to a common CRS at the boundary.

## Reprojection cost

Per-row math, not free. For 10M+ row datasets, reproject once and cache:

```python
gdf_5070 = gdf.to_crs("EPSG:5070")
gdf_5070.to_parquet("cache/features_5070.parquet")
```

Subsequent runs skip the reprojection.

## Coordinate axis order — silent corruption risk

The lat/lng vs lng/lat question. GeoPandas / Shapely use **(x, y)** = **(longitude, latitude)** consistently. Mistakes:

- Reading `(lat, lng)` columns into `Point(lat, lng)` puts the point in the wrong hemisphere.
- Some sources (EPSG-stored CRS metadata) declare axis order in (lat, lng); if you use `pyproj.CRS` directly with `always_xy=False`, you get confusion.

**Always:**

```python
from shapely.geometry import Point
p = Point(longitude, latitude)  # (x, y)
```

Never `Point(lat, lng)`. If your source has `(lat, lng)` columns, swap explicitly:

```python
gdf = gpd.GeoDataFrame(
    df,
    geometry=gpd.points_from_xy(df["lng"], df["lat"]),  # x first
    crs="EPSG:4326",
)
```

## pyproj for edge cases

When SU's helpers + GeoPandas don't cover the case (custom projections, datum shifts, vertical CRS):

```python
from pyproj import Transformer
transformer = Transformer.from_crs("EPSG:4326", "EPSG:32614", always_xy=True)
x, y = transformer.transform(longitude, latitude)
```

`always_xy=True` is the safety net for the axis-order trap above.

## Quick checklist

- [ ] `set_default_crs()` called at session start
- [ ] Every `GeoDataFrame` from external source has its `.crs` verified
- [ ] All distance/area calculations are on a projected CRS, not 4326/4269
- [ ] No `.set_crs(allow_override=True)` calls (you wanted `.to_crs`)
- [ ] Column-name conventions (lng/lat or x/y) are consistent across the codebase
