# Universal Spatial Principles

Principles that apply across **every** engine in the spatial set — PostGIS, GeoPandas, Sedona, DuckDB-spatial. Each principle gets a dedicated file with engine-specific implementation patterns.

These are *separate* from the engine-faithful Mastering PostGIS distillation: that one is PostgreSQL-specific (VACUUM discipline, GIST tradeoffs, planner internals). This one is engine-agnostic.

## The principles

| File | Principle |
|---|---|
| [`crs-is-meaning.md`](crs-is-meaning.md) | A coordinate is a number with no relationship to physical space until it has an SRID. CRS is the semantic layer; project before measuring |
| [`validate-on-ingest.md`](validate-on-ingest.md) | Invalid geometry breaks operations silently. Repair at the boundary, not in the middle of a pipeline |
| [`bbox-pre-filter.md`](bbox-pre-filter.md) | Every fast spatial operation is bounding-box pre-filter + exact predicate. Make the pre-filter explicit and indexed |
| [`subdivide-complex-polygons.md`](subdivide-complex-polygons.md) | Complex polygons (Census tracts, state boundaries) are slow to test against. Split them once, query forever |
| [`spatial-indexing-discipline.md`](spatial-indexing-discipline.md) | A spatial column without a spatial index is a full-table-scan trap |
| [`name-by-srid.md`](name-by-srid.md) | Track CRS across pipeline stages via column naming convention. The bug surfaces at column-name level |

## What's NOT here

PostgreSQL-specific patterns belong in `coding/postgis/references/` (or its `mastering-postgis/` subfolder), not here:

- `VACUUM` discipline — Postgres-only
- GIST vs SP-GIST vs BRIN tradeoffs — Postgres-only
- `EXPLAIN (ANALYZE, BUFFERS)` reading — Postgres-only
- `pg_stat_statements` — Postgres-only
- `parallel_safe` function annotations — Postgres-only
- `postgis_topology` — PostGIS-only feature
- FDW patterns — Postgres-only
- COPY / `\copy` / UNLOGGED tables — Postgres-only

GeoPandas-, Sedona-, and DuckDB-specific patterns belong in their respective engine SKILL.md and references/.

The principles in this folder are the cross-cutting concerns. Each file shows the principle, why it's universal, and per-engine implementation.

## How the principles relate to the engine skills

```
Universal principle (this folder)
        │
        ├──→ PostGIS implementation (coding/postgis/...)
        ├──→ GeoPandas implementation (coding/geopandas/...)
        ├──→ Sedona implementation (coding/sedona/...)
        └──→ DuckDB-spatial implementation (coding/duckdb-spatial/...)
```

Engine skills go deep on engine-specific operations. Principles files cut across, articulating the why and the universal pattern, with engine-specific implementations as recipes.

## Reading order

1. **`crs-is-meaning.md`** — first principle; everything else assumes CRS hygiene
2. **`validate-on-ingest.md`** — second; everything downstream depends on valid geometry
3. **`spatial-indexing-discipline.md`** — third; performance principle that gates everything at scale
4. **`bbox-pre-filter.md`** — fourth; the implementation pattern indices enable
5. **`subdivide-complex-polygons.md`** — fifth; specific high-leverage optimization
6. **`name-by-srid.md`** — sixth; defensive convention for multi-stage pipelines

In practice, agents load these on demand, not in sequence. The reading order is for humans onboarding to the principles.

## Cross-links

- [`../engine-selection.md`](../engine-selection.md) — picking the engine; principles below apply once chosen
- [`../gdal-availability-matrix.md`](../gdal-availability-matrix.md) — engine availability constrains principle implementation
- [`../crs-decision-tree.md`](../crs-decision-tree.md) — operationalizes the CRS principle into specific projection choices
- [`../../coding/postgis/references/mastering-postgis/`](../../../coding/postgis/references/mastering-postgis/) — engine-faithful PostGIS distillation (book-flavored)
