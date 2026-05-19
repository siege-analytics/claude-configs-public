# Principle: Validate Geometry on Ingest

Invalid geometry breaks operations silently. A self-intersecting polygon's area is wrong. A degenerate ring's centroid is meaningless. A NaN coordinate is `false` in every predicate. The bug surfaces three steps downstream as "the spatial join's row count is wrong."

The rule: **repair at the boundary, not in the middle of a pipeline.**

## What "invalid" means

Different engines / standards have slightly different definitions, but the canonical OGC Simple Features rules:

- **Polygon rings must close** (first and last point identical)
- **Ring orientation matters** (exterior ring CCW, interior rings CW — though many implementations are forgiving)
- **No self-intersections within a ring** (no figure-eight polygons)
- **Interior rings must be inside the exterior ring**
- **Interior rings can't intersect each other**
- **No degenerate primitives** (zero-area triangles, zero-length lines, NaN coordinates)

Real-world data violates these constantly:
- Census TIGER occasionally ships polygons with float-precision self-intersections
- Hand-digitized boundaries have drift between adjacent vertices
- Conversion from KML / shapefile / GeoJSON sometimes drops the closing vertex
- "Bowtie" polygons — `[(0,0), (2,2), (0,2), (2,0), (0,0)]` — a single ring that crosses itself

## Per-engine implementation

### PostGIS

```sql
-- Detect
SELECT id, ST_IsValidReason(geom) FROM features WHERE NOT ST_IsValid(geom);

-- Repair (in place)
UPDATE features SET geom = ST_MakeValid(geom) WHERE NOT ST_IsValid(geom);

-- Constrain at table level
ALTER TABLE features ADD CONSTRAINT features_geom_valid CHECK (ST_IsValid(geom));
```

`ST_MakeValid(geom)` preserves dimensionality (polygons stay polygons; bowties become MultiPolygons of two triangles). The legacy `ST_Buffer(geom, 0)` trick is cheaper but lossier.

### GeoPandas / Shapely

```python
from shapely.validation import make_valid, explain_validity

# Detect
invalid_mask = ~gdf.geometry.is_valid
print(gdf[invalid_mask].apply(lambda r: explain_validity(r.geometry), axis=1))

# Repair
gdf["geometry"] = gdf.geometry.apply(make_valid)
```

`make_valid` is Shapely 2.x; older code used `geom.buffer(0)` (same caveat as PostGIS).

### Sedona

```python
df = df.withColumn("geom", expr("ST_MakeValid(geom)"))

# Or filter
df_valid = df.filter("ST_IsValid(geom)")
```

### DuckDB-spatial

```sql
SELECT id FROM features WHERE NOT ST_IsValid(geom);
UPDATE features SET geom = ST_MakeValid(geom) WHERE NOT ST_IsValid(geom);
```

DuckDB's GEOS handles `ST_MakeValid` the same way PostGIS does.

## Why "ingest, not middle"

A pipeline shape:

```
source.shp
  ↓ ingest (validate here)
features (clean)
  ↓ spatial join
features_with_district
  ↓ aggregation
district_summaries
```

If validation happens at ingest, every downstream step has a clean foundation. If validation happens at the spatial join, you've already done two stages of work and discover invalid rows late. If it happens later, you have wrong aggregations and no signal pointing at the cause.

**Practical rule:** every ingest pipeline has an explicit validation step right after the source read. If you skip it because "the source is canonical," you'll find out it isn't the day a downstream join silently drops 12 rows.

## Repair vs drop vs halt

When validation finds invalid rows, three responses:

1. **Repair** — `ST_MakeValid` and continue. Fine when the repair is safe (most simple cases) and you're OK with the changed geometry.
2. **Drop** — exclude invalid rows from production. Fine for civic data where the missing rows are noise, *if you log them*.
3. **Halt** — fail the pipeline; require human review. Right answer for authoritative data where you can't drop silently.

**Never silently drop.** Always log:

```sql
-- During ETL
INSERT INTO etl_log (run_id, message, details)
SELECT
    current_setting('etl.run_id'),
    'Dropped invalid geometry',
    jsonb_build_object('count', COUNT(*), 'sample_ids', array_agg(id))
FROM staging WHERE NOT ST_IsValid(geom);

DELETE FROM staging WHERE NOT ST_IsValid(geom);
```

Six months later, when someone asks "why did county count change?", the log is your answer.

## Validity at table-creation time

Constrain the column so invalid geometry can't enter:

```sql
ALTER TABLE features ADD CONSTRAINT features_geom_valid CHECK (ST_IsValid(geom));
```

This makes invalid INSERTs fail fast. Useful in production tables; less useful in staging tables (you want to land the data and validate, not error during landing).

GeoPandas has no built-in constraint mechanism — validate explicitly at write boundary. For PostgreSQL-backed projects, prefer the database-side constraint as the safety net.

## Validity vs emptiness vs nullness

Three distinct conditions, often confused:

| Condition | Meaning | Test |
|---|---|---|
| **NULL** | No geometry at all | `geom IS NULL` |
| **Empty** | Valid but empty geometry (e.g., `'POINT EMPTY'`) | `ST_IsEmpty(geom)` / `geom.is_empty` |
| **Invalid** | Geometry exists but violates SFA rules | `NOT ST_IsValid(geom)` / `not geom.is_valid` |

A row can be all three (NULL) or any combination. Predicates handle them differently:

- `ST_Within(NULL, polygon)` returns NULL → filtered out by WHERE
- `ST_Within('POINT EMPTY', polygon)` returns FALSE
- `ST_Within(invalid_polygon, point)` returns wrong-but-non-NULL result

The "silent rows missing" bug is most often NULL geometries getting filtered out of spatial joins. Always check:

```sql
SELECT
    COUNT(*) FILTER (WHERE geom IS NULL) AS n_null,
    COUNT(*) FILTER (WHERE ST_IsEmpty(geom)) AS n_empty,
    COUNT(*) FILTER (WHERE NOT ST_IsValid(geom)) AS n_invalid
FROM features;
```

## Engine-specific validity-model differences

**Don't assume:** all engines have the same validity model.

| Engine | Validity model | Repair function |
|---|---|---|
| PostGIS (GEOS) | OGC SFA | `ST_MakeValid` |
| Shapely 2.x (GEOS) | OGC SFA | `make_valid` |
| DuckDB-spatial (GEOS) | OGC SFA | `ST_MakeValid` |
| Sedona (JTS) | JTS, slightly different from GEOS at the edges | `ST_MakeValid` |

For most cases the differences don't matter. For edge cases (very degenerate input geometries, mixed-dimension collections), the same input may validate differently between GEOS and JTS. If you cross engines for the same geometry, validate in both before relying on the result.

## Performance note

`ST_IsValid` and `ST_MakeValid` are not cheap on complex polygons (linear in vertex count). For huge ingest jobs (10M+ polygons):

- Validate in batches; don't `UPDATE ... WHERE NOT ST_IsValid(geom)` over the whole table at once
- Consider parallel workers for the validation pass
- Add the `CHECK` constraint after bulk validation, not during

For point data, validation is essentially free.

## Pitfalls

- **No validation step in the ingest pipeline.** The default failure mode.
- **Validating only at ingest, never on update.** If the production table accepts updates, every update can re-introduce invalid geometry. Use the `CHECK` constraint.
- **Treating `make_valid` as idempotent.** It's not always — bowtie polygons get split into MultiPolygons; a column typed `geometry(Polygon)` will reject the result. Either widen the type to `geometry(MultiPolygon)` or test with `ST_GeometryType` after repair.
- **Not logging dropped rows.** "We discarded 17 rows" with no record of which ones is irrecoverable.
- **`ST_Buffer(geom, 0)` instead of `ST_MakeValid(geom)`.** Cheaper, lossier; can collapse parts of the geometry. Avoid unless you understand the loss.
- **Validating in Python after pulling from a database that already validated.** Wasted work; trust the boundary.
- **Empty geometries treated as `NULL`.** Different conditions; different predicate behavior. Test for both.

## Cross-links

- [`crs-is-meaning.md`](crs-is-meaning.md) — pairs: validate CRS *and* geometry at the boundary
- [`bbox-pre-filter.md`](bbox-pre-filter.md) — invalid geometries can have wrong bounding boxes; pre-filter results may be wrong
- [`../../coding/postgis/references/pitfalls.md`](../../../coding/postgis/references/pitfalls.md) — PostGIS-specific validity debugging
- [`../../coding/geopandas/references/pitfalls.md`](../../../coding/geopandas/references/pitfalls.md) — GeoPandas equivalent
- [`../../coding/sedona/references/pitfalls.md`](../../../coding/sedona/references/pitfalls.md) — Sedona equivalent
