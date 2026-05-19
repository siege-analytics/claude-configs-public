---
name: geocomputation-with-r
description: 'Practical, applied geospatial computing using open-source tools. Use when the user mentions "spatial join", "reproject", "CRS", "geocomputation", "sf package", "terra package", "raster vs vector", "spatial operations", "geographic data I/O", "make a map in R", "Lovelace", "geocompx", or general GIS-in-R workflows. Also trigger when reasoning about CRS choice for an operation, picking between vector and raster representations, debugging projection issues, designing spatial analysis pipelines, or onboarding to spatial work in R. R-flavored but the principles (CRS hygiene, vector / raster choice, spatial-index discipline, reproducible workflows) transfer directly to Python / PostGIS / other engines. Pairs with spatial-data-science for deeper methodology. For Python-specific code see geopandas / postgis / duckdb-spatial skills.'
license: CC-BY-NC-ND-4.0
metadata:
  source: 'r.geocompx.org — full free online edition of Geocomputation with R (Lovelace, Nowosad, Muenchow). CRC Press also publishes paid print edition.'
  coverage: 'Full book (16 chapters) freely readable inline at r.geocompx.org. Open license; verified 2026-05-17 via WebFetch.'
---

# Geocomputation with R Framework

A grounded, practical framework for doing real geographic work with open-source tooling. The book teaches a range of spatial skills — reading / writing / manipulating geographic file formats; making static and interactive maps; applying geocomputation to support evidence-based decision-making across transport, ecosystems, and other geographic phenomena.

## Core Principle

**Geospatial work is reproducible computation, not GUI clicking.** The shift from GUI-based GIS (ArcGIS, QGIS) to command-line geocomputation is the same shift that statistics made when moving from SPSS to R: enabling reproducibility, version control, code review, and integration with the broader scientific workflow. Spatial operations are just operations; the data model has geometry alongside attributes, but the discipline of writing code that another person (or future-you) can re-run is the same.

**The foundation:** every spatial operation has assumptions baked in — about what CRS the data is in, what coordinate system the operation expects, whether the answer should be in degrees or meters, whether a "distance" is Euclidean or great-circle. Most spatial bugs come from CRS / datum / unit mismatches that the code silently coerces. Geocomputation discipline names these assumptions explicitly.

## Scoring

**Goal: 10/10.** When evaluating a spatial analysis pipeline (script, notebook, workflow), rate 0-10 on geocomputation discipline.

- **9-10:** CRS named explicitly at every step; reprojection happens at known points; units propagated correctly; vector vs raster choice justified; spatial-index used before any `ST_*` predicate; reproducible end-to-end from raw source to output map.
- **7-8:** CRS handled correctly but implicitly; one or two unit conversions assumed rather than declared; map renders but workflow has manual steps.
- **5-6:** CRS works but the author can't say which projection or why; mixing geographic and projected data without verification; spatial-index missing on a slow query.
- **3-4:** Distance calculated on lon/lat degrees treated as meters; spatial joins return wrong results due to CRS mismatch; the analyst doesn't know why the map looks distorted.
- **1-2:** Spatial data in a generic data-frame with no spatial semantics; "spatial analysis" is filter-by-name; no CRS metadata at all.

## The Vector / Raster Data Model

Geographic data lives in two representations. Knowing which fits the question is the first geocomputation decision.

| Aspect | Vector | Raster |
|---|---|---|
| **Geometry** | Discrete points, lines, polygons with exact coordinates | Continuous grid cells with regular spacing |
| **Tooling (R)** | `sf` package (interfaces GEOS, GDAL, PROJ, S2) | `terra` package (modern; replaces older `raster`) |
| **Best for** | Administrative boundaries, transport networks, addresses, point observations | Elevation, temperature, satellite imagery, continuous fields |
| **Operations** | Geometric (intersect, union, buffer), topological (within, touches), measurement (length, area) | Algebraic (sum across layers), focal (window operations), zonal (aggregate by polygon) |
| **Storage** | GeoPackage, GeoJSON, Shapefile (legacy), GeoParquet | GeoTIFF, COG (Cloud Optimized GeoTIFF), Zarr, NetCDF |
| **Memory model** | In-memory tabular | Can stream from disk (terra supports tile-based access) |

**The `sf` simple-feature object** combines three components:
- `sfg` — individual geometries
- `sfc` — geometry columns (sets of geometries)
- `sf` — full spatial data frames (attributes + geometry column)

This composition makes spatial data a data-frame with spatial extensions, integrating cleanly with dplyr / tidyverse pipelines. The same conceptual shape exists in Python's geopandas.

**Modern format choice:** GeoPackage > Shapefile for vector (no 10-char field limit, no dbf encoding hell, single file). GeoParquet for columnar workflows. COG > plain GeoTIFF for raster (HTTP range requests, no full download). The Lovelace text doesn't push these hard but the modern consensus is clear.

## CRS Discipline (the chapter that prevents the most bugs)

CRS work is where most spatial code fails silently. Lovelace's chapter 7 framing:

### Identify CRS by AUTHORITY:CODE, not proj-string

`EPSG:4326` is future-proof, widely understood, and survives software upgrades. Proj-strings like `+proj=longlat +ellps=WGS84` are deprecated for identification.

### WKT (Well-Known Text) is the source of truth

If a file has both a proj-string and a WKT representation, the WKT wins. Modern PROJ (5+) uses WKT internally.

### Geometry engine selection matters

`sf` defaults:
- **Projected data:** GEOS (Cartesian geometry; fast)
- **Geographic data (lon/lat):** S2 spherical geometry (handles antimeridian, polar regions correctly)

Forcing GEOS on geographic data is a common bug — it treats degrees as Cartesian, producing distorted distances elongated along the north-south axis.

### Common CRS choices

| CRS | EPSG | Use for |
|---|---|---|
| WGS84 (geographic) | 4326 | Storage; web mapping; GPS data |
| Web Mercator (projected) | 3857 | Web tiles only — distorts area badly outside ±60° latitude |
| UTM (projected, zone-specific) | 32601-32760 (north), 32701-32760 (south) | Distance / area calculations within a single zone |
| Lambert Conformal Conic / Albers Equal Area | various national/regional codes | Country-scale equal-area maps (Albers) or shape-preserving (Lambert) |
| US National Atlas Equal Area | 2163 | US-wide equal-area work |
| British National Grid | 27700 | UK national-grid data |

### When to reproject

- Comparing or combining objects with different CRSs (always reproject; CRS mismatch silently corrupts joins)
- Publishing data online (web maps want geographic CRS or web Mercator)
- Distance or area calculations (must be in projected CRS with linear units, OR use spherical engine on geographic CRS)
- Optimizing for a property (equal area, conformal shape, equidistant)

### Anti-patterns

- Assuming all coordinates use the same CRS without verification (`st_crs(x) == st_crs(y)` before joins)
- Buffer / distance on geographic coordinates without spherical-geometry engine
- Using proj-strings with deprecated keys (`+nadgrids`, `+towgs84`, `+init=epsg:`)
- Picking a single projection for all phases of a project; different operations want different projections

## The Operation Catalog (chapters 3-6 condensed)

### Attribute operations (chapter 3)

Spatial data is a data-frame; non-spatial operations (filter, mutate, join, summarize) work exactly as on any data-frame. `sf` plays well with `dplyr`.

### Spatial operations (chapter 4)

Operations that USE the geometry: spatial subsetting (`st_intersects`, `st_within`), spatial joins (attach attributes by geometry-relation), spatial aggregation (group by polygon).

**Predicate types:**
- Topological: `st_intersects`, `st_touches`, `st_overlaps`, `st_disjoint`
- Distance-based: `st_is_within_distance`, `st_distance`
- Containment: `st_within`, `st_contains`, `st_covers`

### Geometry operations (chapter 5)

Operations that MODIFY the geometry: union, intersection, difference, buffer, centroid, simplify, convex hull, voronoi.

Important detail: simplification (`st_simplify`) on touching polygons creates gaps. For administrative boundaries, use `rmapshaper::ms_simplify` (topology-aware) instead of naive `st_simplify`.

### Raster-vector interactions (chapter 6)

Extract raster values at vector locations (`terra::extract`), rasterize vector data, mask raster by polygon, polygonize raster. The bridge between the two data models.

## Spatial Index Discipline

For any predicate involving `ST_*`, a spatial index transforms an O(N×M) operation into something close to O((N+M) log N). On PostGIS:

```sql
CREATE INDEX idx_my_geom ON my_table USING GIST (geom);
```

In R/sf:
- `sf` operations use STRtree spatial indices automatically.
- For repeated queries against the same data, build the index explicitly: `geo_index <- sf::st_geometry(data)`.

Without indexes, large spatial joins take hours when they should take seconds. This is the most common "the script never finishes" failure.

## Reproducibility + Reproducible Workflows

The book's overall stance: spatial work is real research; it should be version-controlled, peer-reviewable, and re-runnable from raw input to output. Scripts > notebooks > manual GUI workflows. Document your data sources, your CRS choices, your assumptions, your simplification thresholds.

## When this skill does NOT apply

- **Pure attribute analysis** with no spatial semantics → use general data-frame tooling.
- **Python-specific code** → use `geopandas` skill for direct Python equivalents (the principles transfer 1:1; the syntax differs).
- **Engine-specific tuning** → use `postgis` / `duckdb-spatial` / `sedona` skills for engine choice given scale.
- **Deeper methodology** (support, areal interpolation, geostatistics) → use `spatial-data-science` (Pebesma & Bivand) which goes deeper on theory.

## Companions

- `spatial-data-science` — same shelf; deeper methodological book that complements this applied one.
- `coding/postgis` — for SQL-backed spatial work at scale.
- `coding/geopandas` — Python equivalent of the sf workflow.
- `coding/sedona` — distributed spatial compute (Spark) when the data outgrows a single machine.
- `coding/duckdb-spatial` — in-process columnar spatial for medium-sized analytical work.

## Source + license

- **Source:** r.geocompx.org — full free online edition of *Geocomputation with R* (Robin Lovelace, Jakub Nowosad, Jannes Muenchow).
- **License:** Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0) for the online edition. CRC Press print edition is paid.
- **Verified:** WebFetch 2026-05-17 on `r.geocompx.org` confirms the table of contents is the full 16 chapters and chapter pages (verified Chapter 2 "Spatial Class" + Chapter 7 "Reprojecting Geographic Data") have full content readable inline.

## See also

- The Python equivalent *Geocomputation with Python* at `py.geocompx.org` is in development — at the time of absorption (2026-05-17), `py.geocompx.org` is primarily a landing page with chapter content not yet fully online; the R version is the canonical free reference.
- `spatial-data-science` shelf-mate for theory depth.
- Session 260502-pure-vista's `plans/shelf-recommendations-for-su-roles.md` — context on why Geocomputation with R is the chosen geospatial-shelf-floor entry.
