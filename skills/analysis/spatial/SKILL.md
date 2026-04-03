---
name: spatial
description: Decision framework for spatial analysis. Determines when to use spatial methods vs. string lookups vs. graph traversal, and which technology and algorithms to apply.
routed-by: analysis-methods
---

# Spatial Analysis

Apply this decision framework when facing a problem involving geographic data. The first question is always whether you actually need spatial methods at all. See [reference.md](reference.md) for operation code examples, CRS tables, and technology comparisons.

## Step 1: Do You Actually Need Geometry?

Many problems that look spatial can be solved faster without touching geometry.

| Problem | Looks Like | Actually Solved By |
|---------|-----------|-------------------|
| "Which district is this address in?" | Point-in-polygon | **String join** on a ZIP-to-district crosswalk table |
| "Find all donors in this ZIP code" | Spatial query | **String filter** on `zip_code` column |
| "Which donors gave to campaigns in neighboring districts?" | Spatial proximity | **Graph traversal** — donors and campaigns are nodes |
| "How far apart are these two addresses?" | Geodesic distance | **Haversine formula** — two lines of math |
| "Show me all donations within 50 miles" | Radius query | **Bounding box pre-filter** + Haversine |
| "Which state does this coordinate fall in?" | Point-in-polygon | **String lookup** if you already have the state |

**Rule:** If a string comparison or simple formula gives you the answer with acceptable accuracy, use that. Spatial libraries add complexity, dependencies, and cost.

## Step 2: What Accuracy Do You Need?

| Accuracy Level | Example | Acceptable Method |
|---------------|---------|-------------------|
| **State level** | "Which state?" | String lookup on state column or ZIP prefix |
| **County level** | "Which county?" | ZIP-to-county crosswalk (FIPS codes) |
| **Congressional district** | "Which CD?" | ZIP-to-CD crosswalk (~90% accuracy) or point-in-polygon (~99%) |
| **Precinct / block** | "Which precinct?" | Point-in-polygon with geocoded address — no shortcut |
| **Street level** | "Which side of the street?" | Full geocoding + precise boundary geometry |

The crosswalk approach fails when a ZIP code spans multiple districts. About 10% of ZIP codes span two or more CDs. If 90% accuracy is acceptable, use the crosswalk.

## Step 3: How Much Data?

| Scale | Single Machine | Distributed |
|-------|---------------|-------------|
| < 100K points | GeoPandas, SpatiaLite, PostGIS | Overkill |
| 100K – 10M points | PostGIS with spatial index | Overkill unless complex polygons |
| 10M – 100M points | PostGIS with partitioning | Spark + Sedona if cluster available |
| 100M+ points | PostGIS struggles | Spark + Sedona, or tile and parallelize |

## Step 4: What Resources Are Available?

| Available | Use | Why |
|-----------|-----|-----|
| PostgreSQL with PostGIS | PostGIS | Battle-tested, rich functions, ACID |
| Spark cluster | Sedona (GeoSpark) | Distributed spatial joins |
| Python only | GeoPandas + Shapely | Quick analysis, prototyping |
| SQLite / embedded | SpatiaLite | Zero-config, local lookups |
| Browser / web app | Turf.js or H3 | Client-side operations |
| Nothing — minimal deps | Haversine + bounding box | Surprisingly effective |

## Decision Tree

```
START: "I have a spatial problem"
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

## When It's Actually a Graph Problem

Some problems use geographic language but are really about relationships:

| Question | Sounds Spatial | Actually |
|----------|---------------|---------|
| "Which donors are connected to this PAC?" | Network map | **Graph traversal** — find nodes within N hops |
| "Which campaigns share donors?" | Geographic overlap | **Bipartite graph** — donor nodes connect campaign nodes |
| "Shortest path between two political networks?" | Route finding | **Graph shortest path** — Dijkstra or BFS |
| "Which vendors work for competing campaigns?" | Spatial clustering | **Graph community detection** |
| "How does money flow through the system?" | Flow map | **Graph flow analysis** — follow directed edges |

If the core question is about **connections between entities** rather than **positions in space**, use a graph database or graph algorithms.

## Reference Material

See [reference.md](reference.md) for:
- Point-in-polygon patterns at every scale (Shapely, GeoPandas, PostGIS, Sedona)
- Spatial join optimization (subdivide, partition, index both sides)
- Distance and proximity queries (Haversine, KNN, radius search)
- Aggregation by area and apportionment
- Geocoding strategy by volume
- Coordinate reference system (CRS) table
- Full technology comparison matrix
- Common spatial mistakes and fixes

## Attribution Policy

NEVER include AI or agent attribution in code, commits, or documentation.
