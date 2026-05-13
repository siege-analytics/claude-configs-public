# No-GDAL Fallbacks

Some Siege environments don't have GDAL: minimal cloud images, Lambda runtimes, embedded analytics inside non-spatial services. The following is the complete map of what works without it.

## Detect tier first

```python
from siege_utilities.geo.capabilities import geo_capabilities

caps = geo_capabilities()
print(caps["tier"])  # "geo" | "geo-lite" | "geodjango" | "none"
```

- **`"geo"`** — full stack (Shapely, pyproj, GeoPandas, Fiona, Rtree). Use everything.
- **`"geo-lite"`** — Shapely + pyproj only. Most operations work; file I/O is constrained.
- **`"geodjango"`** — `"geo"` + Django GIS (still needs GDAL).
- **`"none"`** — none of the above. Fall back to pandas + math.

Branch your code on `caps["tier"]`. Don't import GeoPandas at module level if you support `geo-lite` callers — wrap with try/except or detect first.

## Operations matrix

| Operation | With GDAL | Without GDAL (geo-lite) |
|---|---|---|
| Read Shapefile | `gpd.read_file("x.shp")` | **Not possible** — convert before deploy |
| Read GeoJSON | `gpd.read_file()` | Hand-parse JSON + `shapely.geometry.shape()` |
| Read GeoPackage | `gpd.read_file()` | **Not possible** — convert before deploy |
| Read GeoParquet | `gpd.read_parquet()` (uses pyarrow, not GDAL) | `gpd.read_parquet()` works without GDAL |
| Read CSV+WKT | manual | manual — `pd.read_csv` + `shapely.wkt.loads` |
| Write GeoJSON | `gpd.to_file()` or manual | manual JSON dump + `geom.__geo_interface__` |
| Write GeoParquet | `gpd.to_parquet()` | `gpd.to_parquet()` works without GDAL |
| Reproject | `gdf.to_crs()` (uses pyproj) | `pyproj.Transformer` directly |
| Spatial predicates | `geom.within(other)` etc. | Same — pure Shapely |
| Buffer / simplify | `geom.buffer(d)` | Same — pure Shapely |
| Spatial join | `gpd.sjoin` (uses Rtree) | `shapely.STRtree` + manual loop |
| Areal interpolation | `tobler.area_interpolate` | Approximate via H3 (`siege_utilities.geo.h3_utils`) |

## The two pillars: GeoParquet + Shapely

For GDAL-less environments, the compatible-file format is **GeoParquet** and the compute layer is **pure Shapely**. Together they cover most spatial pipelines.

### Read GeoParquet without GDAL

```python
import geopandas as gpd

gdf = gpd.read_parquet("features.parquet")  # pyarrow only
# Works in geo-lite tier (or even without GeoPandas if you use pyarrow + shapely directly)
```

If GeoPandas itself isn't installed (rare), use pyarrow + shapely:

```python
import pyarrow.parquet as pq
import pandas as pd
from shapely import wkb

table = pq.read_table("features.parquet")
df = table.to_pandas()
df["geometry"] = df["geometry"].apply(wkb.loads)
# df is a pandas DataFrame with a Shapely geometry column; no GeoDataFrame
```

### Write GeoParquet without GDAL

```python
gdf.to_parquet("out.parquet")  # GeoPandas + pyarrow, no GDAL
```

This is one of the most useful no-GDAL paths. The format itself is well-supported and the WKB encoding stays canonical.

### Reproject without GDAL

`pyproj` is pure Python and ships with PROJ binaries — no GDAL dependency:

```python
from pyproj import Transformer

transformer = Transformer.from_crs("EPSG:4326", "EPSG:5070", always_xy=True)
x, y = transformer.transform(longitude, latitude)
```

For batch reprojection of a Shapely geometry:

```python
from shapely.ops import transform

geom_5070 = transform(transformer.transform, geom)
```

This works on any geometry type without GDAL.

### Spatial join without GeoPandas

Use `shapely.strtree.STRtree`:

```python
from shapely.strtree import STRtree

tree = STRtree(polygons)  # list of Shapely polygons
matches_by_point = []

for point in points:
    candidate_indices = tree.query(point)
    real_matches = [i for i in candidate_indices if polygons[i].contains(point)]
    matches_by_point.append(real_matches)
```

Fast for ~1M points; for >10M, push to PostGIS, DuckDB, or Sedona.

### Areal interpolation without overlay

If you can't use `tobler.area_interpolate` (needs full geo tier), approximate with H3 hexagonal binning:

```python
from siege_utilities.geo.h3_utils import h3_index_polygon, h3_spatial_join

# Convert source polygons to H3 cells at appropriate resolution
source_cells = h3_index_polygon(source_polygons, resolution=8)
target_cells = h3_index_polygon(target_polygons, resolution=8)

# Join via H3 cell membership
merged = h3_spatial_join(source_cells, target_cells)
```

H3 is approximate (boundaries have ~50m precision at resolution 8) but doesn't need GDAL or overlays.

## What you can't do without GDAL — at all

- Read or write Shapefile, GeoPackage, FlatGeobuf, KML, GML, KML, FileGDB, MapInfo TAB.
- True polygon overlay (`gpd.overlay`) requires GEOS via GeoPandas; the `geo-lite` tier has Shapely+pyproj only and is missing some overlay paths.
- Coordinate transformations involving non-standard datum shifts (PROJ has them, but GDAL bundles the grid files).

If you find yourself blocked on these, the choices are:

1. **Pre-convert** files to GeoParquet on a machine that has GDAL; ship Parquet to the GDAL-less environment.
2. **DuckDB-spatial** ([`duckdb-spatial`](../../duckdb-spatial/SKILL.md)) — bundles its own GEOS; reads/writes Parquet without GDAL; provides ST_* operations at SQL level. The strongest single tool for GDAL-less spatial work.
3. **PostGIS** — if you can stand up a tiny Postgres, push the spatial work there.

## SU-blessed no-GDAL paths

`siege_utilities` already supports the geo-lite tier intentionally:

- `geo.spatial_data.get_geographic_boundaries()` returns GeoDataFrames. If only `shapely` is available, parse the underlying GeoJSON manually.
- `geo.h3_utils` is fully usable at geo-lite; H3 needs no GDAL.
- `geo.crs.reproject_if_needed()` uses pyproj; works at geo-lite.
- `geo.geoid_utils.*` is pure Python; works at any tier.
- `geo.crosswalk.crosswalk_processor.apply_crosswalk()` is pandas-only; works at geo-lite.

## Pending SU upstream PRs that close gaps here

- **SU-1:** `read_geoparquet()` / `write_geoparquet()` using DuckDB-WKB without any GeoPandas dep. Closes the "I have only pandas + duckdb" path.
- **SU-6:** `pyogrio` fallback when `fiona` is missing — useful when you have *some* GDAL-adjacent stuff but not the full Fiona stack.
- **SU-9:** DuckDB spatial-query helpers — wraps `INSTALL spatial; LOAD spatial; ST_Read(...)` for parquet/csv → DataFrame.

Until these land, do the equivalent inline.

## Decision flow for the GDAL-uncertain task

```
1. caps = geo_capabilities()
2. If caps["tier"] == "geo": proceed normally with GeoPandas.
3. If caps["tier"] == "geo-lite":
     - Switch any to_file/read_file to to_parquet/read_parquet
     - Replace tobler with H3 (via siege_utilities)
     - Replace gpd.overlay with PostGIS or DuckDB if needed
4. If caps["tier"] == "none":
     - You need pandas + math + (optionally) DuckDB-spatial
     - GeoPandas isn't even available — use the pyarrow + shapely.wkb path
5. If you find an operation that's blocked:
     - Stand up DuckDB-spatial in-process
     - Or push to PostGIS / Sedona
     - Or pre-convert and ship Parquet
```
