# Changelog

All notable changes to this project are documented here. Versioning follows [SemVer](https://semver.org/).

## [Unreleased]

### Added — Spatial skill set (`feat/spatial-skill-overhaul`)

A four-engine spatial skill set with capability-tier dispatch. Replaces the generic "spatial" decision skill with per-engine operational skills plus an augmented router.

**New skills:**

- **`skills/coding/geopandas/`** — GeoPandas + folded Shapely for single-node Python spatial work. Has explicit no-GDAL fallbacks for `geo-lite` environments.
- **`skills/coding/sedona/`** — Apache Sedona for distributed spatial work on Spark. One skill for both PySpark and Scala scaffolding (the spatial logic is identical). Includes raster.
- **`skills/coding/duckdb-spatial/`** — DuckDB's spatial extension as the no-server / no-GDAL path. Bundles GEOS / GDAL / PROJ in a single binary; the strongest single tool for GDAL-less environments (Lambda, slim images, locked-down envs).

**Augmented:**

- **`skills/coding/postgis/`** — added 9 reference files (Mastering PostGIS distillation, indexing strategies, geometry vs geography, spatial joins performance, query optimization, topology, vacuuming and bloat, pitfalls, SU-PostGIS interop map). Existing SKILL.md preserved; new "Companion shelves and references" section links them.
- **`skills/analysis/spatial/SKILL.md`** — augmented as the load-bearing engine-selection router. Three axes: data scale × GDAL availability × workload pattern. Existing 6-step decision framework preserved; new "Always start with: capability detection" prelude calls `siege_utilities.geo.capabilities.geo_capabilities()`. Six new reference files: engine-selection, gdal-availability-matrix, crs-decision-tree, siege-utilities-spatial, capability-tiers, spatial-statistics.

**siege_utilities integration:**

Each engine has a dedicated `siege-utilities-<engine>.md` reference describing what SU obviates and what's still bring-your-own. Cross-engine consolidated map at `skills/analysis/spatial/references/siege-utilities-spatial.md`.

**Resolver registrations:**

- `skills/RESOLVER.md` Coding section: rows for `geopandas`, `sedona`, `duckdb-spatial` (PostGIS row already existed)
- `skills/RESOLVER.md` Analysis section: spatial row reframed to emphasize router's dispatch role
- `RESOLVER.md` (top-level) Writing-code section: row pointing at `analysis/spatial/SKILL.md` as the entry for any spatial work

### Added — Universal cross-engine spatial principles

`skills/analysis/spatial/references/principles/` — 6 files articulating the spatial principles that translate across all four engines (PostGIS, GeoPandas, Sedona, DuckDB-spatial). Distinct from the engine-faithful Mastering PostGIS distillation (which is PostgreSQL-specific). Each principle file shows the principle, why it's universal, and per-engine implementation:

- `index.md` — meta-index + reading order
- `crs-is-meaning.md` — SRID as semantic layer; project before measuring
- `validate-on-ingest.md` — repair geometry at the boundary; never silently drop
- `bbox-pre-filter.md` — every fast spatial op = bbox pre-filter + exact predicate
- `subdivide-complex-polygons.md` — universal 10-100× speedup; per-engine recipes
- `spatial-indexing-discipline.md` — every spatial column gets a spatial index, always
- `name-by-srid.md` — column-naming convention that makes CRS bugs surface at schema-validation time (load-bearing for engines without per-row CRS storage)

### Updated — Mastering PostGIS chapters 3-9 added

Following Ch 1-2 in the previous commit, Ch 3 (vector operations), 4 (raster), 5 (exporting), 6 (ETL), 7 (PL/pgSQL programming), 8 (web backends — `pg_tileserv` / `pg_featureserv` / MVT), 9 (pgRouting). Each is principle-level distillation with cross-links to topic refs and per-engine notes where principles transfer.

### Updated — Topology framing reversed

`skills/coding/postgis/references/topology.md` was framed as "rarely the right tool." Reframed to **option C (pragmatic with use cases)** centered on the load-bearing Siege use case: **point-derived boundaries** (Voronoi tessellation, alpha-shape concave hulls, kernel-density contours, regionalization output). When you produce boundaries from points, shared-edge integrity matters and topology earns its operational complexity. Concrete worked example for Voronoi + topology pipeline. Cross-engine note: topology is PostGIS-specific; other engines reconstruct meshes per operation.

### Added — *Geographic Data Science with Python* distillation + 5 topic refs

Distillation of [GDSPy](https://geographicdata.science/book/intro.html) (Rey, Arribas-Bel, Wolf, 2023; CC-BY-NC-ND online edition) — the canonical modern textbook for spatial analysis on top of GeoPandas + the PySAL ecosystem. Companion to the Mastering PostGIS distillation: GDSPy is methodology-faithful (engine-agnostic math); Mastering PostGIS is engine-faithful (PostgreSQL idioms).

- `analysis/spatial/references/geographic-data-science-distilled.md` — book intro, chapter map, currency caveat, citation
- `analysis/spatial/references/spatial-weights.md` — the W matrix in depth; kernel/KNN/distance-band/hybrid; standardization; sensitivity (was under-weighted in `spatial-statistics.md`)
- `analysis/spatial/references/regionalization.md` — constrained spatial clustering (max-p / SKATER / AZP); redistricting algorithms; compactness measures (Polsby-Popper, Schwartzberg, Reock); pointers to `gerrychain`
- `analysis/spatial/references/spatial-inequality.md` — Gini, Theil, Atkinson; **Theil decomposition into between-region vs within-region inequality**; Lorenz curves
- `analysis/spatial/references/spatial-feature-engineering.md` — neighbor-aggregate features, distance-to features, density features; **spatial cross-validation as non-negotiable** (random K-fold leaks signal across spatially-adjacent rows)
- `analysis/spatial/references/point-pattern-analysis.md` — Ripley's K, L, G, F, J functions; KDE; CSR tests; cross-K for two-pattern association (reverses earlier "out of scope" call)

### Added — Mastering PostGIS book-skill folder structure

`skills/coding/postgis/references/mastering-postgis-distilled.md` (single file) promoted to `skills/coding/postgis/references/mastering-postgis/` (folder with chapter-themed reference files mirroring the book's TOC). `index.md` carries the meta-index, currency caveats, and citation; chapter files are added incrementally (Ch 1 + Ch 2 done in this PR, Ch 3-9 deferred to a follow-up).

### Updated — siege-utilities-duckdb-spatial.md

Added the 4th per-engine SU interop map for symmetry with the other three engines. Documents SU's currently-thin DuckDB integration (format conversion only) and the SU-1 / SU-7 / SU-9 upstream PR candidates that would close most inline-SQL gaps.

### Updated — Sedona scaffolding rebalanced toward PySpark

Sedona content was equal-weighted between PySpark and Scala; rebalanced to **PySpark as the default scaffolding** since most Siege Sedona work is Python. Scala variant moved to a single dedicated reference file (`scaffolding-python-vs-scala.md`).

### Updated — spatial-statistics.md expanded

Was ~250 lines; now ~580 lines with hotspot analysis substantially expanded (methodological choices, multiple-testing correction, edge effects), plus new use cases: empirical Bayes rate smoothing, segregation indices, 2SFCA accessibility. Per-engine implementation matrix for 11 methods. Cross-links to the new GDSPy-derived references above.

### Documentation

- `README.md` — updated Router Skills table to reflect actual sub-skills; added Always-on conventions section listing all `_*-rules.md` files; added Spatial skills section with per-engine table; added Releases & versioning section; corrected stale Reference Skills entries; added pre-work-check / qml-component-review / infrastructure/ops to skill tables; added `siege_utilities` first-class section.

## [0.1.0] — 2026-05-02

First tagged release. Marks the inaugural stable surface of `claude-configs-public` as a usable, reusable Claude Code skill catalog with the **DBrain** book-skill library, an always-on rules system, and the resolver-gated discovery layer.

### Added — DBrain book-skill library (`skills/shelves/`)

A book-derived skill library integrated and adapted from two MIT-licensed upstream skill libraries — [ZLStas/skills](https://github.com/ZLStas/skills) and [wondelai/skills](https://github.com/wondelai/skills) — organized into 11 topic shelves:

- `engineering-principles/` — Clean Code, Clean Architecture, Design Patterns, Domain-Driven Design, Refactoring Patterns, Pragmatic Programmer, Software Design Philosophy
- `systems-architecture/` — Designing Data-Intensive Applications, System Design, Microservices Patterns, Release It!, High-Performance Browser Networking, System Design Interview
- `languages/` — Effective Python / Java / Kotlin / TypeScript, Kotlin in Action, Spring Boot in Action, Programming Rust, Rust in Action, Using Asyncio in Python, Web Scraping with Python
- `data-and-pipelines/` — Data Pipelines Pocket Reference (Densmore)
- `product/` — Jobs to Be Done, Continuous Discovery, Design Sprint, Lean Startup, Lean UX, Inspired, The Mom Test, Improve Retention
- `marketing/` — CRO, StoryBrand, Contagious, Made to Stick, Scorecard / One-Page Marketing, Hooked
- `sales/` — Predictable Revenue, Negotiation, Influence, $100M Offers
- `strategy/` — Blue Ocean, Crossing the Chasm, Traction (EOS), Obviously Awesome
- `design/` — Refactoring UI, iOS HIG, UX Heuristics, Web Typography, Top, Don't Make Me Think, Microinteractions
- `team/` — Drive (Pink), the 37signals Way
- `storytelling/` — Storytelling with Data, Animation at Work

Inspired by [GBrain](https://github.com/garrytan/gbrain). 53 unique book skills, each with an attribution footer pinning the upstream commit.

### Added — Always-on rules

Sibling files of `_output-rules.md` and `_data-trust-rules.md`, registered in the resolver Conventions table:

- `_principles-rules.md` — Clean Code maxims (always-on for any code task)
- `_python-rules.md` — Effective Python idioms
- `_jvm-rules.md` — Effective Java + Effective Kotlin (merged), applied for Java / Kotlin / Scala-on-Spark
- `_typescript-rules.md` — Effective TypeScript idioms
- `_rust-rules.md` — Rust idioms
- `_siege-utilities-rules.md` — workspace-wide preference for [`siege_utilities`](https://github.com/siege-analytics/siege_utilities) before writing local helpers; consider upstream PRs when the gap is generic

### Added — New skills

- `coding/scala-on-spark/` — thin delegating skill that fires for `.scala` / `%scala` / `Dataset[T]` work and chains `coding/spark/` + `shelves/languages/effective-java/` + `shelves/languages/effective-kotlin/` + `shelves/systems-architecture/data-intensive/`.
- `coding/qml-component-review/` — QML component decomposition, properties-in / signals-out discipline, MuseScore plugin work.
- `infrastructure/ops/` — guardrails for shared infrastructure (cyberpower UPS, K8s pod limits, Rundeck concurrency).

### Added — Companion-shelves delegation in existing coding skills

Inserted "Companion shelves" sections into `coding/python`, `coding/python-patterns`, `coding/python-exceptions`, `coding/code-review`, `coding/sql`, `coding/spark`, `coding/django`, `coding/postgis`, `coding/pipeline-jobs`. Each block points the agent to the relevant book skills in `shelves/` for principle-level rationale alongside the project-specific skill content.

### Added — Resolver registrations

- `skills/RESOLVER.md` Conventions table now lists all `_*-rules.md` files (DBrain rules + siege_utilities rule).
- `skills/RESOLVER.md` Coding section gains rows for `scala-on-spark` and `qml-component-review`.
- `skills/RESOLVER.md` Planning section gains row for `pre-work-check`.
- `skills/RESOLVER.md` Infrastructure section gains row for `infrastructure/ops`.
- `skills/RESOLVER.md` new "Shelves (book-derived libraries)" section dispatches to each of the 11 shelves.
- Top-level `RESOLVER.md` Writing-code section gains rows for Scala on Spark, service-boundary design, storage-engine selection, and Python utility helpers (siege_utilities-first).

### Added — `LICENSE` (MIT)

First explicit license file. Matches both upstream sources.

### Added — `THIRD_PARTY_NOTICES.md`

Full attribution for upstream MIT-licensed skill libraries with commit pins and the per-book mapping.

### Fixed

- `skills/analysis/SKILL.md` — restored data-trust framing as the first question of the analysis router. Spatial / entity-resolution / graph methods exist *because* tabular identifiers are dirty; opening the router with "do you actually need geometry?" inverted that premise. Also added Rule 5 making `_data-trust-rules.md` an always-on convention rather than documentation.
- `skills/coding/python/SKILL.md` — restored "Tests and Documentation — non-negotiable" section. The only place in the skills tree making tests + docs a hard merge gate at the language level.
- `skills/coding/SKILL.md` — restored Rule 5 (`_output-rules.md` discovery path), Rule 6 (language-agnostic tests-and-docs policy), and the `python-patterns` / `python-exceptions` reviewer-lens gotcha.

### Documentation

- `README.md` — DBrain section, shelf overview table, Credits, GBrain attribution, MIT license note.
- This `CHANGELOG.md`.

[0.1.0]: https://github.com/siege-analytics/claude-configs-public/releases/tag/v0.1.0
