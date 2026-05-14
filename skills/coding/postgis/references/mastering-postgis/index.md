# Mastering PostGIS — Distilled

Principle-level distillation of *Mastering PostGIS* (Krzysztof Witkowski, Bartosz Chojnacki, Michał Mackiewicz; Packt Publishing, 2017). The book targets PostGIS 2.x; this distillation marks what's still current in PostGIS 3.x and what's been superseded.

This is paraphrase + commentary for agent guidance, not redistribution. Nothing here is a substitute for the original.

## Chapter map

The reference files mirror the book's table of contents. Each is a principle-level summary plus the post-book updates relevant in PostGIS 3.x. Where a topic overlaps the operational reference set in `skills/coding/postgis/references/`, the chapter file points at the deeper task-faithful coverage.

| Chapter | File | Topic |
|---|---|---|
| 1 | [`01-importing-data.md`](01-importing-data.md) | `shp2pgsql`, `ogr2ogr`, COPY-based bulk loads, raster ingest, FDW |
| 2 | [`02-data-types.md`](02-data-types.md) | `geometry` vs `geography` vs `raster`; dimensions; SRIDs; the `box*` family |
| 3 | [`03-vector-operations.md`](03-vector-operations.md) | `ST_*` predicates; spatial joins; `ST_Subdivide`; topology vs simple features |
| 4 | [`04-raster-operations.md`](04-raster-operations.md) | `postgis_raster` extension; tile organization; `ST_MapAlgebra`; raster + vector |
| 5 | [`05-exporting-data.md`](05-exporting-data.md) | `ST_AsText` / `ST_AsBinary` / `ST_AsGeoJSON`; FDW for outbound; postgresql_fdw |
| 6 | [`06-etl-patterns.md`](06-etl-patterns.md) | Staging tables, delta updates, idempotent ingestion, change detection |
| 7 | [`07-plpgsql-programming.md`](07-plpgsql-programming.md) | Stored functions, triggers, custom aggregates, parallel-safe annotations |
| 8 | [`08-web-backends.md`](08-web-backends.md) | `pg_tileserv`, `pg_featureserv`, MVT generation, REST patterns |
| 9 | [`09-pgrouting.md`](09-pgrouting.md) | Network topology, shortest path, isochrones, drive-time |

## What the book gets very right (still current)

- **Conceptual treatment of CRS and SRIDs.** Even with newer EPSG codes, the book's framing of "what does a coordinate mean" is the right mental model. See [`02-data-types.md`](02-data-types.md).
- **Index strategy.** GIST tradeoffs, when to use functional indexes, when to add covering columns — still current. See task-faithful coverage at [`../indexing-strategies.md`](../indexing-strategies.md).
- **Spatial join recipes.** The book's worked examples — `ST_Subdivide`, bounding-box pre-filter, partition-and-conquer — remain the canonical patterns. PostGIS internals haven't fundamentally changed. See [`../spatial-joins-performance.md`](../spatial-joins-performance.md).
- **Validity discipline.** `ST_MakeValid` on ingest; `CHECK` constraints; symptomatic debugging of invalid geometry. See [`../pitfalls.md`](../pitfalls.md).
- **Raster + vector cross-cutting.** The book's `ST_MapAlgebra` + zonal-statistics worked examples are still valid PostGIS 3.x.

## What the book is missing or stale (post-book updates)

- **PostGIS 3.x raster as a separate extension.** `postgis_raster` is now its own extension you load explicitly (`CREATE EXTENSION postgis_raster;`). The book treats raster as part of core. See [`04-raster-operations.md`](04-raster-operations.md).
- **Parallel query.** PostgreSQL 9.6+ added parallelism; PostGIS functions are progressively marked `PARALLEL SAFE`. Check `proparallel` on the function before assuming parallelism kicks in. See [`07-plpgsql-programming.md`](07-plpgsql-programming.md).
- **H3 hexagonal indexing.** Uber's `h3-pg` extension didn't exist when the book was written. Excellent for binning at scale and approximate joins when GeoPandas/PostGIS overlay is overkill. See [`02-data-types.md`](02-data-types.md).
- **PMTiles and GeoParquet.** Modern interchange formats post-date the book entirely. PMTiles for static vector tiles served from object storage; GeoParquet for columnar spatial. PostGIS can write GeoParquet via FDW but it's not native. See [`08-web-backends.md`](08-web-backends.md) and [`05-exporting-data.md`](05-exporting-data.md).
- **Declarative partitioning.** Partition-wise joins/aggregations (PG 11+) and partitioned indexes are critical for 100M+ row spatial tables. Book uses inheritance-based partitioning (now legacy). See [`06-etl-patterns.md`](06-etl-patterns.md).
- **Modern observability.** `pg_stat_statements`, `auto_explain`, `pg_stat_io` (PG 16) are all post-book quality-of-life. Always install. See [`07-plpgsql-programming.md`](07-plpgsql-programming.md).
- **MVT generation native.** `ST_AsMVT` (PostGIS 2.4+) and PG-server-side vector tile generation post-date the book's web chapter. See [`08-web-backends.md`](08-web-backends.md).
- **FDWs for cloud spatial data.** `postgres_fdw` to remote Postgres, `parquet_s3_fdw` for cloud parquet — the modern way to read spatial data from external sources without `shp2pgsql` round-trips. See [`05-exporting-data.md`](05-exporting-data.md).

## What the book gets wrong or has aged badly

- **3D / TIN sections.** Largely unchanged in PostGIS 3.x but use cases have moved to specialized tools (CesiumJS, Unity, dedicated geospatial engines).
- **Raster organization advice.** Modern practice tiles raster outside Postgres (COG on S3 + STAC catalog) more than into `postgis_raster` tables. Book treats Postgres as the raster store; this is now uncommon at production scale.
- **pgRouting integration.** Now lives as its own ecosystem with its own learning curve; don't treat it as a PostGIS subtopic. See [`09-pgrouting.md`](09-pgrouting.md) for entry points and pointers to the canonical pgRouting documentation.

## How to use this distillation

- For **principles and rationale**, read this distillation. Each chapter file frames the book's argument in PostGIS-3.x-current terms.
- For **operational recipes** (specific SQL, index commands, EXPLAIN reads), use the sibling files in `skills/coding/postgis/references/`. The chapter files cross-link.
- For **the canonical reference**, buy the book — paraphrase here is not a substitute for the original treatment.

## Citation

Witkowski K., Chojnacki B., Mackiewicz M. *Mastering PostGIS*. Packt Publishing, 2017. ISBN 978-1-78439-164-5.

Used as inspiration for principles in this reference set; specific code, examples, and worded explanations are Siege's own paraphrase. Not redistributed.
