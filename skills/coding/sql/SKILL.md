---
name: sql
description: SQL conventions for PostgreSQL, PostGIS, and SparkSQL. Covers query structure, performance patterns, and dialect differences.
routed-by: coding-standards
---

# SQL Style

## Companion shelves

For storage-engine reasoning behind query planning (B-tree vs LSM, partitioning, transactions):
- [skill:data-intensive]

Apply these conventions when writing SQL for PostgreSQL (including PostGIS), SparkSQL, or reviewing queries in either dialect. See [reference.md](reference.md) for type tables, PostGIS queries, SparkSQL operations, and dialect differences.

## General Formatting

Keywords UPPERCASE. Identifiers lowercase_snake_case. One clause per line.

```sql
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

## Naming

```sql
-- Tables: plural nouns
CREATE TABLE donations (...);

-- Columns: singular, descriptive
contribution_date    -- not: date, dt, contrib_dt

-- Aliases: short but meaningful, never single letters in production
FROM donations AS don

-- Views: prefixed by purpose
CREATE VIEW v_donor_summary AS ...;

-- Indexes: table_column(s)_idx
CREATE INDEX donations_committee_id_idx ON donations (committee_id);
```

## CTEs Over Subqueries

Use Common Table Expressions to break complex queries into named steps. Each CTE should do one thing.

```sql
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
)
SELECT contributor_name, total_given, donation_count
FROM top_donors
ORDER BY total_given DESC;
```

## Window Functions

```sql
-- Rank within groups
SELECT contributor_name, state, total_given,
    RANK() OVER (PARTITION BY state ORDER BY total_given DESC) AS state_rank
FROM donor_totals;

-- Running total
SELECT contribution_date, amount,
    SUM(amount) OVER (ORDER BY contribution_date) AS running_total
FROM donations;

-- Compare to previous period
SELECT month, total_raised,
    LAG(total_raised) OVER (ORDER BY month) AS prev_month
FROM monthly_totals;
```

## EXPLAIN Before Optimizing

Never guess at performance. Always check the query plan first.

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT ...;
```

What to look for: Seq Scan on large tables (missing index), Nested Loop with high row counts (consider Hash Join), external sort (increase work_mem or add index).

## Query Design Principles

### 1. Be Explicit

Name every column in production queries. `SELECT *` is fine for exploration only.

### 2. Filter Early

Push `WHERE` conditions as close to the source tables as possible. Don't filter after joining.

### 3. Use the Right Join

| Join | Use When |
|------|----------|
| `INNER JOIN` | Only rows that match in both tables |
| `LEFT JOIN` | All rows from left, NULLs for non-matches |
| `CROSS JOIN` | Every combination (rare — usually a mistake) |
| Anti join (`LEFT JOIN ... WHERE right.id IS NULL`) | Rows that do NOT match |

Never use implicit joins (comma-separated `FROM` with `WHERE` conditions).

### 4. Aggregation Discipline

Every non-aggregated column must be in GROUP BY. `HAVING` filters groups after aggregation; `WHERE` filters rows before.

### 5. NULL Awareness

```sql
-- NULL is not a value — it is the absence of a value
WHERE employer IS NULL          -- not: WHERE employer = NULL
SELECT COALESCE(employer, 'Not reported') AS employer

-- COUNT(*) counts all rows; COUNT(column) counts non-NULL values
SELECT COUNT(*) AS total_rows, COUNT(employer) AS has_employer
FROM donations;
```

## Gotchas

Counter-intuitive PostgreSQL behaviors that cause production bugs:

| Default Instinct | Correct Choice | Why |
|-----------------|----------------|-----|
| `JSON` type | `JSONB` | JSON has no indexing, parsed on every access |
| `TIMESTAMP` | `TIMESTAMPTZ` | timestamp silently drops timezone info |
| `OFFSET` pagination | Cursor pagination (`WHERE id > :last`) | OFFSET is O(n) for page n |
| `SELECT FOR UPDATE` for queues | `FOR UPDATE SKIP LOCKED` | FOR UPDATE blocks all workers |
| `VARCHAR(255)` | `TEXT` | PostgreSQL treats them identically; VARCHAR adds a useless constraint |
| `SERIAL` | `GENERATED ALWAYS AS IDENTITY` | SERIAL has surprising edge cases with permissions and sequences |

See [reference.md](reference.md) for diagnostic queries (missing indexes, table bloat, slow queries, lock contention).

## PostgreSQL, PostGIS, and SparkSQL Reference

See [reference.md](reference.md) for:
- PostgreSQL data type recommendations
- Indexing strategy (B-tree, composite, partial, GIN, GiST)
- Transaction and locking patterns
- PostGIS geometry basics, spatial queries, and performance tuning
- SparkSQL dialect differences from PostgreSQL
- SparkSQL performance (partitioning, caching, broadcast hints)

## Attribution Policy

NEVER include AI or agent attribution in queries, migrations, comments, or documentation.
