---
name: spatial
description: "Decision framework for spatial analysis. Determines when to use spatial methods vs. string lookups vs. graph traversal, and which technology and algorithms to apply. Leads with tabular-trust check because in the real world the crosswalk is usually wrong."
routed-by: analysis-methods
---

# Spatial Analysis

Apply this decision framework when facing a problem involving geographic data. See [reference.md](reference.md) for operation code examples, CRS tables, technology comparisons, and dirty-data recipes.

## Step 1: Do You Trust Your Tabular Representation?

Before anything else, assess the quality of identifier-based data. In real-world civic / census / redistricting work, **the tabular representation is usually wrong or stale, and spatial methods exist precisely because of that**.

Ask of every column you're about to JOIN on:

| Question | Red flag |
|---|---|
| What's the vintage of this crosswalk? | "I don't know" or "more than 12 months ago" |
| Does it cover all states / all vintages I need? | Missing rows for Puerto Rico, DC, smaller counties |
| Was the source file updated after the last redistricting cycle? | No, if the crosswalk was built before court orders |
| Are the identifiers spelled consistently? | `"PR"` vs `"RQ"` vs blank for Puerto Rico |
| Is there a `NULL`-or-empty rate ≥ 5% on the join key? | Likely means upstream ingestion is dropping rows |
| Does the crosswalk document its coverage gaps? | No docs → assume gaps |

If **any answer is concerning, skip to Step 3 — you need geometry precisely because the tabular identifiers can't be trusted.**

Common cases where crosswalks lie:
- **ZIP → Congressional District.** ~10% of ZIPs span two or more CDs. Court-ordered re-maps invalidate old crosswalks without warning.
- **FIPS codes across vintages.** State/county FIPS are mostly stable but edge cases exist (Alaska borough changes, merger of Bedford city into Bedford county VA in 2013, new counties in Puerto Rico after 2020).
- **State abbreviations.** USPS (`"PR"`, `"VI"`, `"GU"`, `"MP"`, `"AS"`) vs. Census (sometimes `"RQ"` for Puerto Rico) vs. ISO-3166.
- **Census GEOIDs between 2010/2020.** Block-group and tract boundaries are redrawn; `GEOID20 ≠ GEOID10` for many features.
- **Precinct names.** Spelling and punctuation drift year-to-year even within the same state.

## Step 2: Could a String Lookup *Actually* Work?

Only if Step 1 came back clean. When your tabular data is trustworthy:

| Problem | Looks Like | Solved By |
|---------|-----------|-----------|
| "Which state is this address in?" | Point-in-polygon | **String lookup** (if you already have the `state` column) |
| "Find all donors in this ZIP code" | Spatial query | **String filter** on `zip_code` |
| "How far apart are these two addresses?" | Geodesic distance | **Haversine formula** — two lines of math |
| "Show me all donations within 50 miles of X" | Radius query | **Bounding-box pre-filter** + Haversine |

**Rule:** if a trusted string comparison or simple formula gives the right answer, use it. Spatial libraries add complexity, dependencies, and cost.

## Step 3: What Accuracy Do You Actually Need?

| Level | Example question | Method |
|---|---|---|
| State | "Which state?" | State column / ZIP prefix (99.9%) |
| County | "Which county?" | ZIP-to-county crosswalk if current; else geo join |
| Congressional District | "Which CD?" | Current-vintage crosswalk (~90%) or geo join (~99%) |
| Precinct / block | "Which precinct?" | Geo join only — no shortcut exists |
| Street side | "Which side of the street?" | Full geocoding + precise boundary geometry |

If the problem requires post-redistricting CD assignments and your crosswalk predates the last court order, the "90% crosswalk" number drops fast. Use geometry.

## Step 4: Hidden Graph Problems

Some problems use geographic language but are really about relationships:

| Question | Sounds Spatial | Actually |
|---|---|---|
| "Which donors are connected to this PAC?" | Network map | **Graph traversal** — find nodes within N hops |
| "Which campaigns share donors?" | Geographic overlap | **Bipartite graph** — donor nodes connect campaign nodes |
| "Shortest path between two political networks?" | Route finding | **Graph shortest path** — Dijkstra or BFS |
| "Which vendors work for competing campaigns?" | Spatial clustering | **Graph community detection** |
| "How does money flow through the system?" | Flow map | **Graph flow analysis** — follow directed edges |

If the core question is about **connections between entities** rather than **positions in space**, use a graph database or graph algorithms.

## Step 5: Pick Technology by Scale

| Scale | Single Machine | Distributed |
|---|---|---|
| < 100K points | GeoPandas, SpatiaLite, PostGIS | Overkill |
| 100K – 10M points | PostGIS with spatial index | Overkill unless complex polygons |
| 10M – 100M points | PostGIS with partitioning | Spark + Sedona if cluster available |
| 100M+ points | PostGIS struggles | Spark + Sedona, or tile and parallelize |

## Step 6: Pick Technology by Resources

| Available | Use | Why |
|-----------|-----|-----|
| PostgreSQL with PostGIS | PostGIS | Battle-tested, rich functions, ACID |
| Spark cluster | Sedona (GeoSpark) | Distributed spatial joins |
| Python only | GeoPandas + Shapely | Quick analysis, prototyping |
| SQLite / embedded | SpatiaLite | Zero-config, local lookups |
| Browser / web app | Turf.js or H3 | Client-side operations |
| Nothing — minimal deps | Haversine + bounding box | Surprisingly effective |

## Decision Tree (Linear)

```
START: "I have a spatial problem"
  │
  ├─ Is my tabular representation reliable AND current?
  │   ├─ YES → continue
  │   └─ NO → skip to geometry; crosswalks will 90% but silently
  │
  ├─ Can I solve it with a string join on a crosswalk table?
  │   ├─ YES → Use the crosswalk. Done.
  │   └─ NO (accuracy insufficient, or no crosswalk exists)
  │
  ├─ Can I solve it with simple math (Haversine, bounding box)?
  │   ├─ YES → Write the formula. Done.
  │   └─ NO (need polygon containment, complex spatial joins)
  │
  ├─ Is it really a graph/network problem in disguise?
  │   ├─ YES → Use a graph database or graph algorithms. Done.
  │   └─ NO (genuinely need geometry)
  │
  ├─ How many rows?
  │   ├─ < 10M → PostGIS (or GeoPandas for one-off analysis)
  │   └─ > 10M → Spark + Sedona (or tiled PostGIS with parallelism)
  │
  └─ PROCEED with spatial methods (see reference.md for operations)
```

## Reference Material

See [reference.md](reference.md) for:
- Point-in-polygon patterns at every scale (Shapely, GeoPandas, PostGIS, Sedona)
- Spatial join optimization (subdivide, partition, index both sides)
- Distance and proximity queries (Haversine, KNN, radius search)
- Aggregation by area and apportionment
- Geocoding strategy by volume
- Coordinate reference system (CRS) table
- **Dirty-data recipes: identifier reconciliation, vintage alignment, boundary-edge misses**
- Full technology comparison matrix
- Common spatial mistakes and fixes

## Attribution Policy

NEVER include AI or agent attribution in code, commits, or documentation.
