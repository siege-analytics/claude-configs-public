---
name: shelf-geospatial
description: Router for geospatial book skills. Dispatches to geocomputation-with-r (applied / code-first) or spatial-data-science (theory / methodology) based on task signals. Read this when the task involves CRS choice, spatial joins, raster vs vector decisions, areal interpolation, MAUP / ecological fallacy / scale effects, or any geographic analysis that needs methodological grounding beyond engine-specific code. For engine-specific syntax see coding/postgis, coding/geopandas, coding/sedona, coding/duckdb-spatial.
---

# Geospatial -- Shelf

Books grounding geographic analysis: the principles that make spatial computing non-fraudulent. Load the book that matches your task signal and read its full SKILL.md.

## Trigger table

| Task signal | Book to read |
|---|---|
| CRS / reprojection / spatial-operations / vector vs raster choice; "how do I do this in R / Python / PostGIS" applied questions | [`geocomputation-with-r`](../../shelves/geospatial/geocomputation-with-r/SKILL.md) |
| Support / MAUP / ecological fallacy / scale effects / areal interpolation / geostatistics / spatial regression; "what does this concept actually mean" questions | [`spatial-data-science`](../../shelves/geospatial/spatial-data-science/SKILL.md) |

## Books in this shelf

- [`geocomputation-with-r`](../../shelves/geospatial/geocomputation-with-r/SKILL.md) -- Lovelace, Nowosad, Muenchow. *Geocomputation with R*. Applied / code-first; 16 chapters covering classes, operations, CRS, raster-vector, I/O, mapping. Full free online at r.geocompx.org.
- [`spatial-data-science`](../../shelves/geospatial/spatial-data-science/SKILL.md) -- Pebesma & Bivand. *Spatial Data Science: With Applications in R*. Theory / methodology-first; 17+ chapters across spatial-data, R-tooling, models-for-spatial-data. Full free online at r-spatial.org/book.

## Disambiguation

- **geocomputation-with-r vs spatial-data-science:** geocomputation teaches WHAT to do; spatial-data-science teaches WHY. Load geocomputation when writing code; load spatial-data-science when reasoning about whether the analysis is methodologically defensible. They compose: load both for new spatial work.
- **geospatial shelf vs coding/postgis (and friends):** shelf books are book-shaped -- frameworks + first-principles. `coding/<engine>` skills are operation-level -- syntax for a specific engine. Use shelf books to ground the principles; use coding skills for the actual API calls.

## When to use this shelf

- Designing a new spatial analysis pipeline.
- Debugging a spatial result that "looks wrong" but the code runs.
- Choosing a CRS for an operation.
- Reasoning about whether an areal aggregation is appropriate for the question.
- Onboarding to spatial work in any language / engine.

## When NOT to use this shelf

- **Engine-specific syntax** → use `coding/postgis`, `coding/geopandas`, `coding/sedona`, `coding/duckdb-spatial`.
- **Pure visualization craft** → use `storytelling/storytelling-with-data` plus map-rendering coding skills.
- **Non-spatial work** → no.

## Always-on companions

- `_data-trust-rules.md` -- applies to any data, doubly to spatial data (CRS is one more dimension where trust can be wrong).
- `engineering-principles/` shelf -- for the code-craft floor that any spatial analysis script should meet.

## Origin

Geospatial gap surfaced in the shelf-coverage joint design (sessions 260502-pure-vista + 260502-vital-channel, 2026-05-17). The role table in skills/self-review/SKILL.md calls out the cross-cutting geospatial affirmative standards this shelf grounds: CRS appropriateness, spatial-index hygiene, modern format choice (GeoParquet / COG / Zarr), semantic naming, MAUP / ecological fallacy / scale effects.
