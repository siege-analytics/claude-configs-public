# GeoPandas Performance

The big wins, in order of payoff.

## 1. Switch I/O engine to pyogrio

GeoPandas 0.13+ supports `pyogrio` as a faster, lighter alternative to `fiona`:

```python
import geopandas as gpd
gpd.options.io_engine = "pyogrio"  # session-wide
```

Reads are 5-10× faster on large shapefiles. `pyogrio` wheels are smaller (still need GDAL underneath for some formats, but no separate Fiona stack).

## 2. Use Shapely 2.x / GEOS-vectorized ops

Shapely 2.x (released 2022) vectorizes operations through `shapely.STRtree` and pygeos-style C bindings. GeoPandas builds on this when available.

```python
# Vectorized — fast
gdf["area_m2"] = gdf.to_crs("EPSG:5070").geometry.area

# Per-row apply — slow
gdf["area_m2"] = gdf.apply(lambda r: project_then_area(r.geometry), axis=1)
```

If you're on Shapely 1.x, upgrade. If you're on `pygeos`, migrate to Shapely 2.x (pygeos was merged in).

## 3. Build the spatial index once

GeoPandas builds an STRtree on first `.sindex` access:

```python
counties.sindex  # eager build

# Subsequent joins reuse the index
joined1 = gpd.sjoin(points_today, counties, predicate="within")
joined2 = gpd.sjoin(points_yesterday, counties, predicate="within")
```

For frames you'll join against repeatedly, build eagerly so the latency hit is predictable.

## 4. Filter before joining

The cheapest spatial join is one against fewer rows:

```python
# Bad: join all → filter
joined = gpd.sjoin(points, counties)
joined = joined[joined["state"] == "TX"]

# Good: filter → join
points_tx = points[points["state"] == "TX"]
counties_tx = counties[counties["state_fips"] == "48"]
joined = gpd.sjoin(points_tx, counties_tx)
```

## 5. Drop columns you don't need

Spatial joins copy all columns. If `counties` has 200 columns, the result drags them all:

```python
joined = gpd.sjoin(
    points,
    counties[["geoid", "name", "geometry"]],  # just what you need
    predicate="within",
)
```

## 6. Project once, cache the result

For repeated area/distance work in a meter CRS:

```python
gdf_5070 = gdf.to_crs("EPSG:5070")
gdf_5070.to_parquet("cache/features_5070.parquet")
```

Reproject is O(N) per-row math. Caching pays off after the second use.

## 7. Avoid `apply` for spatial ops

```python
# Slow — apply iterates row-by-row
gdf["centroid"] = gdf.apply(lambda r: r.geometry.centroid, axis=1)

# Fast — vectorized
gdf["centroid"] = gdf.geometry.centroid
```

`gdf.geometry.<op>` returns a vectorized GeoSeries; `gdf.apply(lambda r: r.geometry.<op>)` is a Python loop.

## 8. Use `assign` and method chaining

For pipelines, chain to avoid temporaries:

```python
result = (
    gpd.read_parquet("source.parquet")
       .to_crs("EPSG:5070")
       .assign(area_m2=lambda d: d.geometry.area)
       .pipe(lambda d: gpd.sjoin(d, counties_5070, predicate="within"))
       .assign(area_per_capita=lambda d: d["area_m2"] / d["pop"])
)
```

Reads cleanly and avoids accidental retention of intermediate frames.

## 9. STRtree directly for many-points-vs-static-polygons

When you'll query the same polygon set many times across separate functions, hold the tree directly:

```python
from shapely.strtree import STRtree

tree = STRtree(counties.geometry.values)

def assign_county(point):
    candidates = tree.query(point)
    for idx in candidates:
        if counties.geometry.iloc[idx].contains(point):
            return counties.iloc[idx]["geoid"]
    return None
```

Avoids building/tearing down the implicit `.sindex` per `sjoin` call.

## 10. Out-of-core: dask-geopandas (with caveats)

For data larger than memory, `dask-geopandas` parallelizes GeoPandas operations across partitions:

```python
import dask_geopandas as dgpd

ddf = dgpd.from_geopandas(gdf, npartitions=8)
ddf.spatial_shuffle()
result = ddf.sjoin(counties, predicate="within").compute()
```

Caveat: `dask-geopandas` is alpha-quality compared to PostGIS or Sedona for large joins. For data > 10 GB, prefer:
- **DuckDB-spatial** ([`duckdb-spatial`](../../duckdb-spatial/SKILL.md)) — single-node, in-memory + spilling, very fast
- **Sedona** ([`sedona`](../../sedona/SKILL.md)) — distributed across a Spark cluster
- **PostGIS** with partitioning — persistent, indexed, multi-user

Dask-GeoPandas is useful for the narrow case "I want GeoPandas semantics on a single machine but the data is 2× RAM."

## 11. Skip GeoPandas when you have only points

If you're processing 10M+ points without polygons in the picture, GeoPandas overhead per row may exceed the spatial work. Consider:

- **Pure pandas + numpy** with x/y columns (use Haversine for distance, bounding-box pre-filter)
- **Shapely directly** (see [`shapely-direct.md`](shapely-direct.md))
- **DuckDB** with `ST_*` functions on Parquet

## Profiling

```python
import time

t = time.perf_counter()
joined = gpd.sjoin(points, counties, predicate="within")
print(f"sjoin: {time.perf_counter() - t:.2f}s")

# For deeper profiling
import cProfile
cProfile.run("gpd.sjoin(points, counties, predicate='within')", sort="cumtime")
```

The most common surprise: I/O dominates; the actual spatial join is fast. If reads are the bottleneck, switch to GeoParquet (see [`io-formats.md`](io-formats.md)).
