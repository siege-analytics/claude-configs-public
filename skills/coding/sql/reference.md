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
