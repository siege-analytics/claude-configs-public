# PostGIS Pitfalls

Mistakes that look right and silently produce wrong results, ordered by frequency in real Siege work.

## SRID mismatch

Two geometries with different SRIDs in a spatial predicate return zero rows or an error:

```sql
-- a.geom is SRID 4326, b.geom is SRID 4269 (NAD83)
SELECT COUNT(*) FROM a JOIN b ON ST_Intersects(a.geom, b.geom);
-- ERROR: Operation on mixed SRID geometries
```

If you `ST_Transform` only one side at query time you block the index. Fix at ingest:

```sql
ALTER TABLE b ALTER COLUMN geom TYPE geometry(Point, 4326)
USING ST_Transform(geom, 4326);
```

## Mixed geometry types in one column

`geometry` columns without a type constraint accept anything. Then `ST_Area(geom)` returns 0 for the points hiding in the column, and you spend an afternoon debugging.

```sql
-- BAD — accepts any geometry type
CREATE TABLE features (id SERIAL, geom geometry);

-- GOOD — typed
CREATE TABLE features (id SERIAL, geom geometry(Polygon, 4326));
```

For mixed-but-valid cases (you really do have a column of polygons + multipolygons), use `geometry(MultiPolygon, 4326)` and cast singles up: `ST_Multi(geom)`.

## 3D coordinates sneaking in

Some shapefile loaders add a Z dimension as 0:

```sql
SELECT ST_NDims(geom) FROM features LIMIT 1;
-- Returns 3 instead of 2 — you have Z coords you didn't ask for
```

Most operations work but a few quietly produce wrong results, and storage is bigger. Strip:

```sql
UPDATE features SET geom = ST_Force2D(geom);
```

## ST_Contains vs ST_Intersects vs ST_Covers

| Function | Returns true when… | Boundary points? |
|---|---|---|
| `ST_Contains(a, b)` | b is entirely inside a | excluded |
| `ST_ContainsProperly(a, b)` | b is strictly inside a (no boundary touch) | excluded |
| `ST_Covers(a, b)` | b is inside a | **included** |
| `ST_Intersects(a, b)` | a and b share any point | included |

For "which polygon does this point fall in," `ST_Contains` *misses* points that land exactly on a boundary. Real-world data has many such points (geocoded centroids of buildings on streets). Use `ST_Covers` or `ST_Intersects` for assignment work.

## ST_Transform on the indexed column

```sql
-- BAD — transforms every row, blocks the index
SELECT * FROM features WHERE ST_Transform(geom, 5070) && bbox_5070;
```

Transform the query input instead:

```sql
-- GOOD — transforms once
SELECT * FROM features WHERE geom && ST_Transform(bbox_5070, 4326);
```

Or store both SRIDs as separate columns and index both.

## Computing area in degrees

```sql
-- Returns a meaningless number — degrees squared
SELECT ST_Area(geom) FROM districts WHERE state = 'TX';
```

Lat/lng coordinates are in degrees. Area in square degrees has no useful meaning (not square miles, not square kilometers). Always project before area/distance/length:

```sql
SELECT ST_Area(ST_Transform(geom, 5070)) AS area_m2 FROM districts WHERE state = 'TX';
```

For Texas specifically, EPSG:5070 (Conus Albers) is fine; for global work pick an equal-area projection.

## ST_Distance on lat/lng

Same family of bug:

```sql
-- Returns a tiny number that looks reasonable but isn't meters
SELECT ST_Distance(a.geom, b.geom) FROM places a, places b LIMIT 5;
```

Either project both sides, use `ST_Distance(a.geom::geography, b.geom::geography)` for spheroidal meters, or use `ST_DistanceSphere` for spherical meters.

## Bounding box with no SRID

```sql
-- ST_MakeEnvelope without SRID returns SRID 0 — won't match indexed columns
SELECT * FROM features WHERE geom && ST_MakeEnvelope(-100, 30, -97, 32);

-- Fix
SELECT * FROM features WHERE geom && ST_MakeEnvelope(-100, 30, -97, 32, 4326);
```

The 5th argument is the SRID. Without it, the bounding box has no projection and PostGIS won't compare it to indexed geometry.

## Subdividing in the WHERE clause

```sql
-- BAD — does the subdivision per query
SELECT * FROM districts WHERE ST_Contains(ST_Subdivide(geom, 256), $1);
```

Subdivide once into a separate table; query the subdivided table. See [`spatial-joins-performance.md`](spatial-joins-performance.md).

## Forgetting to ANALYZE after bulk load

```sql
\COPY features FROM '/path/to/big.csv' WITH CSV HEADER;
-- ... some hours later, queries are slow because planner uses default 1000-row estimates
```

Always run `ANALYZE features;` after bulk loads. Better: `VACUUM (ANALYZE, VERBOSE) features;` so you also reclaim any dead tuples and see what was processed.

## Implicit casts in spatial joins

```sql
-- a.geom is geometry, b.geog is geography
WHERE ST_DWithin(a.geom, b.geog, 1000)
-- Implicit cast geometry → geography on every row of a, no index used
```

Keep both sides the same type. Materialize a `geog` column on the larger side if you need geography semantics for distance.

## NULL geometries

`ST_Contains(NULL, point)` returns NULL, not FALSE. WHERE clauses filter out NULLs, so rows with NULL geometry silently disappear from spatial joins. If your assignment pipeline has unexpected row drops, check:

```sql
SELECT COUNT(*) FROM features WHERE geom IS NULL;
```

## Empty geometries

Different from NULL: `ST_GeomFromText('POINT EMPTY', 4326)` is a valid but empty geometry. `ST_IsEmpty(geom)` returns TRUE; most predicates return FALSE for empty inputs. Coalesce or filter explicitly.

## VACUUM never running on time-partitioned tables

Per-partition autovacuum thresholds are independent. Old partitions that rarely get inserts but get updates can accumulate bloat unnoticed. Set per-partition autovacuum settings explicitly when partitioning. See [`vacuuming-and-bloat.md`](vacuuming-and-bloat.md).
