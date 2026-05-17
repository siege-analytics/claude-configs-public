---
name: spatial-data-science
description: 'Methodological foundation of spatial data science — the WHY behind CRS / projections / support / data cubes. Use when the user mentions "support (spatial)", "MAUP", "modifiable areal unit problem", "ecological fallacy", "data cubes", "spatial statistics", "geostatistics", "areal interpolation", "spatial regression", "Pebesma", "Bivand", or asks "what does this spatial concept actually mean". Also trigger when modeling spatial phenomena (not just transforming data), debating CRS choice from first principles, reasoning about scale effects in geographic analysis, or designing a spatial-temporal data model. Heavier on theory than geocomputation-with-r (which is applied); pair them. For engine-specific code see postgis / geopandas / sedona / duckdb-spatial.'
license: CC-BY-NC-ND
metadata:
  source: 'r-spatial.org/book — full free online edition of Spatial Data Science: With Applications in R (Pebesma & Bivand, 2025). CRC Press / Routledge also publishes paid print edition.'
  coverage: 'Full book (17+ chapters across 3 parts) freely readable inline at r-spatial.org/book. Verified 2026-05-17 via WebFetch.'
---

# Spatial Data Science Framework

The methodological / theoretical foundation that makes spatial analysis non-fraudulent. Where Geocomputation with R teaches you HOW to do spatial operations in code, this framework teaches WHY the operations are defined as they are, and what assumptions you're inheriting when you call them.

## Core Principle

**Support matters when manipulating spatial data.** Pebesma & Bivand's central conceptual claim: every attribute attached to a geometry has *support* — the spatial unit the attribute applies to. Is the value a point measurement? A polygon average? A density per area? An aggregate across a region? Pretending support doesn't exist (treating polygon averages as point values, mixing polygon attributes with raster pixel values without aggregation) produces analyses that are formally correct but substantively meaningless.

**The foundation:** spatial data is not just geometry-plus-attributes. It's geometry-plus-attributes-plus-support-plus-time-plus-CRS-plus-datum. Each of these can be wrong independently. The discipline is making each explicit before any analytical operation.

## Scoring

**Goal: 10/10.** When evaluating a spatial analysis for methodological soundness (not just code correctness), rate 0-10.

- **9-10:** Support declared for every attribute; CRS / datum / time-anchor explicit; MAUP / ecological-fallacy / scale-effect risks named; areal interpolation method (when used) justified; spatial autocorrelation tested; uncertainty propagated.
- **7-8:** Support implicit but consistent; one assumption unverified; analysis correct in spirit but documentation thin.
- **5-6:** Support is implicit and mixed (e.g., joining tract-level attributes to point observations without aggregation); scale-effects mentioned but not analyzed.
- **3-4:** Ecological-fallacy risk present (drawing individual-level inferences from area-level data); MAUP not considered; results sensitive to neighbor-definition unmentioned.
- **1-2:** Spatial analysis as filter-and-map, no methodology behind it.

## The Three Parts of the Book

### Part 1 — Spatial Data (chapters 1-6)

The conceptual foundation: coordinates, geometries, attributes, support, data cubes.

**Key concept: Support.** Attribute values can have point support (a measurement at one location), areal support (an aggregate over a polygon), or grid support (a value per raster cell). Operations that mix supports without acknowledgment produce nonsense.

**Key concept: Datum.** A measurement isn't just a number; it's a number anchored to a reference. Time needs an origin (epoch). Locations need a datum (WGS84, ETRS89, NAD83). Conflating datums introduces meter-scale errors silently.

**Key concept: Data cubes.** Multidimensional arrays organizing spatial + temporal + categorical dimensions. The right abstraction for satellite time series, climate model output, or any data with regular structure across time + space. R's `stars` package implements this; Python equivalents include `xarray` + `xcube`.

### Part 2 — R for Spatial Data Science (chapters 7-9)

The tooling: `sf` for vector, `stars` for raster + data cubes, modern cloud-native approaches.

This part overlaps with Geocomputation-with-R but is denser methodologically. Where Lovelace shows you `st_intersection`, Pebesma & Bivand explain why GEOS gives one answer and S2 gives another on the same data.

### Part 3 — Models for Spatial Data (chapters 10-17)

This is the methodologically-distinctive content: actual spatial statistics, not just spatial data manipulation.

**Areal interpolation** — converting attribute data from one spatial framework to another (e.g., census tracts to school districts). Critical for civic / redistricting / demographic work where source and target geographies don't align.

**Geostatistics (kriging)** — modeling spatial autocorrelation; interpolating point measurements to a continuous surface; quantifying uncertainty at unmeasured locations.

**Spatial regression** — when observations are spatially autocorrelated, OLS assumptions break. Spatial lag models, spatial error models, spatial Durbin models handle this explicitly.

**Point pattern analysis** — for event data (crimes, disease cases), the question is whether the pattern is random / clustered / dispersed and how to test that.

## The Methodological Hazards (the disciplines this skill names)

### MAUP — Modifiable Areal Unit Problem

The same underlying phenomenon can produce dramatically different statistical results depending on how spatial units are defined. Aggregating to counties vs tracts vs block groups can flip the sign of a correlation. There is NO neutral choice of spatial unit; the choice IS analytical.

**Implication:** any analysis that depends on areal aggregation must either (a) demonstrate the result is robust across plausible alternative aggregations, or (b) explicitly acknowledge the unit choice is load-bearing for the conclusion. Civic / electoral work is full of MAUP-sensitive analyses; redistricting is literally MAUP-as-a-political-process.

### Ecological fallacy

Drawing individual-level conclusions from area-level data. "Counties that voted X also have high Y" does NOT mean "people who voted X have high Y." The correlation may be entirely between counties, not within them. Cross-level inference is a separate methodological problem.

**Implication:** keep the unit of analysis explicit in every claim. "Tract-level voting outcomes correlate with tract-level income" is correct; "rich people vote X" is a different claim requiring different data.

### Scale effects

Spatial relationships change with scale. A correlation at the city level may vanish at the neighborhood level (or vice versa). Many spatial phenomena are scale-dependent (urban heat island visible at 100m resolution, invisible at 10km).

**Implication:** scale must be reported. Maps without scale annotation are propaganda. Results without scale documentation are not reproducible.

### Edge effects

Spatial analyses near the edge of the study area have less neighborhood data, biasing results. Hotspot detection at the boundary of a city undercounts (because the analysis can't see beyond the boundary).

**Implication:** either use a buffer larger than the analytical neighborhood, OR explicitly note that edge-region results are biased low.

### Neighbor-definition sensitivity

Spatial weights matrices (used in autocorrelation tests, spatial regression) require choosing neighbors. Queen (any shared boundary), rook (shared edge only), k-nearest (k=3 vs k=5 vs k=10), distance-band (1km vs 5km) — each gives different results.

**Implication:** test multiple neighbor definitions; report sensitivity. Single-spec results without sensitivity analysis are not robust.

## Data-Cube Thinking

The data-cube abstraction (Part 1, chapter 6 in the book) deserves its own framing because it changes how you store spatial + temporal data.

Traditional shape: one file per time-step (one GeoTIFF per day), processed with a loop.
Data-cube shape: a single multidimensional array with `time`, `x`, `y` dimensions, processed with array operations.

**Why this matters:**
- Operations across time become vectorized (mean across time, anomaly from climatology, change detection) instead of loop-and-collect.
- Storage is dense in the dimensions you slice on (cloud-optimized formats like Zarr / COG enable HTTP range reads instead of full downloads).
- Visualizations that animate or compose across time become natural rather than ad-hoc.

For civic / electoral work: think census vintages as a time dimension on a data cube of administrative geographies. Re-running an analysis against the 2010 vs 2020 vintage becomes a dimension-slice, not a re-write.

## When this skill does NOT apply

- **Pure code questions** (how do I read a Shapefile, how do I buffer in PostGIS) — those are `geocomputation-with-r` or engine-specific skills.
- **Visualization craft** — see `storytelling/storytelling-with-data` or the `coding/spatial` map-making skills.
- **Pre-spatial data work** — if your data has no geometry yet, this skill doesn't apply yet.

## Companions

- `geocomputation-with-r` — shelf-mate; applied / code-first counterpart to this theory-first book.
- `coding/postgis` — for SQL-backed geostatistics at database scale.
- `coding/sedona` — distributed compute when data outgrows a single machine; data-cube thinking benefits from distributed array engines.
- `coding/geopandas` — Python sister to sf; data-cube equivalent is `xarray`.
- `_data-trust-rules.md` (always-on) — pairs naturally; spatial analysis with bad attribute trust is doubly broken.

## Source + license

- **Source:** r-spatial.org/book — *Spatial Data Science: With Applications in R* (Edzer Pebesma & Roger Bivand).
- **License:** Creative Commons (CC BY-NC-ND equivalent) for the online edition. Routledge / CRC Press publishes the print edition (January 2025) for purchase.
- **Verified:** WebFetch 2026-05-17 on `r-spatial.org/book/01-hello.html` and `02-Spaces.html` confirms full chapters readable inline with substantial content beyond TOC.

## See also

- Session 260502-pure-vista's `plans/shelf-recommendations-for-su-roles.md` — context on why Spatial Data Science is the methodological-depth complement to Geocomputation with R.
- Self-review SKILL.md role table — the cross-cutting geospatial affirmative standards (CRS hygiene, spatial-index discipline, modern formats, semantic naming, MAUP / ecological fallacy / scale effects) are the same ones this book grounds.
