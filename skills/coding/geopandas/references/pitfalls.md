# GeoPandas / Shapely Pitfalls

Bugs that don't error and silently produce wrong results.

## CRS is None

```python
gdf = gpd.read_file("source.shp")
print(gdf.crs)  # None — .prj was missing
gdf["area"] = gdf.geometry.area  # nonsense — no projection info
```

Always check `.crs` after read; refuse to compute area/distance if it's None. See [`crs-management.md`](crs-management.md).

## Mixing CRSs in one frame

GeoPandas allows it. Operations are nondeterministic.

```python
gdf1 = gpd.read_parquet("a.parquet")  # 4326
gdf2 = gpd.read_parquet("b.parquet")  # 5070
combined = pd.concat([gdf1, gdf2])  # silently mixed
combined["area"] = combined.geometry.area  # wildly wrong for 4326 rows
```

Reproject to a common CRS before concat:

```python
combined = pd.concat([gdf1.to_crs("EPSG:5070"), gdf2])
```

## set_crs vs to_crs

```python
gdf = gdf.set_crs("EPSG:4326")  # labels (no coord change)
gdf = gdf.to_crs("EPSG:5070")   # transforms (coords change)
```

Using `set_crs` when you wanted `to_crs` leaves coordinates in the wrong projection but mislabeled. Every subsequent operation is wrong.

If you find yourself needing `set_crs(allow_override=True)`, you almost certainly wanted `to_crs`.

## predicate="contains" vs "within"

```python
joined = gpd.sjoin(points, counties, predicate="contains")  # WRONG
# This means "left contains right" — points contain counties (no row matches)

joined = gpd.sjoin(points, counties, predicate="within")    # CORRECT
# Points within counties
```

If your sjoin returns zero rows or empty matches, double-check the predicate direction.

## predicate="within" excludes boundary points

```python
joined = gpd.sjoin(points, counties, predicate="within")
# Points exactly on county boundaries: NaN
```

For assignment work where boundary points matter (geocoded street centerlines, building corners on parcel lines), use `intersects` or `covered_by`:

```python
joined = gpd.sjoin(points, counties, predicate="intersects", how="left")
```

Same gotcha as PostGIS `ST_Contains` vs `ST_Covers`.

## Z and M coordinates sneaking in

Some sources include Z (elevation) or M (measure) coordinates:

```python
gdf = gpd.read_file("source.shp")
gdf.geometry.iloc[0]  # POINT Z (-98 30 0) — has Z

# Most operations work but:
gdf.to_parquet("out.parquet")  # writes WKB with Z; some readers don't expect it
```

Strip if you don't need them:

```python
from shapely import force_2d
gdf["geometry"] = gdf.geometry.apply(force_2d)
```

## Invalid geometries

```python
gdf.geometry.is_valid.all()  # False — some are invalid
gdf["area"] = gdf.geometry.area  # may give wrong numbers for invalid polygons
```

Validate and repair on ingest:

```python
from shapely.validation import make_valid
gdf["geometry"] = gdf.geometry.apply(make_valid)
```

Or filter:

```python
gdf = gdf[gdf.geometry.is_valid]
```

The choice depends on whether you can drop invalid features (election precinct: no — the precinct exists; donor address: maybe).

## sjoin with empty right side

```python
joined = gpd.sjoin(points, counties[counties["state"] == "ZZ"], how="left")
# All points get NaN for right columns — that's fine
# But: joined is points-shaped; you might expect zero rows
```

Always specify `how`. `how="inner"` returns zero rows when there are no matches; `how="left"` keeps left rows with NaN.

## Vectorized vs apply confusion

```python
# Slow — Python loop
gdf["centroid"] = gdf.apply(lambda r: r.geometry.centroid, axis=1)

# Fast — vectorized
gdf["centroid"] = gdf.geometry.centroid
```

Almost any time you write `gdf.apply` involving `.geometry`, there's a vectorized form. Search the GeoSeries docs first.

## .to_file with default driver

```python
gdf.to_file("out.shp")  # writes Shapefile by default — column names truncated to 10 chars
```

Always specify driver:

```python
gdf.to_file("out.gpkg", driver="GPKG")
gdf.to_parquet("out.parquet")  # GeoParquet — no driver arg, no GDAL needed
```

## .crs comparison

```python
if gdf.crs == "EPSG:4326":  # works in pyproj 3.x
if str(gdf.crs) == "EPSG:4326":  # safer
if gdf.crs.to_epsg() == 4326:  # safest
```

`gdf.crs` is a `pyproj.CRS` object; equality semantics depend on pyproj version. `.to_epsg()` returns an int and compares cleanly.

## Float precision in coordinates

```python
p1 = Point(-98.123456789, 30.987654321)
p2 = Point(-98.123456789, 30.987654321)
p1.equals(p2)        # True
p1.equals_exact(p2, tolerance=0)  # True

# But round-trips:
p3 = wkt.loads(p1.wkt)
p1.equals(p3)        # might be False due to WKT formatter precision
```

For exact deduplication, hash WKB bytes:

```python
hashes = gdf.geometry.to_wkb().apply(hash)
gdf = gdf[~hashes.duplicated()]
```

## Index alignment surprise

```python
gdf2 = gdf.to_crs("EPSG:5070")
gdf["area"] = gdf2.geometry.area  # works because indexes align
```

But:

```python
gdf2 = gdf.copy().reset_index(drop=True)
gdf["area"] = gdf2.geometry.area  # NaN if original gdf has non-default index
```

`reset_index` between operations can silently misalign joins. Be explicit about index when chaining.

## .geometry name collision

```python
gdf["geometry"] = compute_thing(gdf)  # if `compute_thing` returns a Series of values, not geoms, you've broken the GeoDataFrame
```

GeoPandas tracks the active geometry column. Renaming or overwriting it without `set_geometry` can lead to operations failing with `AttributeError: 'GeoDataFrame' object has no attribute 'geometry'`.

If you need a second geometry column, use `set_geometry`:

```python
gdf["centroid"] = gdf.geometry.centroid
gdf_centroid = gdf.set_geometry("centroid")
```

## Reading large GeoJSON

```python
gdf = gpd.read_file("huge.geojson")  # may OOM on multi-GB GeoJSON
```

GeoJSON reads load the whole file into memory before parsing. For files > 1 GB, convert to GeoParquet on a smaller chunk first, or use `pyogrio.read_info()` to inspect, or stream with `fiona`'s lower-level interface.

## sjoin doubles when right side has overlapping polygons

```python
joined = gpd.sjoin(points, areas, predicate="within")
# If a point falls in two overlapping `areas` polygons, you get TWO output rows
```

Deduplicate explicitly:

```python
joined = joined[~joined.index.duplicated(keep="first")]
```

Or aggregate (e.g., `groupby(joined.index).first()`) — but choose deliberately, because keeping all matches may be what you want.
