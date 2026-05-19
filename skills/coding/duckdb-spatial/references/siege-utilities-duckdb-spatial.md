# siege_utilities + DuckDB-Spatial — Interop Map

`siege_utilities` pulls `duckdb>=0.7.0` as a `performance` extra, but currently uses it only for format conversion. The full DuckDB-spatial query layer is **bring-your-own** today. This file documents what SU does, doesn't, and the upstream-PR opportunities (which, when they land, will collapse most inline DuckDB SQL into one-liners).

This is the thinnest of the four engine SU maps because SU's DuckDB integration is the smallest. Most of it is "write directly + watch for SU-1, SU-7, SU-9 to land."

## What SU does today

### Format conversion → `SpatialDataTransformer`

`siege_utilities.geo.spatial_transformations.SpatialDataTransformer.convert_format()` supports a `duckdb` output type:

```python
from siege_utilities.geo.spatial_transformations import SpatialDataTransformer

transformer = SpatialDataTransformer()
transformer.convert_format(
    gdf,
    output_format="duckdb",   # also: shapefile, geojson, gpkg, kml, gml, wkt, wkb, postgis
    output_path="output.duckdb",
)
```

It checks `DUCKDB_AVAILABLE` and adds DuckDB output to the supported set if installed. Useful when you're in a SU-driven pipeline that needs to emit a DuckDB file as an output.

That's the entire DuckDB integration in SU as of the spatial-overhaul snapshot.

### Capability detection → `geo_capabilities()` reports duckdb presence

```python
from siege_utilities.geo.capabilities import geo_capabilities

caps = geo_capabilities()
caps["duckdb"]  # True / False
```

Useful for deciding whether to fall through from a missing GDAL stack to DuckDB-spatial. Doesn't drive any SU logic itself.

## What SU doesn't do — write directly

The honest list. Each item below is also a candidate upstream PR (referenced by ID).

### 1. Reading GeoParquet via DuckDB-WKB (no GDAL)

```python
import duckdb
import geopandas as gpd

con = duckdb.connect()
con.load_extension("spatial")
df = con.execute("""
    SELECT *, ST_AsBinary(geom) AS geom_wkb
    FROM 'features.parquet'
    WHERE state = 'TX'
""").df()

# Convert to GeoDataFrame
from shapely import wkb
df["geometry"] = df["geom_wkb"].apply(wkb.loads)
gdf = gpd.GeoDataFrame(df.drop(columns="geom_wkb"), geometry="geometry", crs="EPSG:4326")
```

This is the load-bearing pattern for GDAL-less environments. **SU-1** (`read_geoparquet()` / `write_geoparquet()` using DuckDB-WKB) would collapse this to a one-liner. Until it lands, write the inline pattern above.

See [`geoparquet-without-gdal.md`](geoparquet-without-gdal.md) for the full pattern.

### 2. CSV → GeoParquet conversion

```python
con.execute("""
    COPY (
        SELECT *, ST_Point(longitude, latitude) AS geom
        FROM 'addresses.csv'
    ) TO 'addresses.parquet' (FORMAT PARQUET)
""")
```

**SU-7** (`csv_to_geoparquet(csv_path, lat_col, lon_col, output_path)`) wraps this. Until it lands, write the SQL.

### 3. Spatial query helpers

```python
con.execute("""
    SELECT p.donation_id, c.geoid
    FROM read_parquet('donations.parquet') p
    JOIN read_parquet('counties.parquet') c
      ON ST_Within(p.geom, c.geom)
""").df()
```

**SU-9** (DuckDB spatial-query helpers — wrap `INSTALL spatial; LOAD spatial; ST_Read(...)`) would provide a `query_spatial()` helper returning a GeoDataFrame. Today: write the SQL inline.

### 4. Reading shapefile / GPKG / KML without GDAL on host

```python
df = con.execute("SELECT * FROM ST_Read('input.shp')").df()
```

The bundled GDAL inside DuckDB's spatial extension does the work. SU has no wrapper; this is one line, so it's not a high-priority PR candidate.

### 5. CRS handling

DuckDB's GEOMETRY type doesn't store SRID metadata. SU's `set_default_crs()` doesn't help here (it's GeoDataFrame-aware, not DuckDB-aware). Track CRS externally via column naming convention:

```sql
COPY (
    SELECT *, ST_Point(longitude, latitude) AS geom_4326
    FROM 'addresses.csv'
) TO 'addresses_4326.parquet' (FORMAT PARQUET)
```

When converting from DuckDB results to a GeoDataFrame, set the CRS explicitly:

```python
gdf = gpd.GeoDataFrame(df, geometry="geom", crs="EPSG:4326")
```

### 6. Cloud credentials

```python
con.execute("INSTALL httpfs")
con.execute("LOAD httpfs")
con.execute("CREATE SECRET (TYPE S3, PROVIDER CREDENTIAL_CHAIN)")
```

SU has no DuckDB-credential helper. Use IAM role / instance profile via `PROVIDER CREDENTIAL_CHAIN`. SU-9 would likely include this.

## Pending SU upstream PRs

From the spatial-overhaul plan §10 backlog, ordered by relevance to DuckDB-spatial work:

| # | Title | Impact on this skill |
|---|---|---|
| **SU-1** | `read_geoparquet()` / `write_geoparquet()` via DuckDB-WKB | **P0.** Closes the GDAL-less GeoParquet I/O gap. Most-used pattern in DuckDB-spatial work. |
| **SU-9** | DuckDB spatial-query helpers (`query_spatial`, `ST_Read` wrapper, GeoDataFrame return) | **P2.** Wraps the inline DuckDB SQL into a SU function. Worth filing once SU-1 lands. |
| **SU-7** | `csv_to_geoparquet(csv_path, lat_col, lon_col, output_path)` | **P2.** Common pipeline shape; one-liner convenience. |

Other items in §10 (SU-2 CRS validation, SU-3 geometry validation, SU-4 Sedona wrappers, SU-5 PostGIS query builder, SU-6 pyogrio fallback, SU-8 areal interpolation metrics, SU-10 capability tier docs) don't directly touch DuckDB-spatial. SU-2 (CRS validation) would be useful when projecting in DuckDB but doesn't depend on DuckDB.

## Checklist when starting DuckDB-spatial work

- [ ] `caps = geo_capabilities()`; verify `caps["duckdb"]` is True (or `pip install duckdb`)
- [ ] `con.install_extension("spatial")` + `con.load_extension("spatial")` at session start
- [ ] For S3 reads, also install `httpfs` and use `CREDENTIAL_CHAIN` (no hardcoded creds)
- [ ] Track CRS externally — column naming convention `geom_<srid>`
- [ ] Watch for SU-1 to land; refactor inline `read_parquet` / `COPY` patterns to `read_geoparquet()` / `write_geoparquet()` once available
- [ ] If you write the same DuckDB-spatial wrapper twice across projects, file the SU PR

## When to NOT use DuckDB-spatial despite SU's gaps

The thin SU integration isn't a reason to avoid DuckDB-spatial. The engine is the right tool whenever:

- GDAL is unavailable in the environment
- The data is on disk in Parquet/CSV and you want SQL semantics
- Single-node, < 100 GB working set
- You're prototyping and don't want Spark startup cost

The inline SQL is concise enough that the missing SU layer doesn't add real friction — it just adds 5-10 lines per pipeline. Once SU-1 lands, that drops to 1 line.

## Mental model

DuckDB-spatial is the **GDAL-less single-node SQL spatial engine.** SU is currently the **runtime planner + Census/CRS/geometry plumbing** — the two complement at a coarse level (SU detects `caps["duckdb"]`; DuckDB does the work). The fine-grained interop (SU-blessed read/write/query helpers) is the upcoming SU-1 / SU-9 / SU-7 territory.

Treat the inline DuckDB SQL as the temporary state. As the SU PRs land, replace.
