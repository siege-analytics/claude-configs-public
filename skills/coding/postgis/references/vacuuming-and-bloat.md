# Vacuuming and Bloat — The Silent Ops Killer

PostGIS GIST indexes bloat fast under update/delete workloads. Spatial query performance degrades quietly until queries that took milliseconds take seconds. This is the most common "PostGIS got slow and we don't know why" cause.

## The mechanism

Postgres MVCC marks updated/deleted rows as dead but doesn't remove them until VACUUM. Indexes accumulate dead pointers. GIST indexes are particularly susceptible because:

1. They have higher per-tuple overhead (bounding-box metadata).
2. Page splits during insert grow the tree unevenly.
3. Dead tuples in GIST can't always be reclaimed in-place — `VACUUM` may need a `REINDEX` to actually recover space.

Symptom: `pg_stat_user_indexes.idx_scan` is high, but query times keep growing. EXPLAIN shows correct index usage; just slow.

## Detection

```sql
-- Index sizes vs table sizes
SELECT
    schemaname || '.' || relname AS table,
    pg_size_pretty(pg_relation_size(relid)) AS table_size,
    indexrelname AS index,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
    ROUND(100.0 * pg_relation_size(indexrelid) / NULLIF(pg_relation_size(relid), 0), 1) AS pct_of_table
FROM pg_stat_user_indexes
JOIN pg_index USING (indexrelid)
WHERE indrelid > 16384  -- user tables only
ORDER BY pg_relation_size(indexrelid) DESC
LIMIT 20;
```

A GIST spatial index 200%+ the table size is bloated. Healthy GIST indexes on geometry columns are usually 10-50% of table size.

```sql
-- Dead tuples
SELECT
    schemaname || '.' || relname AS table,
    n_live_tup,
    n_dead_tup,
    ROUND(100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 1) AS pct_dead,
    last_vacuum,
    last_autovacuum
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC
LIMIT 20;
```

`pct_dead > 20%` means autovacuum isn't keeping up. Tune (below) or vacuum manually.

## Routine maintenance

### Autovacuum — usually undersized for spatial workloads

Default Postgres autovacuum settings target OLTP tables of ~100K rows. PostGIS workloads with multi-million-row spatial tables need:

```sql
ALTER TABLE features SET (
    autovacuum_vacuum_scale_factor = 0.05,    -- vacuum at 5% dead (default 20%)
    autovacuum_analyze_scale_factor = 0.02,   -- analyze at 2% changed (default 10%)
    autovacuum_vacuum_cost_limit = 1000       -- be more aggressive
);
```

This makes autovacuum touch big tables more often with smaller batches — better than long, page-locking vacuums hitting once a week.

### Manual VACUUM

After bulk loads or large updates:

```sql
VACUUM (ANALYZE, VERBOSE) features;
```

`VERBOSE` shows what was reclaimed. `ANALYZE` updates planner stats — critical after bulk changes or the planner uses stale row counts.

### REINDEX for severe bloat

When VACUUM can't recover GIST space:

```sql
REINDEX INDEX CONCURRENTLY features_geom_idx;
```

`CONCURRENTLY` is essential in production — without it, the index is locked for writes for the duration of the rebuild (which on a 100M-row spatial table can be hours).

For very bloated indexes, `REINDEX` halves or quarters the index size, which translates directly to query speedups (less of the index in memory means more cache hits).

## When the table itself is bloated

If `pct_dead` stays high even after VACUUM, the table has internal bloat — pages with mostly-dead tuples that VACUUM can't fully reclaim because of long-running transactions or `VACUUM FULL` aversion.

Options, in order of disruption:

1. **`pg_repack`** (extension) — rebuilds the table online with no exclusive lock. Best for production. Install once: `CREATE EXTENSION pg_repack;`
2. **`CLUSTER`** — rewrites the table sorted by an index. Holds an exclusive lock. Acceptable in maintenance windows.
3. **`VACUUM FULL`** — same outcome as CLUSTER without the sort. Exclusive lock. Last resort.

For partitioned tables, prefer dropping/recreating individual partitions over VACUUM FULL of the whole table.

## Connection pooling and bloat

Long-lived idle transactions block VACUUM from reclaiming dead tuples *anywhere* in the database. They're a common silent cause of bloat.

```sql
SELECT pid, state, xact_start, query_start, state_change, query
FROM pg_stat_activity
WHERE state IN ('idle in transaction', 'idle in transaction (aborted)')
ORDER BY xact_start
LIMIT 20;
```

Anything older than a few minutes is suspicious. Kill with `SELECT pg_terminate_backend(pid);` and trace the offending app code (usually a forgotten transaction, ORM session not closed, etc.).

Connection poolers in transaction mode (pgbouncer) prevent this class of bug.

## Quick-reference checklist

When PostGIS queries are mysteriously slow:

- [ ] `pg_stat_user_tables.n_dead_tup` is < 10% of n_live_tup
- [ ] `last_autovacuum` is recent (within hours, not days)
- [ ] No idle-in-transaction sessions > 5 minutes
- [ ] GIST index sizes < 100% of table sizes
- [ ] After REINDEX, query time improved meaningfully
- [ ] `work_mem` and `maintenance_work_mem` aren't the bottleneck

If all five pass and queries are still slow, the problem isn't bloat — see [`query-optimization.md`](query-optimization.md).
