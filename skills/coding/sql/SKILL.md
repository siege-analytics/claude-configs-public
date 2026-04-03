---
name: sql
description: SQL conventions for PostgreSQL, PostGIS, and SparkSQL. Covers query structure, spatial queries, performance patterns, and dialect-specific idioms.
---

# SQL Style

## When to Use This Skill

When writing SQL for PostgreSQL (including PostGIS), SparkSQL, or reviewing queries in either dialect. The conventions here prioritize readability and correctness over cleverness.

## General Formatting

### Keywords and Layout

```sql
-- Keywords: UPPERCASE
-- Identifiers: lowercase_snake_case
-- One clause per line, indented for readability

SELECT
    d.contributor_name,
    d.amount,
    c.committee_name,
    d.contribution_date
FROM donations AS d
INNER JOIN committees AS c
    ON d.committee_id = c.committee_id
WHERE d.contribution_date >= '2024-01-01'
    AND d.amount > 200
ORDER BY d.amount DESC
LIMIT 100;
```

### Naming

```sql
-- Tables: plural nouns
CREATE TABLE donations (...);
CREATE TABLE committees (...);
CREATE TABLE district_boundaries (...);

-- Columns: singular, descriptive
contribution_date    -- not: date, dt, contrib_dt
committee_name       -- not: name, comm_name
zip_code             -- not: zip, postal

-- Aliases: short but meaningful, never single letters in production
FROM donations AS don        -- not: FROM donations d
INNER JOIN committees AS com -- not: INNER JOIN committees c

-- Views: prefixed by purpose
CREATE VIEW v_donor_summary AS ...;
CREATE VIEW v_active_committees AS ...;

-- Indexes: table_column(s)_idx
CREATE INDEX donations_committee_id_idx ON donations (committee_id);
CREATE INDEX donations_zip_date_idx ON donations (zip_code, contribution_date);
```

### CTEs Over Subqueries

Use Common Table Expressions (CTEs) to break complex queries into named steps. Each CTE should do one thing.

```sql
-- Good: readable, each step is named and testable
WITH donor_totals AS (
    SELECT
        contributor_name,
        SUM(amount) AS total_given,
        COUNT(*) AS donation_count
    FROM donations
    WHERE contribution_date >= '2024-01-01'
    GROUP BY contributor_name
),
top_donors AS (
    SELECT *
    FROM donor_totals
    WHERE total_given > 10000
    ORDER BY total_given DESC
)
SELECT
    td.contributor_name,
    td.total_given,
    td.donation_count
FROM top_donors AS td;

-- Bad: nested subqueries
SELECT * FROM (
    SELECT contributor_name, SUM(amount) AS total
    FROM (SELECT * FROM donations WHERE ...) sub1
    GROUP BY contributor_name
) sub2 WHERE total > 10000;
```

**When CTEs hurt:** PostgreSQL before v12 materializes every CTE. In older versions, if you need the optimizer to push predicates into a CTE, use a subquery instead. PostgreSQL 12+ inlines CTEs automatically when possible.

### Window Functions

Use window functions for ranking, running totals, and comparisons within groups.

```sql
-- Rank donors within each state
SELECT
    contributor_name,
    state,
    total_given,
    RANK() OVER (PARTITION BY state ORDER BY total_given DESC) AS state_rank
FROM donor_totals;

-- Running total by date
SELECT
    contribution_date,
    amount,
    SUM(amount) OVER (ORDER BY contribution_date) AS running_total
FROM donations
WHERE committee_id = 'C00703975';

-- Compare to previous period
SELECT
    month,
    total_raised,
    LAG(total_raised) OVER (ORDER BY month) AS prev_month,
    total_raised - LAG(total_raised) OVER (ORDER BY month) AS change
FROM monthly_totals;
```

## PostgreSQL-Specific

### Data Types

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

### EXPLAIN Before Optimizing

Never guess at performance. Always check the query plan first.

```sql
-- See what the planner will do
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT ...;

-- What to look for:
-- Seq Scan on large tables → missing index
-- Nested Loop with high row counts → consider Hash Join
-- Sort with large external sort → increase work_mem or add index
-- Bitmap Heap Scan → good, index is being used
```

### Indexing Strategy

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

### Transactions and Locking

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

## SparkSQL

### Session and Catalog

```sql
-- Use fully qualified names: catalog.schema.table
SELECT * FROM main.silver.donations LIMIT 10;

-- Set the default catalog/schema for the session
USE CATALOG main;
USE SCHEMA silver;

-- Show what's available
SHOW CATALOGS;
SHOW SCHEMAS IN main;
SHOW TABLES IN main.silver;

-- Table metadata
DESCRIBE EXTENDED main.silver.donations;
SHOW CREATE TABLE main.silver.donations;
```

### Delta Lake Operations

```sql
-- Time travel: query a table as of a previous version
SELECT * FROM main.silver.donations VERSION AS OF 5;
SELECT * FROM main.silver.donations TIMESTAMP AS OF '2024-03-15 00:00:00';

-- Merge (upsert): insert new, update existing
MERGE INTO main.gold.committees AS target
USING staging.new_committees AS source
    ON target.committee_id = source.committee_id
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *;

-- Optimize: compact small files and co-locate related data
OPTIMIZE main.silver.donations ZORDER BY (committee_id, contribution_date);

-- Vacuum: remove old files no longer referenced by any version
VACUUM main.silver.donations RETAIN 168 HOURS;

-- History
DESCRIBE HISTORY main.silver.donations;
```

### SparkSQL Performance

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

### SparkSQL vs PostgreSQL Differences

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

## Query Design Principles

### 1. Be Explicit

```sql
-- Good: every column named
SELECT
    contributor_name,
    amount,
    contribution_date
FROM donations;

-- Bad in production: fragile, unclear what you're getting
SELECT * FROM donations;
```

`SELECT *` is fine for exploration. Never use it in views, application queries, or ETL.

### 2. Filter Early

Push `WHERE` conditions as close to the source tables as possible. Don't filter after joining.

```sql
-- Good: filter before join
SELECT don.amount, com.name
FROM donations AS don
INNER JOIN committees AS com ON don.committee_id = com.committee_id
WHERE don.contribution_date >= '2024-01-01';

-- Better if the join is expensive: filter in a CTE
WITH recent_donations AS (
    SELECT * FROM donations WHERE contribution_date >= '2024-01-01'
)
SELECT rd.amount, com.name
FROM recent_donations AS rd
INNER JOIN committees AS com ON rd.committee_id = com.committee_id;
```

### 3. Use the Right Join

| Join | Use When |
|------|----------|
| `INNER JOIN` | You only want rows that match in both tables |
| `LEFT JOIN` | You want all rows from the left table, with NULLs for non-matches |
| `CROSS JOIN` | You need every combination (rare — usually a mistake) |
| `ANTI JOIN` (`LEFT JOIN ... WHERE right.id IS NULL`) | You want rows that do NOT have a match |

Never use implicit joins (comma-separated `FROM` with `WHERE` conditions). Always use explicit `JOIN ... ON`.

### 4. Aggregation Discipline

```sql
-- Every non-aggregated column must be in GROUP BY
SELECT
    state,
    committee_type,
    COUNT(*) AS donation_count,
    SUM(amount) AS total_amount,
    AVG(amount) AS avg_amount
FROM donations
GROUP BY state, committee_type
HAVING SUM(amount) > 100000
ORDER BY total_amount DESC;
```

`HAVING` filters groups after aggregation. `WHERE` filters rows before aggregation. Don't confuse them.

### 5. NULL Awareness

```sql
-- NULL is not a value — it is the absence of a value
-- NULL = NULL is NULL (not TRUE)
-- NULL <> 'anything' is NULL (not TRUE)

-- Check for NULL explicitly
WHERE employer IS NULL          -- not: WHERE employer = NULL
WHERE employer IS NOT NULL

-- COALESCE for defaults
SELECT COALESCE(employer, 'Not reported') AS employer

-- NULL-safe comparison (PostgreSQL)
WHERE employer IS DISTINCT FROM 'RETIRED'

-- NULLs in aggregation: most aggregates skip NULLs
-- COUNT(*) counts all rows; COUNT(column) counts non-NULL values
SELECT
    COUNT(*) AS total_rows,           -- includes NULLs
    COUNT(employer) AS has_employer   -- excludes NULLs
FROM donations;
```

## Attribution Policy

NEVER include AI or agent attribution in queries, migrations, comments, or documentation.
