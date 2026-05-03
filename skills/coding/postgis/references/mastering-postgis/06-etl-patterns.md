# Ch 6 — ETL with PostGIS

The book's ETL chapter covers staging tables, bulk loads, and pipeline patterns for spatial data flowing into Postgres. Largely current; modern additions include declarative partitioning (PG 10+) and FDW-based ELT.

## The principle

Every spatial ETL pipeline has three responsibilities:

1. **Land the data** — read external source, validate, normalize.
2. **Transform** — reproject, repair geometry, join to canonical IDs.
3. **Promote** — atomic move from staging to production with index/constraint integrity.

The book's prescription: keep the three steps separate. Don't transform during ingest; don't ingest into the production table; don't promote until the data passes validation.

## Stage 1 — Landing

Load into an unindexed `UNLOGGED` staging table:

```sql
CREATE UNLOGGED TABLE features_staging (
    src_id TEXT,
    geom_wkt TEXT,
    attrs JSONB,
    src_srid INTEGER,
    loaded_at TIMESTAMPTZ DEFAULT now()
);
```

Why unlogged + unindexed:
- **`UNLOGGED`** skips WAL — much faster for ephemeral data
- **No indexes** — index updates per-insert kill bulk-load speed
- **`loaded_at`** — for incremental pipelines; lets you `WHERE loaded_at > $last_run`

Bulk load via COPY:

```sql
\copy features_staging (src_id, geom_wkt, attrs, src_srid)
FROM '/path/to/file.csv' WITH CSV HEADER;
```

For 10M+ row loads, `\copy` is the fastest path. `INSERT ... VALUES` per row is 100-1000x slower.

## Stage 2 — Transformation

Validate and normalize in SQL:

```sql
-- Build the canonical geometry column
ALTER TABLE features_staging ADD COLUMN geom geometry(MultiPolygon, 4326);

UPDATE features_staging
SET geom = ST_Multi(  -- coerce to MultiPolygon (handles single polygon → multi)
    ST_MakeValid(  -- repair invalid geometry
        ST_Transform(  -- reproject to canonical CRS
            ST_GeomFromText(geom_wkt, src_srid),
            4326
        )
    )
);

-- Validate
SELECT COUNT(*) AS n_invalid FROM features_staging WHERE NOT ST_IsValid(geom);
SELECT COUNT(*) AS n_empty FROM features_staging WHERE ST_IsEmpty(geom);
SELECT COUNT(*) AS n_null FROM features_staging WHERE geom IS NULL;
```

If counts are non-zero, decide:
- **Drop the bad rows** (with logging) — common for civic data
- **Repair** (most cases handled by `ST_MakeValid`)
- **Halt the pipeline** — for authoritative data where you can't drop silently

The book emphasizes: **never silently drop rows.** Always log what you removed and why.

## Stage 3 — Promotion

Atomic move from staging to production:

```sql
BEGIN;

-- Drop indexes on production temporarily (faster INSERT)
DROP INDEX IF EXISTS features_geom_idx;

-- Insert validated rows
INSERT INTO features (src_id, geom, attrs)
SELECT src_id, geom, attrs
FROM features_staging
WHERE ST_IsValid(geom) AND NOT ST_IsEmpty(geom);

-- Recreate index
CREATE INDEX features_geom_idx ON features USING GIST (geom);

-- Drop staging
DROP TABLE features_staging;

COMMIT;

-- Update planner stats
VACUUM (ANALYZE, VERBOSE) features;
```

The transaction guarantees all-or-nothing. If anything fails, rollback leaves production untouched.

For very large production tables, dropping/recreating the index is itself slow. Alternative: keep the index, accept slower INSERT, but you avoid the rebuild cost.

## Idempotency

The book's strong principle: **ETL should be re-runnable without duplicates or side effects.**

### UPSERT pattern

```sql
INSERT INTO features (src_id, geom, attrs)
SELECT src_id, geom, attrs FROM features_staging
ON CONFLICT (src_id) DO UPDATE
    SET geom = EXCLUDED.geom,
        attrs = EXCLUDED.attrs,
        updated_at = now();
```

`ON CONFLICT` requires a unique constraint on `src_id`. Define it; the constraint is what makes the operation idempotent.

### Soft-delete pattern

For data that may legitimately disappear from source:

```sql
-- Mark all rows as "not seen this run"
UPDATE features SET seen_in_run = false;

-- Upsert from staging; flips seen_in_run to true
INSERT INTO features (src_id, geom, attrs, seen_in_run)
SELECT src_id, geom, attrs, true FROM features_staging
ON CONFLICT (src_id) DO UPDATE
    SET geom = EXCLUDED.geom, attrs = EXCLUDED.attrs, seen_in_run = true;

-- Soft-delete rows not seen in this run
UPDATE features SET deleted_at = now() WHERE NOT seen_in_run AND deleted_at IS NULL;
```

Preferable to hard delete in civic work — you can recover from a bad source-data run.

## Incremental loads

If the source supports it, only ingest changed rows:

```sql
-- Source has updated_at; only fetch rows newer than last run
SELECT max(loaded_at) FROM features;  -- = last_run_timestamp
\copy features_staging FROM PROGRAM 'curl ...?since=$LAST_RUN' WITH CSV HEADER;
```

For sources without timestamps, hash-based detection:

```sql
-- Add a content hash column at ingest time
UPDATE features_staging SET content_hash = md5(geom_wkt || COALESCE(attrs::text, ''));

-- UPSERT only rows where the hash differs
INSERT INTO features (src_id, geom, attrs, content_hash)
SELECT src_id, geom, attrs, content_hash FROM features_staging
ON CONFLICT (src_id) DO UPDATE
    SET geom = EXCLUDED.geom, attrs = EXCLUDED.attrs, content_hash = EXCLUDED.content_hash
    WHERE features.content_hash != EXCLUDED.content_hash;  -- only if changed
```

Avoids unnecessary writes; keeps `updated_at` semantically meaningful.

## Partitioning for time-series ETL (post-book)

PostgreSQL 10+ added declarative partitioning. For time-series spatial data (events, observations):

```sql
CREATE TABLE events (
    id BIGSERIAL,
    geom geometry(Point, 4326),
    occurred_at TIMESTAMPTZ NOT NULL,
    attrs JSONB
) PARTITION BY RANGE (occurred_at);

CREATE TABLE events_2024 PARTITION OF events
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

CREATE INDEX ON events_2024 USING GIST (geom);
```

Benefits:
- **Detach old partitions** for archival / deletion (instant; no DELETE scan)
- **Per-partition ANALYZE** keeps planner stats fresh on the active partition
- **Partition-wise joins** when joining time-series spatial data to similarly-partitioned tables

The book uses inheritance-based partitioning (now legacy). Use declarative for new work.

## Change detection patterns

For "what changed since the last run," beyond per-row hashes:

### Geometry change detection

```sql
-- Compare new vs current geometry; flag changes
SELECT
    s.src_id,
    CASE
        WHEN f.geom IS NULL THEN 'new'
        WHEN NOT ST_Equals(s.geom, f.geom) THEN 'changed'
        ELSE 'unchanged'
    END AS status
FROM features_staging s
LEFT JOIN features f ON s.src_id = f.src_id;
```

`ST_Equals` is exact equality. For "approximately equal" (tolerance for float drift):

```sql
WHEN ST_HausdorffDistance(s.geom, f.geom) > 0.001 THEN 'changed'
```

### Attribute change detection

For JSONB attribute columns, compare keys:

```sql
SELECT s.src_id, jsonb_diff(s.attrs, f.attrs) AS diff
FROM features_staging s
JOIN features f USING (src_id)
WHERE s.attrs != f.attrs;
```

(Define `jsonb_diff` as a helper function; PostgreSQL 14+ has `jsonb_path_ops` for finer-grained queries.)

## Logging and observability

Every ETL run should log:
- Source location and timestamp
- Row counts at each stage (landed, transformed, validated, inserted, updated, soft-deleted)
- Validation failures (counts + sample of bad rows)
- Wall-clock duration per stage
- Final table row count

Persist to a `etl_runs` table:

```sql
CREATE TABLE etl_runs (
    id BIGSERIAL,
    pipeline TEXT,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    source TEXT,
    rows_landed INTEGER,
    rows_inserted INTEGER,
    rows_updated INTEGER,
    rows_soft_deleted INTEGER,
    rows_invalid INTEGER,
    sample_invalid JSONB,
    notes TEXT
);
```

Six months later, when someone asks "why did county count go from 3,143 to 3,141?", `etl_runs` is your answer.

## Pitfalls

- **Transforming in the production table during INSERT** — index updates per row are catastrophic.
- **Forgetting `VACUUM ANALYZE` after promotion** — planner uses stale stats; queries get bad plans for hours.
- **No transaction around promotion** — partial failure leaves production in an inconsistent state.
- **No idempotency guarantee** — re-running the pipeline duplicates rows (no UPSERT) or corrupts (hard delete + load).
- **Silent row drop during validation** — six months later, no record of what was discarded or why.
- **`ST_Equals` for change detection on float-coord geometries** — float drift makes everything "changed." Use `ST_HausdorffDistance` with a tolerance.
- **Per-run TRUNCATE + re-load** — slow, breaks foreign keys, no atomic transition. Use UPSERT instead.
- **Loading raw shapefile via `ogr2ogr` directly to production** — no staging means no validation step. Always stage first.

## SU helpers — `siege_utilities` for source fetching

For Census / GADM / OSM sources, don't `wget` shapefiles. SU's `geo.spatial_data.get_geographic_boundaries()` returns a GeoDataFrame ready to push to PostGIS via `gdf.to_postgis(...)`. See [`../siege-utilities-postgis.md`](../siege-utilities-postgis.md) for the per-task map.

## Cross-links

- [`01-importing-data.md`](01-importing-data.md) — bulk-load tools (`shp2pgsql`, `ogr2ogr`, COPY, FDW)
- [`../siege-utilities-postgis.md`](../siege-utilities-postgis.md) — SU helpers for spatial data sourcing
- [`../indexing-strategies.md`](../indexing-strategies.md) — when to drop/recreate indexes during ETL
- [`../vacuuming-and-bloat.md`](../vacuuming-and-bloat.md) — VACUUM after every load
- [`coding/pipeline-jobs/SKILL.md`](../../../pipeline-jobs/SKILL.md) — pipeline orchestration patterns

## Citation

Witkowski K., Chojnacki B., Mackiewicz M. *Mastering PostGIS*. Packt Publishing, 2017. Chapter 6 ("ETL with PostGIS"). Paraphrase + commentary; not redistribution.
