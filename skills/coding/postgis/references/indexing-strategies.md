# PostGIS Indexing Strategies

## TL;DR

| Index type | Use when | Why |
|---|---|---|
| **GIST** | Always create one on every geometry column you'll filter or join on. | General-purpose; handles geometry, geography, polygons, lines, points, tsvector. Default choice. |
| **SP-GIST** | Point-heavy datasets with uniform spatial distribution. Static tables you build once. | Faster point-in-polygon for points; smaller index size. Slower to build than GIST. |
| **BRIN** | Geometries clustered on disk by ingest order (time-ordered events with locally clustered locations). | Tiny index; only useful when physical row order correlates with spatial location. |
| **B-tree on attributes** | Compound filtering — spatial + temporal + categorical. | Spatial filter narrows candidates; B-tree on `(state, event_date)` finishes the job. Plan for both. |

## Always-create

```sql
CREATE INDEX features_geom_idx ON features USING GIST (geom);
```

For partitioned tables, index every partition (parent index doesn't propagate physical structure):

```sql
CREATE INDEX ON donations_2024 USING GIST (geom);
CREATE INDEX ON donations_2025 USING GIST (geom);
```

After bulk loads, **always** `VACUUM (ANALYZE)`. The GIST index is built but the planner statistics aren't refreshed until you do.

## SP-GIST for points

Worth measuring on point datasets > ~10M rows where the distribution is roughly uniform (no severe clustering):

```sql
CREATE INDEX events_geom_spgist ON events USING SPGIST (geom);
```

Build cost is higher than GIST but query time on `ST_Contains(polygon, point)` against this index can be 30-50% faster on a uniform points table. Test both with `EXPLAIN ANALYZE` on representative queries.

## BRIN — when it actually helps

BRIN is a "summary of summaries." Each block-range entry summarizes the geometry bounding box of N pages. Useful only when:

1. Rows are physically clustered by spatial location (you ingest in spatial order, or you `CLUSTER` the table).
2. Queries hit large contiguous ranges (date ranges that translate to spatial ranges).

```sql
-- Cluster the table by location first
CREATE INDEX features_geohash_btree ON features (geohash(geom));
CLUSTER features USING features_geohash_btree;

-- Then BRIN
CREATE INDEX features_geom_brin ON features USING BRIN (geom);
```

If you don't `CLUSTER` first, BRIN is useless on geometry — block ranges contain bounding boxes covering the entire dataset.

## Index size and bloat

GIST indexes bloat fast under workloads with frequent updates or deletes. Track:

```sql
SELECT
    schemaname, relname AS table,
    indexrelname AS index,
    pg_size_pretty(pg_relation_size(indexrelid)) AS size,
    idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
JOIN pg_index USING (indexrelid)
WHERE indrelid::regclass::text LIKE '%features%';
```

Watch the index size relative to table size. A GIST index larger than the table itself is bloated. Reindex:

```sql
REINDEX INDEX CONCURRENTLY features_geom_idx;
```

`CONCURRENTLY` is critical in production. See [`vacuuming-and-bloat.md`](vacuuming-and-bloat.md).

## Functional indexes — usually a smell

Tempting but slow:

```sql
-- BAD — index unused; ST_Transform on the indexed column blocks index use
CREATE INDEX bad ON features USING GIST (ST_Transform(geom, 5070));
```

If you need a different SRID for distance/area work, store it as a separate column and index that:

```sql
ALTER TABLE features ADD COLUMN geom_5070 geometry(Geometry, 5070);
UPDATE features SET geom_5070 = ST_Transform(geom, 5070);
CREATE INDEX features_geom_5070_idx ON features USING GIST (geom_5070);
```

Pay the storage cost once for query speed forever.

## Multi-column compound queries

Real workloads filter on more than geometry. Add B-tree indexes on the discriminating columns:

```sql
CREATE INDEX features_state_idx ON features (state);
CREATE INDEX features_event_date_idx ON features (event_date);
```

The planner may choose a B-tree to filter `state = 'TX' AND event_date >= ...`, then apply the spatial test on the smaller candidate set. EXPLAIN to verify which index runs first; sometimes you'll want a partial index:

```sql
CREATE INDEX features_geom_tx_idx ON features USING GIST (geom)
WHERE state = 'TX';
```

## Cost-of-build vs query-speed tradeoff

| Operation | GIST cost | SP-GIST cost | BRIN cost |
|---|---|---|---|
| Build (1M rows) | minutes | longer | seconds |
| Build (100M rows) | hour+ | hours | minutes |
| Query (point lookup) | fast | faster (uniform points) | slow unless clustered |
| Query (polygon range) | fast | comparable | slow unless clustered |
| Update (per-row) | per-row index update | comparable | bulk-recalculates the affected page range — cheap |

In ETL pipelines that rebuild tables nightly, BRIN can be appealing for the build cost alone — but only if the access pattern matches.
