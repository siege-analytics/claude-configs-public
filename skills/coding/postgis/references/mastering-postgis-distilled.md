# Mastering PostGIS — Distilled

Principle-level distillation of *Mastering PostGIS* (Krzysztof Witkowski, Bartosz Chojnacki, Michał Mackiewicz, 2017). The book targets PostGIS 2.x — call out what's stable vs. what needs post-book treatment.

This is paraphrase + commentary for agent guidance, not redistribution.

## Stable principles (still correct in PostGIS 3.x)

- **Spatial reference systems are intent.** A geometry without an SRID is a geometry without a meaning. Encode CRS at ingest, not at query time.
- **`geometry` for projected work, `geography` for great-circle distance.** Choose deliberately at the column level. See [`geometry-vs-geography.md`](geometry-vs-geography.md).
- **GIST is the workhorse index.** Always create it on geometry columns you'll filter or join on. SP-GIST and BRIN are situational. See [`indexing-strategies.md`](indexing-strategies.md).
- **`ST_DWithin` over `ST_Distance`-with-WHERE.** The former uses the index; the latter scans every row.
- **Subdivide complex polygons once, query forever.** `ST_Subdivide` to ~256 vertices per piece is the canonical 10-100× speedup for point-in-polygon against Census tracts, congressional districts, precincts. See [`spatial-joins-performance.md`](spatial-joins-performance.md).
- **`ST_MakeValid` on ingest.** Invalid geometry is the silent corruptor — every downstream operation may return wrong results without erroring.
- **Topology is for shared-edge editing.** Don't reach for `postgis_topology` unless you're editing polygon networks where moving one vertex must move adjacent edges. See [`topology.md`](topology.md).

## Post-book topics (the book doesn't cover; you'll need them)

- **PostGIS 3.x raster as separate extension.** `postgis_raster` is now its own extension you load explicitly. The book treats raster as part of core.
- **Parallel query.** PostgreSQL 9.6+ added parallelism; PostGIS functions are progressively marked `PARALLEL SAFE`. Check `proparallel` on the function before assuming parallelism kicks in.
- **H3 indexing.** Uber's hexagonal indexing extension (`h3-pg`) didn't exist when the book was written. Excellent for binning at scale and approximate joins when GeoPandas/PostGIS overlay is overkill.
- **PMTiles / GeoParquet.** Modern interchange formats post-date the book entirely. PMTiles for static vector tiles served from object storage; GeoParquet for columnar spatial. Postgres can write GeoParquet via Foreign Data Wrappers but it's not native.
- **Partitioning improvements.** Declarative partitioning (PG 10+) and partition-wise joins/aggregations (PG 11+) are post-book. Critical for 100M+ row spatial tables.
- **`pg_stat_statements` + `auto_explain`.** Performance introspection is post-book quality-of-life — install always.

## What the book gets very right

- **Conceptual treatment of CRS.** Even with newer EPSG codes, the book's framing of "what does a coordinate mean" is the right mental model.
- **Index strategy.** GIST tradeoffs, when to use functional indexes, when to add covering columns — still current.
- **Spatial join recipes.** The book's worked examples remain the canonical recipes; PostGIS internals haven't fundamentally changed.

## What the book gets wrong or stale

- **3D / TIN sections.** Largely unchanged in PostGIS 3.x but use cases have moved to specialized tools (CesiumJS, Unity).
- **Raster organization.** Modern practice tiles raster outside Postgres (COG on S3 + STAC) more than into `postgis_raster` tables.
- **pgRouting integration.** Now lives as its own ecosystem; don't treat it as a PostGIS subtopic.

## Citation

Witkowski K., Chojnacki B., Mackiewicz M. *Mastering PostGIS*. Packt Publishing, 2017. Used as inspiration for principles in this reference set; specific code, examples, and worded explanations are Siege's own paraphrase. Not redistributed.
