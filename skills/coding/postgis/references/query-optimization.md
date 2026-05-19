# PostGIS Query Optimization

Beyond indexes — planner reads, parallelism, materialization, and parameter tuning.

## EXPLAIN — what to read

Always `EXPLAIN (ANALYZE, BUFFERS)`, never bare `EXPLAIN`. ANALYZE actually runs; BUFFERS shows I/O.

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT * FROM donations d
JOIN districts_subdivided b ON ST_Contains(b.geom, d.geom)
WHERE d.amount > 1000;
```

What to look for, in order of importance:

1. **Seq Scan on a big table when the WHERE is selective** — index missing or unused. Fix by adding/repairing index, then re-running `ANALYZE`.
2. **Estimated rows ≠ actual rows by >10×** — stats are stale or correlated columns are confusing the planner. `ANALYZE` first; consider `CREATE STATISTICS` for multivariate stats.
3. **Sort spilling to disk** — appears as `external merge` or `Sort Method: external merge Disk: ...`. Bump `work_mem` for the session, or break the query into smaller pieces.
4. **Hash joins on huge tables** — sometimes a Nested Loop with the right index is dramatically faster. Plan-hint with `enable_hashjoin = off` for the session to compare.
5. **Lots of `Heap Blocks: lossy=...`** — `effective_cache_size` may be undersized; planner is over-using bitmap fallback.

## Hot session settings

Useful in interactive analysis:

```sql
SET work_mem = '256MB';                -- per sort/hash; default is tiny (4MB)
SET maintenance_work_mem = '2GB';      -- index builds and VACUUM
SET effective_cache_size = '32GB';     -- planner hint, not allocation
SET max_parallel_workers_per_gather = 4;
SET random_page_cost = 1.1;            -- for SSD; default 4.0 assumes spinning disk
SET geqo_threshold = 12;               -- enable genetic optimizer for big joins
```

In production set these in `postgresql.conf` per the workload. `work_mem` is per-operation so multiply by concurrent backends.

## Materialized views for spatial assignments

If the same spatial join produces an assignment used by many downstream queries, materialize:

```sql
CREATE MATERIALIZED VIEW mv_donation_district AS
SELECT DISTINCT d.id AS donation_id, b.district_id
FROM donations d
JOIN districts_subdivided b ON ST_Contains(b.geom, d.geom);

CREATE INDEX ON mv_donation_district (donation_id);

-- Refresh on schedule
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_donation_district;
```

`CONCURRENTLY` requires a unique index on the view. Plan for it.

## Parallel-aware function authoring

Custom PostGIS-using functions don't get parallelism by default. Mark them `PARALLEL SAFE` if they can:

```sql
CREATE OR REPLACE FUNCTION distance_meters_5070(a geometry, b geometry)
RETURNS double precision AS $$
    SELECT ST_Distance(ST_Transform(a, 5070), ST_Transform(b, 5070));
$$ LANGUAGE SQL IMMUTABLE PARALLEL SAFE;
```

`IMMUTABLE` and `PARALLEL SAFE` together let the planner inline and parallelize. Skip these and the function becomes a serial barrier.

## Avoid round-trips

For batch work, do everything in one query rather than fetching candidates and re-querying. Common anti-pattern in Python:

```python
# BAD — N+1 round trips
for donor_id in donor_ids:
    cur.execute("SELECT district_id FROM districts WHERE ST_Contains(geom, %s)", [point])
```

Replace with a single CTE-driven query and batch the inputs. Use `COPY` to load a temp table of inputs if needed.

## Bulk-load patterns

For 10M+ row spatial loads:

```sql
-- Stage in unlogged table without indexes
CREATE UNLOGGED TABLE features_staging (
    id BIGINT,
    geom geometry
);

\COPY features_staging FROM '/path/to/file.csv' WITH CSV HEADER;

-- Index after the load
CREATE INDEX ON features_staging USING GIST (geom);

-- Move to permanent table
INSERT INTO features SELECT * FROM features_staging;
DROP TABLE features_staging;
```

`UNLOGGED` skips WAL — much faster for staging that you don't need crash-safe. The final `INSERT` is logged.

For repeatable bulk loads (nightly), keep the table partitioned by ingest date and DROP/CREATE individual partitions instead of UPDATE.

## Postgres-side caching: `CLUSTER`

If queries always hit a contiguous range (recent dates, single state), physically reorder rows:

```sql
CREATE INDEX features_state_idx ON features (state);
CLUSTER features USING features_state_idx;
ANALYZE features;
```

Clusters all `'TX'` rows together on disk. Subsequent queries fetch them in sequential I/O. Maintenance: re-cluster after large mutations.

## Connection management

PostGIS queries with large result sets benefit from server-side cursors (Python: `cursor.itersize` in psycopg2; SQLAlchemy: `stream_results=True`). Pulling 10M rows in one fetch crashes both client and server.

For application code, pool connections (`pgbouncer` in transaction mode) — PostGIS extension load is per-connection and expensive on connection churn.

## Track slow queries

```sql
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
```

Then:

```sql
SELECT
    query,
    calls,
    mean_exec_time,
    total_exec_time,
    rows
FROM pg_stat_statements
WHERE query LIKE '%ST_%'
ORDER BY total_exec_time DESC
LIMIT 20;
```

The biggest spatial-query offenders show up here. Prioritize fixing the top 5; ignore long-tail.
