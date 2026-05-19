# DuckDB-Spatial Pitfalls

## 1. Forgot `LOAD spatial`

```python
con = duckdb.connect()
con.execute("SELECT ST_Within(p.geom, c.geom) FROM ...")
# Catalog Error: Scalar Function ST_Within does not exist
```

`INSTALL spatial` is one-time; `LOAD spatial` is per-connection. Forget the load and ST_* functions are undefined. Always:

```python
con.install_extension("spatial")
con.load_extension("spatial")
```

## 2. Computing distance in degrees

```sql
-- WRONG — returns degrees (meaningless)
SELECT ST_Distance(p1.geom, p2.geom) FROM places p1 JOIN places p2 ON p1.id < p2.id;
```

`ST_Distance` returns CRS units. For lat/lng (EPSG:4326), use:

```sql
-- Spheroidal meters
SELECT ST_Distance_Sphere(p1.geom, p2.geom) FROM places p1 JOIN places p2 ON p1.id < p2.id;

-- Or project both sides
SELECT ST_Distance(
    ST_Transform(p1.geom, 'EPSG:4326', 'EPSG:5070'),
    ST_Transform(p2.geom, 'EPSG:4326', 'EPSG:5070')
)
FROM places p1 JOIN places p2 ON p1.id < p2.id;
```

Same gotcha as PostGIS — see [`coding/postgis/references/pitfalls.md`](../../postgis/references/pitfalls.md).

## 3. CRS is not stored in GEOMETRY type

DuckDB's `GEOMETRY` type is coordinate-only. No SRID metadata. Track CRS externally:

- Column naming convention: `geom_4326`, `geom_5070`.
- Sidecar JSON or README documenting the file's CRS.
- GeoParquet metadata when written via DuckDB's COPY (preserves through round-trip if you stay in DuckDB).

For GeoPandas interop, set the CRS on the GeoDataFrame after loading:

```python
df = con.execute("SELECT * FROM 'features.parquet'").df()
gdf = gpd.GeoDataFrame(df, geometry="geom", crs="EPSG:4326")  # explicit
```

## 4. WKB endianness assumptions

DuckDB writes WKB in standard NDR (little-endian) format, which is what every other tool reads. But:

```python
# If you read WKB from another source (e.g., Postgres EWKB) and pass to DuckDB:
con.execute("SELECT ST_GeomFromWKB(?)", [postgres_ewkb])
# May fail or misread — Postgres EWKB embeds SRID, plain WKB doesn't
```

For Postgres WKB, use `ST_AsBinary(geom)` on the Postgres side (returns plain WKB) before passing.

## 5. Single-process ceiling

DuckDB scales up, not out. Single-machine RAM × disk-spill margin is your ceiling. Practical limits:

- 32 GB RAM machine, fast NVMe scratch: comfortable up to ~50 GB working set.
- 128 GB RAM machine: ~200 GB working set.
- Beyond that: spills become the bottleneck; latency degrades; eventually OOM.

When you hit it, push to Sedona on Spark — the SQL is similar enough to port quickly.

## 6. R-tree index doesn't always get used

DuckDB's optimizer sometimes prefers a hash-based or nested-loop join for "small" right sides even when an R-tree index exists. EXPLAIN to verify:

```sql
EXPLAIN ANALYZE SELECT * FROM points p JOIN counties c ON ST_Within(p.geom, c.geom);
```

Look for `RTREE_INDEX_JOIN` or `RANGE_JOIN`. If you see `NESTED_LOOP_JOIN`, force the index:

```sql
SELECT /*+ INDEX(c counties_geom_idx) */ * FROM points p JOIN counties c ON ST_Within(p.geom, c.geom);
```

(Hint syntax may not be supported in all versions; check docs.)

## 7. ST_Read with very large shapefiles

`ST_Read('huge.shp')` reads the whole file into memory before returning. For multi-GB shapefiles, convert externally first or use `read_parquet` with a pre-converted file.

## 8. Mixing Pandas and Arrow result types

```python
result_arrow = con.execute("SELECT * FROM features").arrow()
result_df = con.execute("SELECT * FROM features").df()
```

`.arrow()` is faster (zero-copy in some cases) but geometry columns come back as binary, not Shapely. `.df()` converts to Pandas; geometry columns are still binary unless you cast. There's no built-in "give me a GeoDataFrame" — you have to wrap with GeoPandas yourself.

## 9. `read_csv_auto` and lat/lng schema inference

```python
con.execute("SELECT * FROM 'data.csv'")
# longitude/latitude inferred as VARCHAR if some rows are blank
```

Force types:

```python
con.execute("""
    SELECT * FROM read_csv_auto(
        'data.csv',
        types={'longitude': 'DOUBLE', 'latitude': 'DOUBLE'}
    )
""")
```

Or `CAST(latitude AS DOUBLE)` in the query.

## 10. Extension version drift

DuckDB extensions are pinned to specific DuckDB versions. After a `pip install --upgrade duckdb`, the spatial extension must be re-installed:

```python
con.install_extension("spatial", force_install=True)
con.load_extension("spatial")
```

In long-running services, this isn't an issue — just be aware after upgrades.

## 11. Shutil-clean tempdir between runs

For long-running Python processes that create many DuckDB connections, set the temp directory and clean periodically:

```python
con.execute("SET temp_directory = '/mnt/scratch/duckdb'")
```

Defaults to `/tmp`, which fills fast on small instances when DuckDB spills.

## 12. Parquet schema mismatches across files

When reading multiple Parquet files via glob (`read_parquet('s3://bucket/*.parquet')`), schemas must match. If one file has `geom` as GEOMETRY and another as BLOB (WKB bytes), the read fails.

Normalize at write time:

```sql
COPY (
    SELECT id, ST_GeomFromWKB(geom_blob) AS geom
    FROM read_parquet('s3://bucket/inconsistent/*.parquet')
) TO 's3://bucket/normalized/' (FORMAT PARQUET, PARTITION_BY (state));
```

## 13. Cloud credentials

```python
con.execute("CREATE SECRET (TYPE S3, KEY_ID '...', SECRET '...', REGION 'us-east-1')")
# Hardcoded creds — never check into git
```

Prefer credential chain (IAM role, env vars, instance profile):

```python
con.execute("CREATE SECRET (TYPE S3, PROVIDER CREDENTIAL_CHAIN)")
```

## 14. `ATTACH` to Postgres for spatial — check version compatibility

DuckDB's `postgres` extension does basic spatial passthrough, but `ST_*` functions in the join condition execute on the DuckDB side (data shipped over). For server-side spatial filtering, write the query in Postgres directly instead.

## 15. Quiet failures in COPY

```sql
COPY (SELECT bad_query FROM nonexistent_table) TO 'output.parquet';
-- May produce empty file with no error in some configurations
```

Always verify output:

```python
con.execute("SELECT COUNT(*) FROM 'output.parquet'").fetchone()[0]
```

## Quick checklist

When DuckDB-spatial gives weird results:

- [ ] `LOAD spatial` actually called
- [ ] Distance in degrees is the explanation for "0" / nonsense numbers
- [ ] CRS tracked externally (column name or sidecar)
- [ ] R-tree index used (`EXPLAIN ANALYZE` shows `RTREE_INDEX_JOIN`)
- [ ] Memory limit + temp_directory set for big queries
- [ ] Extension version matches DuckDB version after upgrade
