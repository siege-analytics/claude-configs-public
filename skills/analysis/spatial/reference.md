# Spatial Analysis Reference

Detailed operation patterns, code examples, and technology tables. Referenced by the main skill.

## Spatial Operations

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

**PostGIS nearest neighbor:**
```sql
SELECT p.name, p.geom <-> ST_SetSRID(ST_MakePoint(:lng, :lat), 4326) AS distance
FROM places AS p
ORDER BY p.geom <-> ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)
LIMIT 5;
```

**PostGIS radius search:**
```sql
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
-- 1 degree latitude ~ 111 km, 1 degree longitude ~ 111 km * cos(lat)
WHERE lat BETWEEN :center_lat - 0.45 AND :center_lat + 0.45
  AND lng BETWEEN :center_lng - 0.45 / COS(RADIANS(:center_lat))
                AND :center_lng + 0.45 / COS(RADIANS(:center_lat))
```

### Aggregation by Area

**If you already have the region assignment** (e.g., state, district, county as a column):
```sql
-- Just GROUP BY — no geometry needed
SELECT state, COUNT(*) AS donations, SUM(amount) AS total
FROM donations
GROUP BY state;
```

**Apportionment** — when a region spans multiple units:
```python
# ZIP 07901 is 60% in NJ-07 and 40% in NJ-10
# A $100 donation from 07901 contributes $60 to NJ-07 and $40 to NJ-10
apportioned_amount = donation_amount * overlap_fraction
```

### Geocoding (Address to Coordinates)

| Volume | Accuracy Needed | Use |
|--------|----------------|-----|
| < 100 addresses | High | Geocoding API (Google, Census, Nominatim) |
| 100 – 10,000 | Medium | Census Geocoder batch API (free, US only) |
| 10K – 1M | Medium | Self-hosted Nominatim or Pelias |
| > 1M | Approximate is OK | ZIP centroid lookup (no geocoding needed) |

**ZIP centroid shortcut:**
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
| UTM zones | 326xx | Accurate distance/area in a specific region (~6 deg longitude wide) |
| State Plane | varies | High accuracy within a US state (for surveying-grade work) |
| Albers Equal Area | 5070 | Area calculations across the continental US |

**Rules:**
- Store in EPSG:4326 (degrees)
- Transform to a projected CRS for distance or area calculations
- Transform back to 4326 for display or export
- Never calculate distance in degrees — 1 degree of longitude varies from 111 km at the equator to 0 km at the poles

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
| Calculating distance in degrees | 1 deg longitude varies by latitude | Transform to projected CRS or use Haversine |
| Using Web Mercator (3857) for area | Distorts area away from equator | Use an equal-area projection (e.g., Albers 5070) |
| No spatial index | Every query scans every polygon | `CREATE INDEX USING GIST (geom)` |
| Geocoding when ZIP centroid suffices | Slow, expensive, rate-limited | Use ZIP centroid table for approximate location |
| Point-in-polygon without ST_Subdivide | Complex polygons (>1000 vertices) are slow | Subdivide to ~256 vertices per piece |
| Using spatial join when a crosswalk exists | 100x more compute for the same answer | Check if a lookup table (ZIP-to-district) exists first |
| Storing coordinates as TEXT | Can't index, can't query, can't transform | Use GEOMETRY or GEOGRAPHY type |
| Mixing CRS without transforming | Points miss their polygons | Always `ST_Transform` to match the target CRS |
