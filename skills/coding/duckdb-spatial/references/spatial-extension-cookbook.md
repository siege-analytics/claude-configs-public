# DuckDB Spatial Extension — Cookbook

Common operations as recipes. Assumes `con.load_extension("spatial")` already called.

## Setup

```python
import duckdb

con = duckdb.connect()                 # in-memory
# con = duckdb.connect("analysis.db")  # file-backed for persistence
con.install_extension("spatial")        # one-time download per environment
con.load_extension("spatial")
```

For S3 reads:

```python
con.install_extension("httpfs")
con.load_extension("httpfs")
con.execute("CREATE SECRET (TYPE S3, PROVIDER CREDENTIAL_CHAIN)")  # use IAM role
```

## Construct geometries

```sql
SELECT ST_Point(-98, 30) AS p;
SELECT ST_GeomFromText('POLYGON((-99 29, -97 29, -97 31, -99 31, -99 29))') AS poly;
SELECT ST_GeomFromWKB(wkb_bytes) AS g;
SELECT ST_GeomFromGeoJSON('{"type":"Point","coordinates":[-98,30]}') AS g;
```

## Convert geometries to text/binary

```sql
SELECT ST_AsText(geom) AS wkt FROM features;
SELECT ST_AsBinary(geom) AS wkb FROM features;
SELECT ST_AsGeoJSON(geom) AS gj FROM features;
```

## Predicates

```sql
SELECT * FROM points p JOIN counties c
  ON ST_Within(p.geom, c.geom);

SELECT * FROM features WHERE ST_Intersects(geom, ST_GeomFromText('POLYGON(...)'));
SELECT * FROM features WHERE ST_Contains(boundary, geom);
SELECT * FROM features WHERE ST_Disjoint(a.geom, b.geom);
```

## Distance — choose your units

```sql
-- In CRS units (meaningless for lat/lng)
SELECT ST_Distance(a.geom, b.geom) FROM places a JOIN places b ON a.id < b.id;

-- Spheroidal meters (great-circle on WGS84) — for lat/lng coords
SELECT ST_Distance_Sphere(a.geom, b.geom) FROM places a JOIN places b ON a.id < b.id;

-- Project first, then plain distance for projected meters
SELECT ST_Distance(
    ST_Transform(a.geom, 'EPSG:4326', 'EPSG:5070'),
    ST_Transform(b.geom, 'EPSG:4326', 'EPSG:5070')
) FROM places a JOIN places b ON a.id < b.id;
```

## Spatial join with R-tree index

```sql
CREATE INDEX counties_geom_idx ON counties USING RTREE (geom);

-- Join now uses the R-tree
SELECT p.id, c.geoid
FROM points p JOIN counties c ON ST_Within(p.geom, c.geom);
```

For ad-hoc queries, DuckDB builds an in-memory R-tree implicitly when it sees `ST_Within`/`ST_Intersects` in a join condition. The explicit `CREATE INDEX` makes it persistent for repeated queries.

## ST_Read — legacy formats without GDAL on host

```sql
SELECT * FROM ST_Read('input.shp');
SELECT * FROM ST_Read('input.gpkg', layer='polygons');
SELECT * FROM ST_Read('input.kml');
SELECT * FROM ST_Read('s3://bucket/input.shp');
```

The bundled GDAL inside the spatial extension does the work. The host system has no GDAL.

## CSV → GeoParquet pipeline

```sql
COPY (
    SELECT
        *,
        ST_Point(longitude, latitude) AS geom_4326
    FROM 'addresses.csv'
) TO 'addresses.parquet' (FORMAT PARQUET);
```

GeoParquet output is readable by GeoPandas, Sedona, BigQuery GIS, anything that understands the GeoParquet spec.

## Reproject

```sql
-- One-off
SELECT ST_Transform(geom, 'EPSG:4326', 'EPSG:5070') AS geom_5070 FROM points;

-- Materialize
COPY (
    SELECT id, name, ST_Transform(geom, 'EPSG:4326', 'EPSG:5070') AS geom_5070
    FROM 'features.parquet'
) TO 'features_5070.parquet' (FORMAT PARQUET);
```

PROJ ships inside the extension; no separate install.

## Aggregates

```sql
-- Bounding box of all geometries
SELECT ST_Envelope_Agg(geom) AS bbox FROM features;

-- Union all polygons
SELECT ST_Union_Agg(geom) AS combined FROM districts WHERE state = 'TX';

-- Centroid
SELECT ST_Centroid(geom) AS center FROM features;
```

## Validity

```sql
SELECT id FROM features WHERE NOT ST_IsValid(geom);

-- Repair
UPDATE features SET geom = ST_MakeValid(geom) WHERE NOT ST_IsValid(geom);
```

## Geohash / spatial binning

```sql
SELECT ST_GeoHash(geom, 9) AS gh9 FROM features;
SELECT gh, COUNT(*) FROM (
    SELECT ST_GeoHash(geom, 5) AS gh FROM points
) GROUP BY gh;
```

For H3 hexagonal indexing, install the H3 extension separately (`INSTALL h3 FROM community`).

## Distance-within with index

```sql
-- ST_DWithin equivalent — DuckDB doesn't have a dedicated function, use ST_Distance_Sphere
SELECT a.id, b.id
FROM places a JOIN places b ON a.id < b.id
WHERE ST_Distance_Sphere(a.geom, b.geom) < 5000;  -- 5 km
```

Index assistance is more limited than PostGIS's `ST_DWithin`. For high-volume distance work, project first and use plain `ST_Distance` with the indexed projected geometry.

## Spatial join across files (without loading)

```sql
-- DuckDB reads both files, joins, returns result — never materializes intermediate
COPY (
    SELECT p.id, c.geoid
    FROM 'donations.parquet' p
    JOIN 'counties.parquet' c
      ON ST_Within(p.geom, c.geom)
) TO 'donations_with_county.parquet' (FORMAT PARQUET);
```

Streaming I/O. RAM usage proportional to working set, not total data.

## Predicate pushdown for cloud reads

```python
result = con.execute("""
    SELECT *
    FROM 's3://bucket/donations.parquet'
    WHERE state = 'TX' AND amount > 1000
""").df()
```

DuckDB pushes filters into the Parquet reader; only matching row groups are downloaded from S3. For large cloud datasets this is the critical performance win.

## Batch processing many files

```sql
-- Glob pattern — reads all matching files
SELECT *, ST_Centroid(geom) AS centroid
FROM read_parquet('s3://bucket/donations/*.parquet');

-- With Hive-style partitions
SELECT *
FROM read_parquet('s3://bucket/donations/state=TX/*.parquet');
```

## Performance tuning

```python
# Set threads
con.execute("SET threads = 8")

# Set memory limit (spills above this)
con.execute("SET memory_limit = '8GB'")

# For very large queries, set the temp directory (defaults to /tmp)
con.execute("SET temp_directory = '/mnt/scratch'")
```

DuckDB spills automatically; you mostly tune by giving it more memory and faster scratch disk.

## Observability

```sql
EXPLAIN ANALYZE
SELECT c.geoid, COUNT(*)
FROM 'donations.parquet' p
JOIN 'counties.parquet' c ON ST_Within(p.geom, c.geom)
GROUP BY c.geoid;
```

DuckDB's EXPLAIN is concise; look for `RANGE_JOIN` or `RTREE_INDEX_JOIN` nodes for spatial-aware execution. `NESTED_LOOP_JOIN` on a spatial predicate means the optimizer didn't use the index.

## Cross-database queries

DuckDB can query Postgres, MySQL, SQLite directly:

```sql
INSTALL postgres;
LOAD postgres;
ATTACH 'host=localhost dbname=mydb user=u password=p' AS pg (TYPE POSTGRES);

SELECT *
FROM pg.public.donations p
JOIN 'counties.parquet' c ON ST_Within(p.geom, c.geom);
```

Useful when you have spatial data in Parquet but the lookup table is in Postgres.

## Reference

- DuckDB spatial extension docs: https://duckdb.org/docs/extensions/spatial
- Spatial function reference: https://duckdb.org/docs/extensions/spatial/functions
