# Shapely Directly — When GeoDataFrame is Overkill

GeoPandas builds on Shapely. When inputs are dicts/WKT/coordinate pairs (not files, not tables), drop directly to Shapely. Faster, fewer dependencies, simpler code.

## When to skip GeoPandas

| Input shape | Use |
|---|---|
| File on disk → GeoDataFrame manipulation → write file | **GeoPandas** |
| Single coordinates / WKT / dicts → check predicate / measure / transform | **Shapely directly** |
| API response with `geometry` field as GeoJSON dict | **Shapely directly** to test/measure; convert to GeoDataFrame only if you have many |
| Stream of points being checked against a polygon set | **`shapely.STRtree` directly** (avoids GeoDataFrame allocation per row) |

## The basic operations

```python
from shapely.geometry import Point, LineString, Polygon, MultiPolygon, shape
from shapely import wkt, wkb
from shapely.ops import transform, unary_union

# Construct
p = Point(longitude, latitude)
poly = Polygon([(-99, 29), (-97, 29), (-97, 31), (-99, 31), (-99, 29)])
line = LineString([(0, 0), (1, 1), (2, 0)])

# From WKT
g = wkt.loads("POINT(-98 30)")

# From WKB (typical when reading from Parquet/Postgres)
g = wkb.loads(wkb_bytes)

# From GeoJSON dict (typical from API responses)
g = shape({"type": "Point", "coordinates": [-98, 30]})

# Predicates
p.within(poly)        # True
poly.contains(p)      # True
p.distance(poly)      # 0.0
p.buffer(0.1).area    # ~0.0314 (degrees², so actually meaningless without projection)
```

## Reproject without GeoPandas

```python
from pyproj import Transformer
from shapely.ops import transform

tr = Transformer.from_crs("EPSG:4326", "EPSG:5070", always_xy=True)
poly_5070 = transform(tr.transform, poly)
print(poly_5070.area)  # in square meters now
```

## Spatial join via STRtree

```python
from shapely.strtree import STRtree

# Polygons indexed once
tree = STRtree(polygons)  # list/array of Shapely geoms

# Query each point
for point in points:
    candidate_indices = tree.query(point)
    matches = [i for i in candidate_indices if polygons[i].contains(point)]
```

`STRtree.query` returns *bounding-box candidates*. The exact predicate (`contains`, `intersects`, etc.) must be applied to filter false positives. This is what `gpd.sjoin` does internally; doing it directly skips GeoPandas overhead.

For a typed result without numpy index gymnastics:

```python
matches_per_point = []
for point in points:
    cands = tree.query(point, predicate="intersects")  # Shapely 2.x: predicate arg
    matches_per_point.append([polygons[i] for i in cands])
```

## When to convert TO GeoDataFrame

Once you have N+ records that share a CRS and you'll iterate / aggregate:

```python
import geopandas as gpd

records = [{"id": i, "geometry": geom, "name": n} for i, (geom, n) in enumerate(zip(geoms, names))]
gdf = gpd.GeoDataFrame(records, crs="EPSG:4326")
```

Threshold: ~100 records. Below that, lists of dicts + Shapely are simpler.

## When to convert FROM GeoDataFrame

If you've built a GeoDataFrame and need to pass it to a non-GeoPandas API (a JSON serializer, a custom processor):

```python
# To list of GeoJSON-shaped dicts
records = gdf.to_dict("records")  # geometry remains as Shapely; convert if needed
records = [
    {**{k: v for k, v in r.items() if k != "geometry"}, "geometry": r["geometry"].__geo_interface__}
    for r in records
]

# To list of WKT
wkts = gdf.geometry.to_wkt().tolist()

# To list of WKB bytes
wkbs = gdf.geometry.to_wkb().tolist()
```

## Pitfalls when going Shapely-direct

### 1. CRS lives nowhere

Shapely geometries don't carry CRS. You must track it externally:

```python
# Fragile
geom = Point(-98, 30)
area = geom.buffer(0.01).area  # in square degrees — meaningless

# Better
SRID = "EPSG:4326"
geom = Point(-98, 30)
# When computing area, project explicitly
area_m2 = transform(Transformer.from_crs(SRID, "EPSG:5070", always_xy=True).transform, geom).area
```

This is the main reason to use GeoDataFrame even for small datasets — it tracks `.crs`. If you stay direct-Shapely, document the CRS in variable names: `point_4326 = Point(...)`.

### 2. Coordinate axis order

Shapely uses **(x, y) = (longitude, latitude)** consistently. `Point(-98, 30)` is "longitude -98, latitude 30." Common mistake: `Point(30, -98)` puts the point in the Pacific Ocean off Antarctica.

### 3. Mutability

Shapely 2.x geometries are immutable. Operations return new geometries:

```python
buffered = point.buffer(0.1)  # new geometry; original unchanged
```

### 4. Empty geometries

```python
empty = wkt.loads("POINT EMPTY")
empty.is_empty   # True
empty.area       # 0.0
empty.bounds     # () — empty tuple, not (0, 0, 0, 0)
empty.contains(point)  # False (everything is False against empty)
```

Test `g.is_empty` before predicate calls if your data may have empties.

### 5. Validity

```python
poly = Polygon([(0, 0), (2, 2), (0, 2), (2, 0), (0, 0)])  # bowtie — invalid
poly.is_valid  # False
poly.area      # may give wrong number; many ops silently broken on invalid

from shapely.validation import make_valid
poly_fixed = make_valid(poly)  # MultiPolygon of two triangles
```

Validate at the boundary — when reading from a source you don't control.

## Integration with siege_utilities

SU's `geo.spatial_runtime.GeometryPayload` round-trips Shapely geometries through Spark/Sedona stages safely. If you're going Shapely-direct in a Spark UDF, use SU's encoder/decoder rather than `geom.wkt` (which loses precision) or pickling (which breaks across versions):

```python
from siege_utilities.geo.spatial_runtime import encode_geometry, decode_geometry

payload = encode_geometry(geom)  # WKB-bytes payload, Spark-safe
# ... pass through Spark stage ...
geom_back = decode_geometry(payload)
```

See [`sedona`](../../sedona/SKILL.md) for the Spark side.
