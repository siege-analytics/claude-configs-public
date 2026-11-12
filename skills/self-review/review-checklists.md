# Self-review methods and checklists

Optional domain and method reference. The compact contract in [Self-review](SKILL.md) governs; these checks do not require rank stages, pre-coding approval or mandatory findings. Use relevant substantive domain checks. Activate only the domain checklists required by the diff and project policy. This content does not grant a reviewer implementation authority.

## Domains

The domain declares what kind of work is under review. Each domain
has its own affirmative standards -- the things that must be true for
the work to be correct, beyond what the shelves check mechanically.

- **Software engineering** -- implementing features, fixing bugs, writing
  tests. Shelves cover this domain nearly completely.
- **Data engineering** -- pipelines, schemas, ETL, derived data,
  replicated state, and distributed processing. Shelves cover partially
  (writing-code:5, writing-tests:1, writing-claims:1-3) and should be
  supplemented with `shelves/systems-architecture/data-intensive/` for
  DDIA-style review. Affirmative standards: source-of-truth declared;
  idempotence; replayability/backfill; schema evolution compatibility;
  partitioning and hot-key behavior; transaction/isolation assumptions;
  named consistency guarantee; watermarking/timeliness; lineage; and
  reconciliation/integrity checks for derived stores.
- **Data analysis & visualization** -- statistical modeling, defensible
  findings, chart/report generation. Shelves cover mostly via
  `_writing-claims-rules.md`. Affirmative standards not shelved:
  sample-size adequacy, confounder controls, observed-vs-inferred,
  falsifiability, MAUP / ecological fallacy / scale effects.
- **Geospatial (cross-cutting)** -- applies within any of the above.
  Not shelved. Affirmative standards: CRS appropriateness per operation
  (4326 for storage, equal-area for buffer/area, web-mercator for
  tiles), spatial-index hygiene before any `ST_*` predicate, modern
  format choice (GeoParquet > Shapefile; COG / Zarr where they fit),
  semantic naming of geographic concepts (vintage / plan / district /
  GEOID), elegant temporal-spatial intersections. **Delight as audit
  signal**: "would I point at this work?"

### Review perspective

Inspect the requested outcome, actual implementation, consequential assumptions, relevant failure cases and validation evidence. Use only the domain checks that affect the change.

- Does the change solve the reported problem and preserve relevant contracts?
- Are authorization, input validation, data integrity and error handling appropriate to the actual effects?
- Do tests demonstrate the behavior and important failure cases rather than mirror implementation?
- Do runtime-dependent claims match the actual consumer, configuration and version?
- Are complexity and resource use reasonable for the observed scale?
- Are deployment, rollback and documentation sufficient for the consequences?

Record material findings and resolutions. A supported finding-free review is valid. Do not require invented mistakes, a fixed number of findings, separate Junior/Lead passes or a pre-coding approval ceremony. The compact contract in [Self-review](SKILL.md) governs publication review.
