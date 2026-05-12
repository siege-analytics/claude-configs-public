# Ch 7 — PostGIS Programming (PL/pgSQL)

The book's programming chapter covers stored functions, triggers, custom aggregates. All current; the modern addition is `PARALLEL SAFE` annotations (PG 9.6+) and improved JIT compilation (PG 11+).

## When to write PL/pgSQL functions

Stored functions earn their complexity when:

- The same logic appears in 5+ queries — encapsulate it
- The logic involves spatial operations that benefit from inlining (the planner can sometimes optimize through `IMMUTABLE` functions)
- You need a trigger (validation, history table, denormalization)
- The logic is too complex for a CTE but doesn't warrant a full application layer

Don't write functions when:
- The logic is one-off — a CTE or subquery is clearer
- The function obscures behavior that should be explicit in the query
- The function makes the query non-portable (other databases can't run PL/pgSQL)

## A canonical pattern — distance helper

```sql
CREATE OR REPLACE FUNCTION distance_meters(
    a geometry,
    b geometry,
    DEFAULT_PROJ INTEGER DEFAULT 5070
) RETURNS double precision AS $$
    SELECT ST_Distance(
        ST_Transform(a, DEFAULT_PROJ),
        ST_Transform(b, DEFAULT_PROJ)
    );
$$ LANGUAGE SQL IMMUTABLE PARALLEL SAFE;
```

Three annotations matter:
- **`LANGUAGE SQL`** — for simple expression-based functions, faster than PL/pgSQL because it can be inlined
- **`IMMUTABLE`** — same input → same output; planner can cache and parallelize
- **`PARALLEL SAFE`** — eligible for parallel query execution

Without these, the planner treats the function as a black box and runs it serially per row. With them, it inlines into the query and respects parallelism.

## Function volatility classes

| Class | Meaning | Use when |
|---|---|---|
| **IMMUTABLE** | Same input → same output, always | Pure spatial math; format conversions |
| **STABLE** | Same input → same output, within a query | Functions that read tables (snapshots) |
| **VOLATILE** | May differ between calls | Functions with side effects (`now()`, INSERT) |

Default is `VOLATILE` — slowest. Annotate as strictly as truthful for your function.

## Parallel safety

```sql
SELECT proname, proparallel
FROM pg_proc
WHERE proname LIKE 'st_%'
ORDER BY proname;
```

`proparallel`: `s` = safe, `r` = restricted, `u` = unsafe. Most ST_* functions are safe; some (like `ST_AsMVT_Aggr`) are restricted.

For your custom functions, explicitly annotate:

```sql
CREATE FUNCTION my_func(geom geometry) RETURNS double precision
LANGUAGE SQL IMMUTABLE PARALLEL SAFE AS $$ ... $$;
```

Without `PARALLEL SAFE`, your function blocks parallel query plans even if everything else qualifies.

## Triggers for spatial validation

Enforce invariants at write time:

```sql
CREATE OR REPLACE FUNCTION enforce_valid_geometry()
RETURNS trigger AS $$
BEGIN
    IF NOT ST_IsValid(NEW.geom) THEN
        NEW.geom := ST_MakeValid(NEW.geom);
    END IF;
    IF ST_IsEmpty(NEW.geom) THEN
        RAISE EXCEPTION 'Empty geometry not allowed';
    END IF;
    IF ST_SRID(NEW.geom) != 4326 THEN
        RAISE EXCEPTION 'Geometry must be in EPSG:4326, got %', ST_SRID(NEW.geom);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER features_validate_geom
BEFORE INSERT OR UPDATE OF geom ON features
FOR EACH ROW EXECUTE FUNCTION enforce_valid_geometry();
```

The book covers this pattern; it's still the right way to enforce data quality at the database layer.

**Pitfall:** triggers slow inserts. For bulk loads, drop the trigger temporarily (`ALTER TABLE features DISABLE TRIGGER features_validate_geom;`), validate in the staging step, re-enable.

## History tables via triggers

Capture every change to a spatial row:

```sql
CREATE TABLE features_history (
    id BIGSERIAL,
    feature_id BIGINT,
    geom geometry,
    attrs JSONB,
    operation TEXT,
    changed_at TIMESTAMPTZ DEFAULT now(),
    changed_by TEXT DEFAULT current_user
);

CREATE OR REPLACE FUNCTION track_feature_changes()
RETURNS trigger AS $$
BEGIN
    INSERT INTO features_history (feature_id, geom, attrs, operation)
    VALUES (
        COALESCE(NEW.id, OLD.id),
        COALESCE(NEW.geom, OLD.geom),
        COALESCE(NEW.attrs, OLD.attrs),
        TG_OP
    );
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER features_history_trigger
AFTER INSERT OR UPDATE OR DELETE ON features
FOR EACH ROW EXECUTE FUNCTION track_feature_changes();
```

For redistricting / boundary work where you need an audit trail of every edit, this pattern is essential.

## Custom aggregates

PostGIS ships `ST_Union_Aggr`, `ST_Envelope_Aggr`, etc. For your own:

```sql
-- Aggregate that returns a centroid weighted by feature area
CREATE OR REPLACE FUNCTION area_weighted_centroid_state(state geometry, geom geometry, area double precision)
RETURNS geometry AS $$
DECLARE
    cur_area double precision;
    cur_centroid geometry;
BEGIN
    -- ... accumulator logic ...
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE AGGREGATE area_weighted_centroid(geometry, double precision) (
    SFUNC = area_weighted_centroid_state,
    STYPE = geometry
);
```

Custom aggregates are powerful but rarely needed. Reach for them when standard aggregates can't express the operation cleanly.

## Modern observability — pg_stat_statements + auto_explain

Post-book: install always.

```sql
CREATE EXTENSION pg_stat_statements;
```

Then:

```sql
SELECT
    query,
    calls,
    mean_exec_time,
    total_exec_time
FROM pg_stat_statements
WHERE query LIKE '%ST_%'
ORDER BY total_exec_time DESC
LIMIT 20;
```

Top spatial-query offenders show up here. Prioritize fixing the top 5; ignore long tail.

For automatic plan capture on slow queries:

```sql
LOAD 'auto_explain';
SET auto_explain.log_min_duration = '1s';
SET auto_explain.log_analyze = true;
```

Logs plans for queries > 1 second to the Postgres log. Useful for finding "this used to be fast and now it isn't" regressions.

## JIT compilation (PG 11+, post-book)

PostgreSQL JIT-compiles queries above a cost threshold. Spatial queries with large planning costs benefit measurably:

```sql
SET jit = on;
SET jit_above_cost = 100000;
```

Defaults are usually right; if you see "JIT" in EXPLAIN output for spatial queries and they're slower than expected, try `SET jit = off` for the session — JIT has overhead that can dominate for short-running queries.

## Pitfalls

- **Function defaults to `VOLATILE`** — blocks parallel query and inlining. Always annotate volatility.
- **PL/pgSQL when SQL would do** — PL/pgSQL functions can't be inlined; SQL functions can. Use SQL for one-expression functions.
- **Triggers on bulk-load tables** — slow ingestion 10-100x. Disable during bulk load.
- **`SECURITY DEFINER` functions accessing tables** — RLS bypass risk. Use only when needed; document scope.
- **No explicit `IMMUTABLE`/`STABLE`** — planner can't optimize. Default `VOLATILE` is the worst case.
- **Triggers + RAISE EXCEPTION rolling back transactions** — inconsistent error handling at the application layer; document trigger behavior in user-facing docs.
- **Custom aggregate with `VOLATILE` state function** — non-deterministic results across runs. Almost always wrong; use `IMMUTABLE`.

## Cross-links

- [`../query-optimization.md`](../query-optimization.md) — `EXPLAIN`, `pg_stat_statements`, parallel query setup
- [`../vacuuming-and-bloat.md`](../vacuuming-and-bloat.md) — autovacuum and `auto_explain` for ops monitoring
- [`06-etl-patterns.md`](06-etl-patterns.md) — ETL pipelines that disable triggers during bulk load

## Citation

Witkowski K., Chojnacki B., Mackiewicz M. *Mastering PostGIS*. Packt Publishing, 2017. Chapter 7 ("PostGIS Programming"). Paraphrase + commentary; not redistribution.
