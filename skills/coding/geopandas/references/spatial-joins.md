# GeoPandas Spatial Joins

`gpd.sjoin` and `gpd.sjoin_nearest` — patterns, predicates, performance.

## sjoin basics

```python
import geopandas as gpd

points = gpd.read_parquet("donations.parquet")
counties = gpd.read_parquet("counties.parquet")

joined = gpd.sjoin(
    points,             # left
    counties,           # right
    how="left",         # "left", "right", "inner"
    predicate="within", # "intersects", "within", "contains", "covers", "covered_by", "crosses", "overlaps", "touches", "dwithin"
)
```

Result: each left row gets right columns appended for matching rows. Use `how="left"` to preserve unmatched left rows (with NaN right columns).

## Predicate decision

| Predicate | "True when..." | Boundary points? |
|---|---|---|
| `intersects` | any shared point | included |
| `within` | left is inside right | excluded |
| `contains` | right is inside left | excluded |
| `covers` | left covers right (boundary OK) | included |
| `covered_by` | left is covered by right (boundary OK) | included |
| `dwithin` | within distance (use `distance=` kwarg) | n/a |

For "which polygon does this point fall in," `within` *misses* points exactly on a boundary. Real-world data has many such points (geocoded centroids of buildings on streets). For assignment work, prefer `intersects` or `covered_by`.

## sjoin_nearest

For "the closest right feature for each left feature":

```python
joined = gpd.sjoin_nearest(
    points,
    facilities,
    how="left",
    distance_col="dist_m",  # adds a column with the distance
    max_distance=5000,      # in CRS units; set this — otherwise it scans everything
)
```

Always set `max_distance`. Without it, every left point matches against the nearest right feature globally, which is O(N×M) without spatial pruning.

For meters, project both sides to a meter-based CRS first.

## Performance

### Build the index once

GeoPandas builds an STRtree spatial index on the right side of `sjoin` automatically. The first access to `.sindex` builds it; subsequent calls reuse:

```python
counties.sindex  # build now (eager)
joined1 = gpd.sjoin(points, counties, predicate="within")
joined2 = gpd.sjoin(more_points, counties, predicate="within")  # reuses index
```

For frames you'll join against repeatedly, build the index explicitly to avoid surprise latency.

### Vectorize, don't apply

Bad:
```python
points["county"] = points.apply(
    lambda row: counties[counties.contains(row.geometry)].iloc[0]["name"],
    axis=1,
)  # O(N*M), no index
```

Good:
```python
joined = gpd.sjoin(points, counties[["name", "geometry"]], how="left", predicate="within")
points["county"] = joined["name"]
```

### Filter before joining

If you only need joins within Texas, filter both sides first:

```python
points_tx = points[points["state"] == "TX"]
counties_tx = counties[counties["state_fips"] == "48"]
joined = gpd.sjoin(points_tx, counties_tx, predicate="within")
```

Drops the candidate set before the spatial index even runs.

### Sjoin against subdivided polygons

For complex polygons (Census tracts, congressional districts), pre-subdivide:

```python
from shapely.ops import unary_union
import numpy as np

def subdivide_polygon(geom, max_vertices=256):
    """Recursively split until each piece has ≤ max_vertices."""
    if len(geom.exterior.coords) <= max_vertices:
        return [geom]
    minx, miny, maxx, maxy = geom.bounds
    midx = (minx + maxx) / 2
    left = geom.intersection(Polygon([(minx, miny), (midx, miny), (midx, maxy), (minx, maxy)]))
    right = geom.intersection(Polygon([(midx, miny), (maxx, miny), (maxx, maxy), (midx, maxy)]))
    return subdivide_polygon(left, max_vertices) + subdivide_polygon(right, max_vertices)
```

Or use `shapely.ops.split`, or PostGIS `ST_Subdivide` if data is round-tripping through Postgres.

In practice for moderate datasets (< 10M points × few thousand polygons), this isn't needed — GeoPandas' STRtree is fast enough. For larger or more-complex data, push to PostGIS or Sedona where `ST_Subdivide` is one call.

## Many-to-many: spatial overlay

For polygon-polygon "give me the intersections of these two coverages":

```python
overlay = gpd.overlay(
    a, b,
    how="intersection",  # "union", "identity", "symmetric_difference", "difference"
    keep_geom_type=True,
)
```

Useful for areal interpolation (split a population polygon by overlapping target polygon, distribute population by area). For that specific use case, prefer `siege_utilities.geo.interpolation.areal.interpolate_areal()` — it handles weighting correctly.

## sjoin with predicate=dwithin

Distance-within search:

```python
joined = gpd.sjoin(
    points,
    facilities,
    predicate="dwithin",
    distance=500,  # in CRS units — project to meters first if needed
)
```

This is index-aware and faster than computing `gpd.GeoSeries.distance` and filtering.

## Result structure

After `sjoin`:
- Left columns retained as-is.
- Right columns added with their original names.
- An `index_right` column shows the matched right-side index.
- For `how="left"`, unmatched rows have NaN in right columns.

For multi-match cases (a point that intersects two boundaries — common at boundary lines), you get multiple rows in the result. Deduplicate with `drop_duplicates` on the left index, or aggregate with `groupby`.

## Pitfalls

- **CRS mismatch.** sjoin will reproject the right side to match the left, with a warning. Preempt this — reproject both to a common CRS explicitly.
- **`predicate="contains"` confusion.** `contains` means *left contains right* (left is the polygon, right is the point). Most "find the polygon for each point" tasks want `predicate="within"` (left is the point, right is the polygon) or `predicate="intersects"`.
- **`how="right"`.** Rarely what you want. Use `how="left"` and swap arguments instead.
- **`sjoin` on tiny right side.** If the right side is < 100 polygons, building the spatial index is overhead. Just iterate or use a single GeoSeries comparison.
