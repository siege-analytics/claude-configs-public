# Geographic Data Science with Python — Distilled

Principle-level distillation of [*Geographic Data Science with Python*](https://geographicdata.science/book/intro.html) (Sergio J. Rey, Dani Arribas-Bel, Levi J. Wolf; CRC Press, 2023; online CC-BY-NC-ND). The book is the canonical modern reference for spatial analysis on top of GeoPandas + the PySAL ecosystem.

This is paraphrase + commentary for agent guidance, not redistribution.

## Why this book is the spatial-analysis spine

Mastering PostGIS gives us the **engine** principles for spatial Postgres. Geographic Data Science with Python (GDSPy) gives us the **method** principles for spatial analysis on top of any engine — the W matrix, the regionalization algorithm, the spatial cross-validation discipline, the autocorrelation test. Where Mastering PostGIS is engine-faithful (PostgreSQL idioms, GIST indexes, VACUUM), GDSPy is methodology-faithful (the math is engine-agnostic; the book happens to demo it in `pysal` / `geopandas`).

The two complement, they don't overlap. Both are cited and distilled here.

## Chapter map

| Ch | Topic | Where in our refs |
|---|---|---|
| 1 | Geographic thinking | (meta intro; not separately distilled) |
| 2 | Computational tools | (covered by `coding/geopandas/SKILL.md` + `coding/duckdb-spatial/SKILL.md`) |
| 3 | Spatial data | (covered by `coding/geopandas/references/io-formats.md` etc.) |
| 4 | **Spatial weights** | [`spatial-weights.md`](spatial-weights.md) |
| 5 | Choropleth mapping | (covered by SU's `create_choropleth`; see [`siege-utilities-spatial.md`](siege-utilities-spatial.md)) |
| 6 | Global spatial autocorrelation (Moran's I) | [`spatial-statistics.md`](spatial-statistics.md) §1 |
| 7 | Local spatial autocorrelation (LISA, Gi*) | [`spatial-statistics.md`](spatial-statistics.md) §2 + §3 |
| 8 | **Point pattern analysis** | [`point-pattern-analysis.md`](point-pattern-analysis.md) |
| 9 | **Spatial inequality** | [`spatial-inequality.md`](spatial-inequality.md) |
| 10 | **Clustering and regionalization** | [`spatial-statistics.md`](spatial-statistics.md) §7 (clustering) + [`regionalization.md`](regionalization.md) (regionalization) |
| 11 | Spatial regression | [`spatial-statistics.md`](spatial-statistics.md) §5 + §6 |
| 12 | **Spatial feature engineering** | [`spatial-feature-engineering.md`](spatial-feature-engineering.md) |

Bold rows are net-new files added because of GDSPy. The book inspired material in the others as well; see per-file citations.

## What the book gets very right (universal principles)

- **Spatial weights are the model, not a parameter.** Chapter 4 hammers this. The W matrix encodes "what counts as a neighbor" — change W, change every downstream test. Our spatial-statistics work was under-weighting this; [`spatial-weights.md`](spatial-weights.md) is the correction.
- **Regionalization is a constrained-clustering problem.** Chapter 10's separation of clustering (no contiguity constraint) from regionalization (contiguity required) is the right framing. Critical for redistricting work.
- **Spatial cross-validation is non-negotiable for spatial ML.** Chapter 12. Random K-fold leaks signal across spatially-adjacent train/test rows. We had nothing on this; [`spatial-feature-engineering.md`](spatial-feature-engineering.md) corrects it.
- **Spatial inequality decomposes between-group and between-region.** Chapter 9. Treating segregation indices as the only frame misses regional concentration patterns. [`spatial-inequality.md`](spatial-inequality.md) extends our existing segregation coverage.
- **Point pattern analysis isn't out of scope after all.** Chapter 8. For donor-cluster questions, polling-place placement, event-location work — Ripley's K, kernel density, and CSR tests are the right tools. [`point-pattern-analysis.md`](point-pattern-analysis.md) reverses my earlier "out of scope" call.

## What's modern and not in older PySAL writing

- **Sub-package consolidation.** PySAL is now a "metapackage" — actual functionality lives in `libpysal`, `esda`, `spreg`, `mgwr`, `segregation`, `spopt`, `pointpats`, `splot`. The book is current with this naming.
- **`spopt`** — the regionalization sub-package. New in 2022; the canonical home for max-p, SKATER, AZP. Not covered in the older Springer PySAL book.
- **`pointpats`** — point pattern analysis sub-package. New-ish.
- **GeoPandas integration.** The book uses GeoPandas as the data carrier throughout; older PySAL writing predates this maturity.

## How to use this distillation

- For **methodology and rationale**, read the relevant chapter file (linked above).
- For **runnable code recipes**, the book's notebooks at https://github.com/gdsbook/book are CC-licensed and execute against current PySAL.
- For **per-engine implementation** (PostGIS, Sedona, DuckDB equivalents where they exist), see [`spatial-statistics.md`](spatial-statistics.md)'s per-engine matrix.

## Citation

Rey, S.J., Arribas-Bel, D., Wolf, L.J. *Geographic Data Science with Python*. CRC Press, 2023. Online edition (CC-BY-NC-ND): https://geographicdata.science/book/intro.html

Used as inspiration for principles in this reference set; specific code, examples, and worded explanations are Siege's own paraphrase. Not redistributed. The CC-BY-NC-ND license permits attribution-bearing use; commercial use of the original book content requires permission from the publisher.
