# SQL Reference

Detailed type tables, PostGIS patterns, SparkSQL operations, dialect differences, and production gotchas. Referenced by the main skill.

## PostgreSQL Gotchas

Production failure modes. These are counter-intuitive behaviors that cause real bugs.

### Use JSONB, Not JSON

```sql
-- JSON: stored as text, parsed on every access, no indexing
-- JSONB: binary format, indexable, supports containment operators
CREATE TABLE events (data JSONB);  -- not JSON

-- JSONB supports GIN indexes for fast containment queries
CREATE INDEX ON events USING GIN (data);
SELECT * FROM events WHERE data @> '{"type": "donation"}';
```

`JSON` preserves whitespace and key order (rarely useful). `JSONB` is faster for everything else.

### Use timestamptz, Not timestamp

```sql
-- timestamp: no timezone, ambiguous — "2024-03-15 14:00:00" in which timezone?
-- timestamptz: stores UTC, converts to session timezone on display
ALTER TABLE donations ADD COLUMN created_at TIMESTAMPTZ DEFAULT NOW();
```

`timestamp` silently drops timezone information. If your server moves or your session timezone changes, all your times are wrong.

### Use Cursor Pagination, Not OFFSET

```sql
-- BAD: OFFSET scans and discards rows — O(n) for page n
SELECT * FROM donations ORDER BY id LIMIT 20 OFFSET 10000;
-- Scans 10,020 rows to return 20

-- GOOD: Cursor pagination — O(1) regardless of page depth
SELECT * FROM donations WHERE id > :last_seen_id ORDER BY id LIMIT 20;
-- Seeks directly to the cursor position via index
```

OFFSET gets slower on every page. At page 500 of a 10M-row table, it's scanning 10,000 rows to return 20.

### Use SKIP LOCKED for Queues

```sql
-- BAD: SELECT FOR UPDATE blocks all other workers on the same rows
BEGIN;
SELECT * FROM job_queue WHERE status = 'pending' ORDER BY created_at LIMIT 1 FOR UPDATE;
-- All other workers block here until this transaction commits

-- GOOD: SKIP LOCKED lets workers grab different rows concurrently
BEGIN;
SELECT * FROM job_queue WHERE status = 'pending' ORDER BY created_at LIMIT 1
FOR UPDATE SKIP LOCKED;
-- Other workers skip this row and grab the next one
UPDATE job_queue SET status = 'processing' WHERE id = :id;
COMMIT;
```

### Diagnostic Queries

Run these to find problems before they find you.

```sql
-- Find missing indexes: tables with sequential scans but no index scans
SELECT schemaname, relname, seq_scan, idx_scan,
       seq_scan - idx_scan AS too_many_seq_scans
FROM pg_stat_user_tables
WHERE seq_scan > idx_scan AND seq_scan > 1000
ORDER BY too_many_seq_scans DESC;

-- Find unused indexes (candidates for removal)
SELECT schemaname, indexrelname, idx_scan, pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE idx_scan = 0 AND schemaname NOT IN ('pg_catalog')
ORDER BY pg_relation_size(indexrelid) DESC;

-- Find table bloat (dead rows consuming space)
SELECT schemaname, relname, n_dead_tup, n_live_tup,
       ROUND(n_dead_tup::numeric / GREATEST(n_live_tup, 1) * 100, 1) AS dead_pct
FROM pg_stat_user_tables
WHERE n_dead_tup > 10000
ORDER BY n_dead_tup DESC;

-- Find slow queries (requires pg_stat_statements extension)
SELECT query, calls, mean_exec_time, total_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Find lock contention
SELECT blocked.pid AS blocked_pid, blocked_activity.query AS blocked_query,
       blocking.pid AS blocking_pid, blocking_activity.query AS blocking_query
FROM pg_catalog.pg_locks blocked
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked.pid = blocked_activity.pid
JOIN pg_catalog.pg_locks blocking ON blocked.locktype = blocking.locktype
  AND blocked.relation = blocking.relation AND blocked.pid != blocking.pid
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking.pid = blocking_activity.pid
WHERE NOT blocked.granted;
```

## PostgreSQL Data Types

| Use | Type | Not |
|-----|------|-----|
| Money amounts | `NUMERIC(12,2)` | `FLOAT`, `MONEY`, `REAL` |
| Identifiers (external) | `TEXT` | `VARCHAR(n)` unless there's a real constraint |
| Identifiers (internal) | `UUID` with `gen_random_uuid()` | Serial integers for distributed systems |
| Timestamps | `TIMESTAMPTZ` | `TIMESTAMP` (loses timezone) |
| Dates | `DATE` | `TEXT` with format conventions |
| Yes/no flags | `BOOLEAN` | `INTEGER` 0/1, `CHAR(1)` Y/N |
| JSON data | `JSONB` | `JSON` (no indexing), `TEXT` |
| IP addresses | `INET` | `TEXT` |

## PostgreSQL Indexing Strategy

```sql
-- B-tree: equality and range queries (default)
CREATE INDEX ON donations (committee_id);
CREATE INDEX ON donations (contribution_date);

-- Composite: for queries that filter on both columns (left-to-right)
CREATE INDEX ON donations (state, contribution_date);

-- Partial: when you only query a subset
CREATE INDEX ON donations (amount) WHERE amount > 200;

-- GIN: for JSONB, full-text search, array containment
CREATE INDEX ON filings USING GIN (metadata);

-- GiST: for geometry, range types, nearest-neighbor
CREATE INDEX ON boundaries USING GIST (geom);
```

**Rules:**
- Index columns you filter on (`WHERE`), join on (`ON`), or sort on (`ORDER BY`)
- Composite indexes: put equality columns first, range columns last
- Don't index columns with very low cardinality (boolean, status with 3 values) unless it's a partial index
- Drop unused indexes — they slow writes and waste space (`pg_stat_user_indexes.idx_scan = 0`)

## PostgreSQL Transactions and Locking

```sql
-- Explicit transactions for multi-step operations
BEGIN;
    UPDATE committees SET total_raised = total_raised + 500 WHERE id = 'C00703975';
    INSERT INTO donations (committee_id, amount, ...) VALUES ('C00703975', 500, ...);
COMMIT;

-- Use SELECT ... FOR UPDATE when you need to read-then-write atomically
BEGIN;
    SELECT total_raised FROM committees WHERE id = 'C00703975' FOR UPDATE;
    -- row is now locked until COMMIT
    UPDATE committees SET total_raised = ... WHERE id = 'C00703975';
COMMIT;
```

## PostGIS

### When to Use PostGIS vs. Alternatives

See the **Spatial Analysis** skill for the full decision framework. Quick rule of thumb:

| Situation | Use |
|-----------|-----|
| Point-in-polygon assignment for < 10M rows | PostGIS |
| Spatial joins across large datasets on a single machine | PostGIS |
| Distributed spatial joins across billions of rows | Spark + Sedona |
| One-off exploration / visualization | GeoPandas |
| ZIP-to-district lookup (no geometry needed) | String join on a crosswalk table |

### Geometry Basics

```sql
-- Store geometries in EPSG:4326 (WGS84 lat/lng) for storage
-- Transform to a projected CRS for distance/area calculations

-- Create a point from lat/lng
SELECT ST_SetSRID(ST_MakePoint(-97.7431, 30.2672), 4326) AS geom;

-- Create a point using geography type (for distance in meters)
SELECT ST_MakePoint(-97.7431, 30.2672)::geography AS geog;

-- Always store with SRID
ALTER TABLE locations ADD COLUMN geom GEOMETRY(Point, 4326);
CREATE INDEX ON locations USING GIST (geom);
```

### Common Spatial Queries

```sql
-- Point-in-polygon: which district contains this address?
SELECT d.district_id, d.name
FROM district_boundaries AS d
WHERE ST_Contains(d.geom, ST_SetSRID(ST_MakePoint(-97.74, 30.27), 4326));

-- Spatial join: assign all donations to their districts
SELECT don.id, don.amount, dist.district_id
FROM donations AS don
INNER JOIN district_boundaries AS dist
    ON ST_Contains(dist.geom, don.geom);

-- Nearest neighbor: find the 5 closest polling places
SELECT p.name, ST_Distance(p.geom::geography, my_point::geography) AS dist_meters
FROM polling_places AS p
ORDER BY p.geom <-> ST_SetSRID(ST_MakePoint(-97.74, 30.27), 4326)
LIMIT 5;

-- Area calculation (transform to appropriate projected CRS first)
SELECT
    district_id,
    ST_Area(ST_Transform(geom, 3857)) / 1e6 AS area_km2
FROM district_boundaries;
```

### PostGIS Performance

```sql
-- ALWAYS use a spatial index (GiST)
CREATE INDEX ON district_boundaries USING GIST (geom);

-- Use && (bounding box overlap) for fast pre-filtering
-- ST_Contains/ST_Intersects already use the index, but explicit && helps in complex queries
SELECT *
FROM boundaries
WHERE geom && ST_MakeEnvelope(-98, 30, -97, 31, 4326)
    AND ST_Contains(geom, my_point);

-- For bulk spatial joins, cluster the table on the spatial index
CLUSTER district_boundaries USING district_boundaries_geom_idx;

-- Use ST_Subdivide for complex polygons (>500 vertices)
-- Breaks one complex polygon into many simple ones for faster containment tests
INSERT INTO boundaries_subdivided (district_id, geom)
SELECT district_id, ST_Subdivide(geom, 256)
FROM district_boundaries;
```

## SparkSQL vs PostgreSQL Differences

| Feature | PostgreSQL | SparkSQL |
|---------|-----------|----------|
| String concat | `\|\|` | `CONCAT()` or `\|\|` |
| Regex match | `~` / `~*` | `RLIKE` / `REGEXP` |
| Current timestamp | `NOW()` / `CURRENT_TIMESTAMP` | `CURRENT_TIMESTAMP()` |
| Type casting | `column::TYPE` | `CAST(column AS TYPE)` |
| Upsert | `INSERT ... ON CONFLICT` | `MERGE INTO ... USING` |
| Array access | `array[1]` (1-based) | `array[0]` (0-based) |
| JSON field | `data->>'key'` | `data.key` (struct) or `get_json_object()` |
| Temp tables | `CREATE TEMP TABLE` | `CREATE OR REPLACE TEMP VIEW` |
| Sequences | `SERIAL` / `GENERATED` | Not supported — use UUID or monotonically_increasing_id() |

## SparkSQL Performance

```sql
-- Partitioning: for large tables filtered by a low-cardinality column
CREATE TABLE main.silver.donations (
    id STRING,
    amount DECIMAL(12,2),
    contribution_date DATE,
    state STRING
)
USING DELTA
PARTITIONED BY (state);

-- Caching: for tables read multiple times in one session
CACHE TABLE main.silver.committees;
-- ... use it multiple times ...
UNCACHE TABLE main.silver.committees;

-- Broadcast hint: for small dimension tables in joins
SELECT /*+ BROADCAST(com) */
    don.amount,
    com.committee_name
FROM main.silver.donations AS don
INNER JOIN main.silver.committees AS com
    ON don.committee_id = com.committee_id;

-- Check partition pruning in EXPLAIN
EXPLAIN EXTENDED
SELECT * FROM main.silver.donations WHERE state = 'NJ';
-- Look for: "PartitionFilters: [state = NJ]"
```


# Addendum to coding/sql/reference.md — PostgreSQL Performance

Append this section after the existing dialect-specific content. Scoped to PostgreSQL specifically (PostGIS lives in its own sub-skill).

Draws from:
- **Markus Winand — *SQL Performance Explained* + use-the-index-luke.com** (the index discipline canon)
- **depesz.com (Hubert Lubaczewski) + explain.depesz.com** — EXPLAIN plan reading
- **Laurenz Albe (Cybertec)** — partitioning, isolation, replication
- **Bruce Momjian** — talks on MVCC, VACUUM, streaming replication

---

## Indexes — the main lever

### Pick the index type

| Type | Use for |
|---|---|
| **B-tree** | Default. Equality + range on ordered data. 95% of indexes. |
| **Hash** | Equality only, and only when you're sure. Usually B-tree is just as fast. |
| **GIN** | `jsonb`, array, full-text search (`tsvector`) |
| **GiST** | Geometric data (PostGIS), ranges, full-text |
| **SP-GiST** | Space-partitioning — phone numbers, IP addresses, non-uniform data |
| **BRIN** | Huge tables physically sorted by the indexed column (time-series ingest). Tiny on disk. |

### Composite index ordering (Winand's key insight)

Order matters. Columns used in equality filters go FIRST, range filters LAST:

```sql
-- Query: WHERE cycle = 2024 AND contribution_date BETWEEN '2024-01-01' AND '2024-06-30'
CREATE INDEX donations_cycle_date_idx ON donations (cycle, contribution_date);
-- Good: B-tree can seek to cycle=2024, then range-scan date

-- WRONG order:
CREATE INDEX donations_date_cycle_idx ON donations (contribution_date, cycle);
-- B-tree has to scan entire date range looking for cycle=2024 rows
```

Rule: **columns compared with = go first, then columns compared with <, >, BETWEEN**. Columns used in `ORDER BY` can sometimes be added at the end to avoid a sort.

### Covering (INCLUDE) indexes

```sql
CREATE INDEX donations_donor_idx
    ON donations (contributor_id)
    INCLUDE (amount, contribution_date);
```

Makes the index itself satisfy `SELECT amount, contribution_date WHERE contributor_id = ?` — no heap fetch. Powerful for hot-path queries but adds to index bloat; profile before enabling.

### Partial indexes — a free win for lopsided data

```sql
-- 99% of donations aren't flagged; index only the 1%
CREATE INDEX donations_flagged_idx
    ON donations (id)
    WHERE flagged = true;
```

Tiny index, instant seeks on the common query. Works for any predicate.

### Index anti-patterns

| Pattern | Problem |
|---|---|
| `WHERE UPPER(name) = 'SMITH'` | Index on `name` unused. Use `LOWER`/`UPPER` in the index, or a functional index |
| `WHERE name LIKE '%smith%'` | Leading `%` prevents B-tree use. Trigram (`pg_trgm`) index instead |
| `WHERE date::text = '2024-01-01'` | Cast prevents index use. Compare as date |
| Too many indexes (>10 per table) | Write amplification. Audit with `pg_stat_user_indexes` and drop unused |
| Index on a column with 2 distinct values | Useless. Planner reverts to Seq Scan |

## EXPLAIN — read the plan, always

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) SELECT ...;
```

Paste the output into **explain.depesz.com** for a visual breakdown. Look for:

| Sign | Meaning |
|---|---|
| **Seq Scan** on a big table | Missing or unused index |
| **Nested Loop** with high iterations | Wrong join strategy; usually means one side is underestimated |
| **"rows removed by filter"** | Index didn't narrow enough; add a better predicate to the index |
| **External merge/sort** | `work_mem` too small; query sorts to disk |
| **Bitmap Index Scan** + **Bitmap Heap Scan** | Fine for many matches; inefficient for a handful |
| **"actual time" >> "estimated cost"** | Planner statistics are stale — `ANALYZE` the table |

`BUFFERS` shows actual I/O. If "shared read" is high, you're hitting disk; if "shared hit" is high, cache is warm.

## Statistics

```sql
-- Rebuild stats after bulk load
VACUUM ANALYZE donations;

-- Auto-vacuum settings in postgresql.conf for write-heavy tables
ALTER TABLE donations SET (
    autovacuum_vacuum_scale_factor = 0.05,  -- more aggressive than default 0.2
    autovacuum_analyze_scale_factor = 0.02
);
```

Auto-vacuum defaults are right for low-write tables, too timid for high-write ones. Monitor `pg_stat_user_tables.n_dead_tup` and `last_autovacuum`.

## Partitioning — when and how

Partition when:
- Table > 100M rows AND
- Queries consistently filter on the partition key AND
- Partition maintenance (drop old / add new) is part of the workflow

```sql
-- Declarative range partitioning (PG10+)
CREATE TABLE donations (
    id BIGSERIAL,
    contribution_date DATE NOT NULL,
    amount DECIMAL
) PARTITION BY RANGE (contribution_date);

CREATE TABLE donations_2024 PARTITION OF donations
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
CREATE TABLE donations_2025 PARTITION OF donations
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');

-- Attach per-partition indexes
CREATE INDEX ON donations_2024 (contributor_id);
CREATE INDEX ON donations_2025 (contributor_id);
```

Gotchas:
- Foreign keys from a partitioned table to another table work; FKs pointing *into* a partitioned table have restrictions pre-PG12
- Default partition catches unrouted rows — ALWAYS create one, even if it's empty: `FOR VALUES WITH (MODULUS 1, REMAINDER 0)` or `DEFAULT`
- `pg_partman` automates rolling partitions (drop oldest monthly, etc.)

## MVCC and VACUUM (Momjian's territory)

Postgres stores old row versions until VACUUM reclaims them. On write-heavy tables this creates "bloat":

```sql
-- Check bloat
SELECT schemaname, tablename, n_dead_tup, n_live_tup,
       round(100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 1) AS dead_pct
FROM pg_stat_user_tables
WHERE n_dead_tup > 1000
ORDER BY dead_pct DESC;
```

If `dead_pct > 20%`, autovacuum is losing. Options:
- Increase autovacuum aggressiveness (per-table settings above)
- `VACUUM (FULL, ANALYZE) donations;` — exclusive lock, rewrites the whole table. Offline maintenance only.
- `pg_repack` extension — does VACUUM FULL's work without the exclusive lock. Production-safe.

## Isolation levels — pick deliberately

| Level | Default? | Use for |
|---|---|---|
| Read Uncommitted | No (not actually supported — acts as Read Committed) | Never |
| **Read Committed** | **Yes** | Default; each statement sees a fresh snapshot |
| Repeatable Read | No | Multi-statement analytical queries that need a consistent view |
| Serializable | No | Financial-grade consistency; adds serialization-error retries |

Serializable is not a free lunch — `SQLSTATE 40001` retries become the norm. Don't enable it casually.

## Locking — know the footguns

```sql
-- This locks the whole table for the duration of ALTER
ALTER TABLE donations ADD COLUMN reviewed BOOLEAN NOT NULL DEFAULT false;
-- On a 50M-row table, minutes of lock. Reads blocked.

-- Better: two-step migration
ALTER TABLE donations ADD COLUMN reviewed BOOLEAN;
-- ...backfill in batches, each with its own transaction...
UPDATE donations SET reviewed = false WHERE reviewed IS NULL;
-- ...when backfill is done:
ALTER TABLE donations ALTER COLUMN reviewed SET DEFAULT false;
ALTER TABLE donations ALTER COLUMN reviewed SET NOT NULL;
```

Postgres 11+ added `DEFAULT` without table rewrite for new rows, but `NOT NULL` still requires the rewrite. Laurenz Albe's posts on this are the reference.

## CTEs — no longer an optimization fence (PG12+)

Pre-PG12: CTEs materialized, creating planner boundaries. Post-PG12: CTEs are inlined by default (exceptions: recursive CTEs, `WITH ... AS MATERIALIZED`, CTEs with side effects).

Rule: use CTEs freely for readability. If the planner makes a bad choice, try `WITH cte AS NOT MATERIALIZED (...)` to force inlining.

## Connection pooling

Postgres isn't cheap on connections (~10 MB each). For web workloads:

- **PgBouncer** (session-level pooler) for transactional workloads
- **Odyssey** (Yandex, multi-threaded) for very high concurrency
- **Connection pool from the app** (psycopg_pool, SQLAlchemy pool) for steady-state
- Don't: open 1000 idle connections from your app server and hope

Session vs transaction vs statement pooling:
- `session`: client holds connection for the duration of its session. Compatible with prepared statements, SET, etc.
- `transaction`: connection returned to pool on COMMIT. Breaks `SET`, prepared statements.
- `statement`: connection returned after each query. Breaks transactions. Rarely correct.

## Common mistakes

| Pattern | Impact | Fix |
|---|---|---|
| `SELECT *` in production code | Breaks when column added, extra network | Name columns |
| Implicit casts (`WHERE int_col = '5'`) | Sometimes index-unusable | Cast constants, not columns |
| Updating the whole table in one transaction | Long lock + bloat | Batch updates (`WHERE id BETWEEN ...`) |
| `OR` across different columns in a WHERE | Planner can't combine indexes well | Rewrite as UNION ALL of two indexable queries |
| Nested `ANY(ARRAY(...))` | Planner can't flatten | Rewrite as IN or JOIN |
| Not analyzing after bulk load | Planner uses empty stats | `ANALYZE <table>` or `VACUUM ANALYZE` |
| `COUNT(*)` on huge table | Full scan | Approximate count via `reltuples` from `pg_class` if OK |
| Prepared statements against a pg_bouncer in transaction mode | Silent breakage | Disable prepared statements or switch pooler mode |
| Ignoring `pg_stat_statements` | Flying blind on hot queries | Always install; inspect weekly |

## References

- **Markus Winand** — *SQL Performance Explained* + use-the-index-luke.com (indexing canon)
- **depesz.com** — Hubert Lubaczewski's blog + explain.depesz.com (EXPLAIN plans)
- **Laurenz Albe** — Cybertec PostgreSQL Blog (internals, performance)
- **Bruce Momjian** — momjian.us (lectures on MVCC, VACUUM)
- **PostgreSQL docs + release notes** — postgresql.org/docs (primary reference)
- **`pgTune`** — pgtune.leopard.in.ua (baseline configuration)
- **`pg_stat_statements`** extension — always enable; the single best introspection tool
