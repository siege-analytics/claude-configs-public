# Changelog

All notable changes to this project are documented here. Versioning follows [SemVer](https://semver.org/).

## [Unreleased]

(no changes pending)

## [1.1.0] — 2026-05-08

Adds the lessons-learned rules pipeline: a three-tier system that turns recurring code-review findings, CodeRabbit threads, and incident lessons into durable, evidence-backed rules. Also tightens the Definition of Done by running code-review at commit time, not just at PR-open.

### Added — Pre-commit code-review gate (#29)

Operationalizes Definition of Done criterion (a) at the pre-commit transition. Every commit invokes `[skill:code-review]` against the staged diff. Blockers stop the commit; Majors must be fixed in the same commit or deferred to a follow-up ticket. A `[review-skip]` override exists for documented exceptions, mirroring `[no-ticket]` and `[direct-commit]`.

The pre-PR review (in `[skill:create-pr]`) still runs as a second pass over the cumulative diff. The two reviews are complementary: pre-commit catches findings while context is fresh; pre-PR catches drift across multiple commits.

- `skills/git-workflow/commit/SKILL.md` — new step 3 + Pre-review gate section + checklist row
- `skills/_definition-of-done-rules.md` — criterion (a) names both transitions; transitions table updated

### Added — Lessons-learned rules pipeline (#31, #33)

Three-tier system for capturing, distilling, and curating durable rules:

| Tier | Lives in | Owned by | Promotion gate |
|---|---|---|---|
| 1 — Ledger | `<repo>/LESSONS.md` | `[skill:lessons-learned]` | recurrence ≥ 3, or 1 production incident, or Critical-severity → Tier 2 |
| 2 — Project rules | `<repo>/.claude/rules/<topic>.md` | `[skill:distill-lessons]` | appears in 2+ projects, or is language/framework-level → Tier 3 |
| 3 — Org rules (this repo) | `claude-configs-public/skills/_*-rules.md` | Human PR with cited evidence | (top of pipeline) |

**New skills:**
- `skills/meta/lessons-learned/` (+ `template/LESSONS.md`) — Tier-1 capture. Three discipline rules: every entry has a link, rules-not-advice, recurrence counter not duplicates.
- `skills/meta/distill-lessons/` — Tier-1 → Tier-2 promotion. One rule at a time, with a conflict gate (refuses to write a contradictory rule) and human wording confirmation.
- `skills/meta/rules-audit/` — cross-tier hygiene pass. Four phases: Tier-1 hygiene, Tier-2 hygiene, cross-tier (Tier-2 → Tier-3 candidates, conflicts with newer evidence, stale upstream rules), coverage. Surface-only, never auto-acts.

**Integration:**
- `skills/coding/code-review/SKILL.md` — loads project `.claude/rules/*.md` at the start of every review; logs recurring findings via `[skill:lessons-learned]` at the end.
- `skills/session/coderabbit-response/SKILL.md` — new step 8: feed the ledger for recurring CR findings.
- `skills/session/pr-comments/SKILL.md` — new workflow step: feed the ledger for recurring human-reviewer flags.
- `skills/session/wrap-up/SKILL.md` — sweeps for ledger entries before the CLAUDE.md update; checks rules-audit cadence and nudges (non-blocking) if >60 days since last audit; clarifies CLAUDE.md = session-scoped, LESSONS.md = durable.

### Added — Tier-3 PR requirements documented (#33)

`CONTRIBUTING.md` now has a "How rules get promoted into this repo" section. Adding or amending a rule in any `_*-rules.md` requires citing ≥2 Tier-2 projects (or 1 + language/framework justification), listing the originating Tier-1 evidence, and passing the conflict gate. PRs without cited evidence are asked to gather evidence first or downgrade to discussion issues.

### No breaking changes

All additions and additive integrations. Existing skills retain their behavior; new behavior is opt-in via the new skills. Downstream consumers can pin to `v1.1.0-nested` or `v1.1.0-flat` once published.

## [1.0.0] — 2026-05-07

Major release. Decouples skill identity from filesystem layout; one source serves Claude Code (resolver hook) and Craft Agent (slash-command pane) via a build step.

### Added — Dual-layout build (slug-token references)

Decouples skill identity (slug) from filesystem layout. Cross-references between skills now use `[skill:<slug>]` and `[rule:<slug>]` tokens; the build expands them to layout-appropriate paths.

- `bin/build.py` — produces `dist/nested/` (mirrors source for Claude Code with the resolver hook) and `dist/flat/` (leaf skills at `skills/<slug>/` for Craft Agent's pane). Token resolution + RESOLVER generation per layout.
- `bin/sync-skill-references.py` — mechanical converter from path-form to token-form Markdown links. Used for the one-time migration; CI runs it in `--check` mode to enforce token form on every PR.
- `skills/RESOLVER.template.md` — slug-token version of the resolver. Build emits per-layout RESOLVER.md from this template.
- `.github/workflows/build-and-publish.yml` — validate references on every PR; build and publish to `release/nested` and `release/flat` on every push to main; tag fan-out (`vX.Y.Z` → `vX.Y.Z-nested` + `vX.Y.Z-flat`) on tag push.
- `CONTRIBUTING.md` — slug-token convention, contributor workflow, build commands, downstream consumer instructions.

### Changed — `RESOLVER.md` is now a build artifact

`skills/RESOLVER.md` removed from source; replaced by `skills/RESOLVER.template.md`. The build generates `RESOLVER.md` per layout with paths appropriate to that layout. Hand-editing the resolver now means editing the template.

### Changed — Cross-references converted to tokens (mechanical)

249 skill cross-references and 39 rule cross-references across 46 SKILL.md and `_*-rules.md` files converted from path-form Markdown links to `[skill:slug]` / `[rule:slug]` tokens. No content change beyond link form. Going forward, contributors use tokens; CI catches path-form references that slip in by habit.

### Breaking — pin to a release-branch tag, not the source tag

`main` now contains build infrastructure (tokens unresolved). Downstream consumers should pin to `v1.0.0-nested` or `v1.0.0-flat` (release-branch tags), not `v1.0.0` (source tag). See [Distribution layouts](README.md#distribution-layouts).

This is a breaking change to the consumption pattern; existing v0.x consumers pulling from `main` need to update their subtree pull command. The skills themselves are unchanged.

## [0.3.0] — 2026-05-06

Adds the Definition of Done as an always-on rule with hard enforcement, and makes `pre-work-check` and `think` slash-invokable to match their README classifications.

### Added — Definition of Done (`_definition-of-done-rules.md`)

New always-on rule file `skills/_definition-of-done-rules.md`, sibling of `_principles-rules.md` and `_output-rules.md`. Five hard criteria for "done":

- **(a) Code-reviewed** — every behavior change goes through review
- **(b) Edge cases explored** — concrete checklist (empty / boundary / duplicate / out-of-order / very-small / very-large / mixed-types / partial-failure / null / identifier-collision)
- **(c) Tests written** — mandatory; no test infrastructure means add it first; PRs without tests must justify in description
- **(d) Non-trivial updates → update the ticket** — status, comments, links, final summary
- **(e) Work has a ticket** — every behavior change starts from one

Hard enforcement, not recommendations. Soft rules erode; these are documented responses to specific Siege incidents.

Cross-referenced from:
- `skills/coding/SKILL.md` Rule 6 (one-line reference)
- `skills/coding/python/SKILL.md` "Tests and Documentation" section (paragraph reference)
- `skills/coding/code-review/SKILL.md` §1 (edge-case checklist promoted from one bullet to 9-item explicit checklist)
- `skills/git-workflow/create-pr/SKILL.md` ("Definition of Done gate (mandatory)" subsection — failed criteria → PR opens as draft)
- `skills/session/wrap-up/SKILL.md` (Step 0 verification ahead of commit/cleanup)

Registered in `skills/RESOLVER.md` Conventions table.

### Changed — `pre-work-check` and `think` are slash-invokable

Both skills already classified as user-invokable in README (Action / Analytical). Frontmatter brought into line:

- `skills/planning/pre-work-check/SKILL.md` — `disable-model-invocation: true` added; now slash-invokable as `/pre-work-check`
- `skills/thinking/think/SKILL.md` — `disable-model-invocation: true` added; now slash-invokable as `/think`

Resolver-driven enforcement is unchanged. Both skills remain auto-applied gates via the resolver hook; the change adds manual invocation as an option.

### Documentation

- `README.md` — adds `_definition-of-done-rules.md` to Always-on conventions table; new "Definition of Done" section explaining the five criteria and PR/wrap-up gating

## [0.2.0] — 2026-05-02

## [0.2.0] — 2026-05-02

Spatial skill overhaul — adds the four-engine spatial skill set (PostGIS / GeoPandas / Sedona / DuckDB-spatial), the universal cross-engine principles, two book distillations (Mastering PostGIS, Geographic Data Science with Python), and substantially expanded spatial-statistics coverage.

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

[Unreleased]: https://github.com/siege-analytics/claude-configs-public/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/siege-analytics/claude-configs-public/releases/tag/v1.1.0
[1.0.0]: https://github.com/siege-analytics/claude-configs-public/releases/tag/v1.0.0
[0.3.0]: https://github.com/siege-analytics/claude-configs-public/releases/tag/v0.3.0
[0.2.0]: https://github.com/siege-analytics/claude-configs-public/releases/tag/v0.2.0
[0.1.0]: https://github.com/siege-analytics/claude-configs-public/releases/tag/v0.1.0
