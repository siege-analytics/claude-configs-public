---
name: spatial
description: Decision framework for spatial analysis. Determines when a problem truly requires spatial methods vs. string lookups vs. graph traversal, which technology to use, and which algorithms to apply.
---

# Spatial Analysis

## When to Use This Skill

When facing a problem that involves geographic data — locations, boundaries, distances, areas, or spatial relationships. The first question is always whether you actually need spatial methods at all.

## The Decision Framework

### Step 1: Do You Actually Need Geometry?

Many problems that look spatial can be solved faster and simpler without touching geometry at all.

| Problem | Looks Like | Actually Solved By |
|---------|-----------|-------------------|
| "Which district is this address in?" | Point-in-polygon | **String join** on a ZIP-to-district crosswalk table (if ZIP granularity is sufficient) |
| "Find all donors in this ZIP code" | Spatial query | **String filter** on `zip_code` column |
| "Which donors gave to campaigns in neighboring districts?" | Spatial proximity | **Graph traversal** — donors and campaigns are nodes, donations are edges |
| "How far apart are these two addresses?" | Geodesic distance | **Haversine formula** — two lines of math, no GIS library needed |
| "Show me all donations within 50 miles of this city" | Radius query | **Bounding box pre-filter** + Haversine, or a simple lat/lng range check |
| "Which state does this coordinate fall in?" | Point-in-polygon | **R-tree index lookup** if you do this at scale, or a **string lookup** if you already have the state |

**Rule:** If a string comparison or a simple formula gives you the answer with acceptable accuracy, use that. Spatial libraries add complexity, dependencies, and computation cost.

### Step 2: What Accuracy Do You Need?

| Accuracy Level | Example | Acceptable Method |
|---------------|---------|-------------------|
| **State level** | "Which state?" | String lookup on state column or ZIP prefix |
| **County level** | "Which county?" | ZIP-to-county crosswalk (FIPS codes) |
| **Congressional district** | "Which CD?" | ZIP-to-CD crosswalk (~90% accuracy) or point-in-polygon (~99%) |
| **Precinct / block** | "Which precinct?" | Point-in-polygon with geocoded address — no shortcut |
| **Street level** | "Which side of the street?" | Full geocoding + precise boundary geometry |

The crosswalk approach fails when a ZIP code spans multiple districts. For congressional districts, about 10% of ZIP codes span two or more CDs. If 90% accuracy is acceptable, use the crosswalk. If you need 99%+, you need actual geometry.

### Step 3: How Much Data?

| Scale | Single Machine | Distributed |
|-------|---------------|-------------|
| < 100K points | GeoPandas, SpatiaLite, PostGIS | Overkill |
| 100K – 10M points | PostGIS, GeoPandas (with spatial index) | Overkill unless join is against complex polygons |
| 10M – 100M points | PostGIS (with partitioning and indexes) | Spark + Sedona if you already have a cluster |
| 100M+ points | PostGIS struggles, even with partitioning | Spark + Sedona, or tile and parallelize |

### Step 4: What Resources Are Available?

| Available | Use | Why |
|-----------|-----|-----|
| PostgreSQL with PostGIS | PostGIS | Battle-tested, rich function library, ACID transactions |
| Spark cluster | Sedona (GeoSpark) | Distributed spatial joins, scales horizontally |
| Python only (no database) | GeoPandas + Shapely | Quick analysis, prototyping, small data |
| SQLite / embedded | SpatiaLite | Zero-config, good for caching and local lookups |
| Browser / web app | Turf.js or H3 | Client-side spatial operations |
| Nothing — minimal dependencies | Haversine + bounding box math | Surprisingly effective for distance and containment |

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
  └─ PROCEED with spatial methods below.
```

## Spatial Operations Reference

### Point-in-Polygon (Containment)

**Problem:** Given a point (lat/lng), determine which polygon it falls inside.

**Approaches by scale:**

```
< 1,000 lookups:     Linear scan with Shapely
< 100,000 lookups:   R-tree index (GeoPandas sjoin, SpatiaLite)
< 10,000,000:        PostGIS with GIST index
> 10,000,000:        Spark + Sedona or tiled PostGIS
```

**PostGIS:**
```sql
SELECT b.district_id
FROM district_boundaries AS b
WHERE ST_Contains(b.geom, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326));
```

**GeoPandas:**
```python
import geopandas as gpd

points = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lng, df.lat), crs="EPSG:4326")
boundaries = gpd.read_file("districts.shp")
result = gpd.sjoin(points, boundaries, predicate="within")
```

**Spark + Sedona:**
```python
from sedona.spark import SedonaContext

points_df = spark.sql("""
    SELECT id, ST_Point(lng, lat) AS geom FROM donations
""")
boundaries_df = spark.sql("""
    SELECT district_id, geom FROM district_boundaries
""")
result = points_df.join(boundaries_df, F.expr("ST_Contains(boundaries.geom, points.geom)"))
```

### Spatial Join (Many-to-Many)

**Problem:** Match every point to its containing polygon (or every polygon pair that intersects).

**This is the most expensive spatial operation.** Optimize aggressively.

**Optimization techniques:**
1. **Pre-filter with bounding box:** `ST_Intersects` uses the spatial index (bounding box) before exact geometry check
2. **Subdivide complex polygons:** `ST_Subdivide(geom, 256)` breaks one complex polygon into many simple ones
3. **Partition by region:** Process each state/region separately to limit the join scope
4. **Index both sides:** GIST indexes on both the point and polygon tables

**PostGIS (optimized):**
```sql
-- Subdivide complex boundaries first (one-time prep)
CREATE TABLE boundaries_subdivided AS
SELECT district_id, ST_Subdivide(geom, 256) AS geom
FROM district_boundaries;
CREATE INDEX ON boundaries_subdivided USING GIST (geom);

-- Spatial join against subdivided boundaries
SELECT d.id, d.amount, b.district_id
FROM donations AS d
INNER JOIN boundaries_subdivided AS b
    ON ST_Contains(b.geom, d.geom);
```

### Distance and Proximity

**Problem:** Find things near a location, or calculate distance between locations.

**For distance between two points — no library needed:**

```python
from math import radians, cos, sin, asin, sqrt

def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distance in kilometers between two lat/lng points."""
    lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlng / 2) ** 2
    return 6371 * 2 * asin(sqrt(a))
```

**For nearest neighbor at scale:**

```sql
-- PostGIS: K-nearest neighbor using <-> operator (uses GIST index)
SELECT p.name, p.geom <-> ST_SetSRID(ST_MakePoint(:lng, :lat), 4326) AS distance
FROM places AS p
ORDER BY p.geom <-> ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)
LIMIT 5;
```

**For "everything within N km":**

```sql
-- PostGIS: use geography type for distance in meters
SELECT *
FROM locations
WHERE ST_DWithin(
    geom::geography,
    ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
    50000  -- 50 km in meters
);
```

**Bounding box pre-filter (no spatial library):**

```sql
-- Approximate: filter by lat/lng range before exact distance calculation
-- 1 degree latitude ≈ 111 km, 1 degree longitude ≈ 111 km * cos(lat)
WHERE lat BETWEEN :center_lat - 0.45 AND :center_lat + 0.45
  AND lng BETWEEN :center_lng - 0.45 / COS(RADIANS(:center_lat))
                AND :center_lng + 0.45 / COS(RADIANS(:center_lat))
```

### Aggregation by Area

**Problem:** Sum, count, or average values within geographic regions.

**If you already have the region assignment** (e.g., state, district, county as a column):
```sql
-- Just GROUP BY — no geometry needed
SELECT state, COUNT(*) AS donations, SUM(amount) AS total
FROM donations
GROUP BY state;
```

**If you need to assign regions first, then aggregate:**
1. Spatial join to assign regions (see above)
2. Then GROUP BY the region column

**Apportionment** — when a point falls in overlapping regions or a region spans multiple units:
```python
# ZIP 07901 is 60% in NJ-07 and 40% in NJ-10
# A $100 donation from 07901 contributes $60 to NJ-07 and $40 to NJ-10
apportioned_amount = donation_amount * overlap_fraction
```

### Geocoding (Address to Coordinates)

**Problem:** Convert a street address to lat/lng.

**Decision:**

| Volume | Accuracy Needed | Use |
|--------|----------------|-----|
| < 100 addresses | High | Geocoding API (Google, Census, Nominatim) |
| 100 – 10,000 | Medium | Census Geocoder batch API (free, US only) |
| 10K – 1M | Medium | Self-hosted Nominatim or Pelias |
| > 1M | Approximate is OK | ZIP centroid lookup (no geocoding needed) |

**ZIP centroid shortcut:**
If you only need approximate location (within ~10 km), look up the ZIP code's centroid from Census ZCTA data. This is a simple table join — no geocoding API, no rate limits, no cost.

```sql
SELECT d.*, z.latitude, z.longitude
FROM donations AS d
LEFT JOIN zip_centroids AS z ON d.zip_code = z.zip_code;
```

## Coordinate Reference Systems (CRS)

| CRS | EPSG | Use For |
|-----|------|---------|
| WGS84 | 4326 | Storage, exchange, GPS coordinates (lat/lng in degrees) |
| Web Mercator | 3857 | Web maps (Leaflet, Mapbox). **Never** use for area/distance calculations |
| UTM zones | 326xx | Accurate distance/area in a specific region (~6° longitude wide) |
| State Plane | varies | High accuracy within a US state (for surveying-grade work) |
| Albers Equal Area | 5070 | Area calculations across the continental US |

**Rules:**
- Store in EPSG:4326 (degrees)
- Transform to a projected CRS for distance or area calculations
- Transform back to 4326 for display or export
- Never calculate distance in degrees — 1 degree of longitude varies from 111 km at the equator to 0 km at the poles

## When It's Actually a Graph Problem

Some problems use geographic language but are really about relationships:

| Question | Sounds Spatial | Actually |
|----------|---------------|---------|
| "Which donors are connected to this PAC?" | Network map | **Graph traversal** — find nodes within N hops |
| "Which campaigns share donors?" | Geographic overlap | **Bipartite graph** — donor nodes connect campaign nodes |
| "What's the shortest path between these two political networks?" | Route finding | **Graph shortest path** — Dijkstra or BFS |
| "Which vendors work for competing campaigns?" | Spatial clustering | **Graph community detection** — find clusters of shared vendors |
| "How does money flow through the system?" | Flow map | **Graph flow analysis** — follow directed edges |

If the core question is about **connections between entities** rather than **positions in space**, use a graph database (Neo4j, NetworkX) instead of a spatial engine.

## Technology Quick Reference

| Tool | Strengths | Weaknesses | Best For |
|------|-----------|------------|----------|
| **PostGIS** | Full SQL integration, ACID, rich functions, mature | Single machine, complex setup | Production spatial queries, moderate scale |
| **GeoPandas** | Easy to use, Python-native, great for prototyping | Memory-bound, single thread | Exploration, small datasets, visualization |
| **Shapely** | Pure geometry operations, no I/O overhead | No spatial index, slow for bulk | Geometry manipulation in Python code |
| **SpatiaLite** | Zero-config, embedded, portable | Limited functions vs PostGIS | Local caching, mobile, embedded apps |
| **Sedona** | Distributed, scales to billions, Spark integration | Cluster required, startup overhead | Large-scale spatial joins on existing Spark infra |
| **H3** | Fast hexagonal indexing, resolution levels | Approximation (not exact geometry) | Aggregation by area, heatmaps, binning |
| **Turf.js** | Client-side, no server needed | JavaScript only, small data | Browser-based spatial analysis |
| **GDAL/OGR** | Format conversion, projection, CLI tools | Not a query engine | ETL for spatial formats (Shapefile, GeoJSON, etc.) |

## Common Mistakes

| Mistake | Problem | Fix |
|---------|---------|-----|
| Calculating distance in degrees | 1° longitude varies by latitude | Transform to projected CRS or use Haversine |
| Using Web Mercator (3857) for area | Distorts area away from equator | Use an equal-area projection (e.g., Albers 5070) |
| No spatial index | Every query scans every polygon | `CREATE INDEX USING GIST (geom)` |
| Geocoding when ZIP centroid suffices | Slow, expensive, rate-limited | Use ZIP centroid table for approximate location |
| Point-in-polygon without ST_Subdivide | Complex polygons (>1000 vertices) are slow | Subdivide to ~256 vertices per piece |
| Using spatial join when a crosswalk exists | 100x more compute for the same answer | Check if a lookup table (ZIP→district) exists first |
| Storing coordinates as TEXT | Can't index, can't query, can't transform | Use GEOMETRY or GEOGRAPHY type |
| Mixing CRS without transforming | Points miss their polygons | Always `ST_Transform` to match the target CRS |

## Attribution Policy

NEVER include AI or agent attribution in code, commits, or documentation.
