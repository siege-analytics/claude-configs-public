# Principle: Name by SRID

When the engine doesn't store CRS metadata with the geometry — and most don't — track the CRS via column naming convention. Use `geom_<srid>` as the column name. The bug surfaces at column-name level, before downstream operations corrupt silently.

## The principle

A coordinate column called `geom` doesn't tell you what CRS it's in. A coordinate column called `geom_4326` does, at the column-name level, without needing to consult metadata or documentation.

When stage 1 produces `geom_4326` and stage 2 outputs `geom_5070`, the rename is the documentation. When stage 3 expects `geom_4326` but gets `geom_5070`, the type-checker (or schema-aware reader) catches it. When you're reading old code six months later, the column name is the explanation.

The convention is universally applicable across engines, but **load-bearing for engines without per-row CRS storage** (Sedona, DuckDB-spatial, raw Shapely).

## Where it matters most

| Engine | CRS stored where? | Naming convention impact |
|---|---|---|
| **PostGIS `geometry`** | Per-row SRID in the geometry value itself | Belt-and-suspenders; column name + per-row SRID both work |
| **PostGIS `geography`** | Always EPSG:4326 implicitly | Naming optional |
| **GeoPandas** | `.crs` attribute on the GeoDataFrame | Naming useful but `.crs` is the source of truth |
| **Shapely (raw)** | Nothing | **Naming is the only signal** |
| **Sedona** | Nothing in schema | **Naming is the only signal** |
| **DuckDB-spatial** | Nothing in GEOMETRY type | **Naming is the only signal** |
| **GeoParquet** | Column metadata | Naming useful; metadata is the source of truth |

The bottom three are where naming is the sole defense against silent CRS drift.

## The naming pattern

```
geom_<srid>
```

Examples:
- `geom_4326` — WGS 84 lat/lng
- `geom_5070` — Conus Albers Equal Area
- `geom_3857` — Web Mercator
- `geom_26915` — NAD83 / UTM zone 15N

For multiple geometry columns of the same type:

```
centroid_4326
boundary_4326
buffer_5070
```

The pattern: `<role>_<srid>`.

## Per-engine implementation

### Sedona

```python
df = sedona.read.format("geoparquet").load("s3://bucket/data.parquet")
df = df.withColumn("geom_4326", expr("ST_GeomFromWKB(geom_wkb)"))
df = df.withColumn("geom_5070", expr("ST_Transform(geom_4326, 'EPSG:4326', 'EPSG:5070')"))

# Now any downstream operation can tell at a glance:
result = sedona.sql("""
    SELECT id, ST_Area(geom_5070) AS area_m2 FROM df  -- meters², because of column name
""")
```

When stage 2 reads `geom_5070`, it knows the units. When stage 3 reads `geom_4326`, it knows to project before measuring.

### DuckDB-spatial

```python
con.execute("""
    COPY (
        SELECT *,
               ST_Point(longitude, latitude) AS geom_4326
        FROM 'addresses.csv'
    ) TO 'addresses.parquet' (FORMAT PARQUET)
""")

# Downstream reads
con.execute("SELECT id, ST_Area(ST_Transform(geom_4326, 'EPSG:4326', 'EPSG:5070')) FROM 'addresses.parquet'")
```

### Shapely (raw)

```python
# Variable naming follows the same convention
point_4326 = Point(longitude, latitude)

# Reproject to meters
from pyproj import Transformer
from shapely.ops import transform

tr = Transformer.from_crs("EPSG:4326", "EPSG:5070", always_xy=True)
point_5070 = transform(tr.transform, point_4326)

# Now: point_5070.distance(other_5070) is meters
```

### GeoPandas

The `.crs` attribute is the source of truth, but column naming for *additional* geometry columns helps:

```python
gdf["centroid_4326"] = gdf.geometry.centroid
gdf["centroid_5070"] = gdf.to_crs("EPSG:5070").geometry.centroid
```

When you have multiple geometry columns, only one is the active geometry (`gdf.geometry`); the others are just data. Naming makes which-CRS-is-which obvious.

### PostGIS

PostGIS stores SRID per-row, so naming is redundant for safety. But useful for clarity in tables with multiple geometry columns:

```sql
CREATE TABLE features (
    id BIGSERIAL,
    geom_4326 geometry(Point, 4326),
    geom_5070 geometry(Point, 5070),  -- materialized projection for fast distance work
    geog geography(Point, 4326)
);
```

## What "the bug surfaces at column-name level" means

Without the convention:

```python
# Stage 1 (someone else's code, six months ago)
df_stage1 = sedona.sql("SELECT id, ST_Transform(geom, 'EPSG:4326', 'EPSG:5070') AS geom FROM source")
df_stage1.write.format("geoparquet").save("s3://stage/")

# Stage 2 (you, today)
df_stage2 = sedona.read.format("geoparquet").load("s3://stage/")
df_stage2 = df_stage2.withColumn("area_m2", expr("ST_Area(geom)"))
# Problem: the area is in m² because stage 1 projected, but you didn't know that
# Six months later, a different stage 1 ships data still in 4326 — same column name
# Now your area is in degrees², numbers look similar enough not to alarm, conclusions wrong
```

With the convention:

```python
# Stage 1
df_stage1 = sedona.sql("SELECT id, ST_Transform(geom, 'EPSG:4326', 'EPSG:5070') AS geom_5070 FROM source")
df_stage1.write.format("geoparquet").save("s3://stage/")

# Stage 2
df_stage2 = sedona.read.format("geoparquet").load("s3://stage/")
# Schema check: column is "geom_5070" — you know it's projected
df_stage2 = df_stage2.withColumn("area_m2", expr("ST_Area(geom_5070)"))
# Six months later, if stage 1 ships data still in 4326 with column "geom_4326",
# stage 2's read fails fast: "column geom_5070 not found"
```

The convention turns a silent semantic bug into a loud schema-validation bug. Faster to detect, faster to fix.

## When the convention breaks down

- **Tables with one fixed CRS** (always 4326, e.g.) — naming is overhead. Just use `geom`. The discipline matters when CRS varies.
- **External data with fixed schemas** — you can't rename columns of incoming Parquet files; track CRS via sidecar metadata or wrapper.
- **GeoPandas single-geometry frames** — `.crs` is the source of truth; column name is decorative.
- **Schemas owned by another team** — you can't impose the convention; document the CRS in the data dictionary.

For these cases, a `crs_metadata.md` or `dataset_dictionary.json` sidecar serves the same role.

## Combined with type constraints

In PostGIS, combine naming with type constraints for double safety:

```sql
CREATE TABLE features (
    id BIGSERIAL,
    geom_4326 geometry(Point, 4326),  -- name AND type AND SRID
    geom_5070 geometry(Point, 5070)
);
```

Inserting a 4326 geometry into the `geom_5070` column raises:

```
ERROR:  Geometry SRID (4326) does not match column SRID (5070)
```

Before any downstream operation runs. The fastest possible detection.

## What about non-geometry CRS-bound columns?

Columns that *aren't geometry* but depend on CRS — bounding boxes, coordinate ranges, etc. — same convention:

```sql
xmin_4326 DOUBLE PRECISION,
ymin_4326 DOUBLE PRECISION,
xmax_4326 DOUBLE PRECISION,
ymax_4326 DOUBLE PRECISION
```

Or as one column:

```sql
bbox_4326 box2d
```

Anything where the units depend on the CRS deserves the suffix.

## Pitfalls

- **Forgetting to update the column name when reprojecting** — `ST_Transform` produces 5070 coordinates but you keep the name `geom_4326`. Defeats the convention. Update both.
- **Columns named just `geom`** — works but loses the safety property. Acceptable for fixed-CRS tables; risky for multi-CRS pipelines.
- **Different conventions across teams** — `geom_4326` vs `geom_wgs84` vs `geom_latlng` for the same thing. Pick one project-wide.
- **Reading a column without checking the suffix** — discipline isn't free; it requires the reader to actually look at the name. Pair with schema validation.
- **CRS-suffix in code variable names but not table columns** (or vice versa) — convention drift between layers.

## Cross-links

- [`crs-is-meaning.md`](crs-is-meaning.md) — the principle this convention enforces
- [`../crs-decision-tree.md`](../crs-decision-tree.md) — picking which SRID to use
- [`../gdal-availability-matrix.md`](../gdal-availability-matrix.md) — GeoParquet metadata as alternative to naming
