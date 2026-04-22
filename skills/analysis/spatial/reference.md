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


# Addendum to analysis/spatial/reference.md

Proposed new section to append after the "Common Mistakes" table. Positions the dirty-tabular-data reality, which the SKILL.md now leads with.

---

## Dirty Tabular Data — Why Geometry Exists

In real-world civic / census / redistricting work, the tabular representation is usually the *reason* you need geometry. The crosswalks, FIPS codes, and state columns users rely on are wrong more often than anyone admits.

### Common lies

| Lie | What actually happens |
|---|---|
| "ZIP → Congressional District is a 1-to-1 table" | ~10% of ZIPs span multiple CDs. Court-ordered redistricts invalidate tables mid-cycle. |
| "FIPS codes are stable" | Mostly true — except Alaska borough reorgs (Wrangell 2008, Hoonah-Angoon 2015), Bedford VA county merger (2013), new Puerto Rico municipios. |
| "Census GEOIDs for tracts stay the same" | They change every decennial. `GEOID20 ≠ GEOID10` for most features. |
| "State abbreviation 'PR' means Puerto Rico everywhere" | USPS: `PR`. Census sometimes: `RQ`. ISO-3166: `PR`. Some voter files: `P.R.` with dots. |
| "The precinct name is consistent year-to-year" | Spelling drift. `"WARD 1 PCT 3"` becomes `"Ward 1-3"` becomes `"W1P3"` without warning. |
| "Contributor address normalization is uniform" | Abbreviations (`Street`/`St.`/`St`), apartment handling (`#4`/`Apt 4`/`Unit 4`), and typo rates vary by source. |
| "The crosswalk file's publication date equals its data vintage" | No. A 2024-published ZIP-to-CD crosswalk may use 2020 CD boundaries even if states have since redrawn. |

### Vintage alignment

Any join involving geographies has an implicit `year` dimension. Always pin it:

```python
# BAD: which vintage of FIPS are you joining?
merged = donors.merge(counties, on="county_fips")

# GOOD: make the vintage explicit
counties_2020 = counties[counties.year == 2020]
merged = donors.merge(counties_2020, on="county_fips")
assert merged["county_name_2020"].isna().sum() == 0, "unmatched counties"
```

When the upstream source doesn't expose vintage, you can sometimes detect it by row count (Alaska has 30 boroughs post-2008, 25 pre). Where detection fails, treat the source as untrusted and use geometry.

### Identifier reconciliation patterns

**1. Build a crosswalk with explicit coverage.**

```python
# A reconciliation table that names every identifier system involved
@dataclass
class StateIdentifiers:
    fips: str         # "48"
    usps: str         # "TX"
    iso3166: str      # "US-TX"
    census_name: str  # "Texas" — but watch "District of Columbia" vs "DC"
    common: str       # "Texas"
```

Then any code that takes "a state" runs through a single `normalize_state(raw) -> StateIdentifiers`.

**2. Validate at ingestion boundaries.**

Don't trust an upstream `state` column to be 2-char USPS. Coerce and raise on unknown:

```python
def normalize_state(raw: str) -> str:
    if raw in USPS_CODES:
        return raw
    if raw in FIPS_TO_USPS:
        return FIPS_TO_USPS[raw]
    if raw.upper() in NAME_TO_USPS:
        return NAME_TO_USPS[raw.upper()]
    raise ValueError(f"unknown state identifier: {raw!r}")
```

Do the same for ZIP (sometimes a 9-digit ZIP+4 gets split, sometimes not), FIPS (leading zeros stripped by Excel), and party (`D`/`DEM`/`Democratic`/`democrat`).

**3. Log mismatches at coarse granularity.**

When you DO join and some rows drop, log it with enough context to reproduce:

```python
pre = len(donors)
merged = donors.merge(districts, on=["state", "cd"], how="left")
unmatched = merged[merged["district_id"].isna()]
log_warning(
    f"district join lost {len(unmatched)} of {pre} donors "
    f"({len(unmatched)/pre:.1%}); unique unmatched (state, cd): "
    f"{unmatched[['state', 'cd']].drop_duplicates().head(10).to_dict('records')}"
)
```

Silent NaN rows are how dirty data corrupts analytics. A logged count turns "analysis is wrong" into "diagnostics say 3% of rows were dropped, here's why."

### Boundary-edge misses

Point-in-polygon can also lie:

- **Coastline mismatch.** TIGER coastline != Natural Earth coastline != RDH coastline. A lat/lng near the shore may fall in no polygon, or two polygons, depending on which source.
- **Shared state borders.** Segments on the Texas-Louisiana line may have small (< 100m) drift between TIGER 2010 and TIGER 2020, creating sliver gaps.
- **Enclaves and exclaves.** Some districts aren't simply-connected (e.g. Kentucky Bend). Polygon libraries sometimes simplify these away.

Mitigations:
- After point-in-polygon, check for unmatched points and log rate
- For edge cases, use a snap-to-nearest-polygon fallback with a distance threshold (e.g., snap if within 100m, otherwise flag)
- If accuracy matters, use the same provider's boundaries AND the same provider's point geocoder — don't mix TIGER with Google geocoder

### When to raise vs. silently accept

At the **ingestion boundary** — when data enters your system — raise on unknown identifiers. It's better to halt an ingest than to silently miscategorize donors for a month.

At the **analysis boundary** — when data is used for reporting — raise if data loss exceeds a threshold (e.g., > 1% unmatched after join). Below that, log and proceed, but include the rate in the output.

### Checklist before shipping spatial / identifier code

- [ ] Every public function documents the identifier systems it accepts
- [ ] Normalization runs at ingestion with explicit failure mode
- [ ] Join vintages are pinned (no ambiguous "current" year)
- [ ] Unmatched-row rate is logged after every join
- [ ] Boundary-edge miss rate is logged for point-in-polygon
- [ ] Tests include a "known-dirty" fixture (empty strings, ISO-3166 variants, Excel-stripped FIPS, renamed precincts)


# Addendum to analysis/spatial/reference.md — ESDA / Geographic Data Science

Append this section after the "Dirty Tabular Data" section.

Draws from **Rey, Arribas-Bel, Wolf — *Geographic Data Science with Python*** (geographicdata.science/book/intro.html) — the canonical open-access reference.

---

## Exploratory Spatial Data Analysis (ESDA)

Most spatial work is descriptive: "what's going on spatially with this variable?" Before regressions and models, run ESDA.

### Core PySAL stack

| Library | Use |
|---|---|
| `libpysal` | Spatial weights (W) construction — Queen/Rook contiguity, KNN, distance-band |
| `esda` | Global and local spatial statistics — Moran's I, LISA, Geary's C |
| `spreg` | Spatial regression — lag, error, SARAR, GWR hooks |
| `segregation` | Residential / spatial segregation indices |
| `mgwr` | Geographically Weighted Regression |
| `splot` | ESDA-specific visualizations (choropleth, LISA cluster maps) |

### Spatial weights — the foundation

Every spatial statistic requires a weights matrix `W` — who is a neighbor of whom.

```python
from libpysal import weights

# Queen contiguity (shares vertex OR edge)
w = weights.Queen.from_dataframe(gdf)
w.transform = "r"  # row-standardize

# Rook contiguity (shares edge only)
w = weights.Rook.from_dataframe(gdf)

# K-nearest neighbors (for point data or non-contiguous polygons)
w = weights.KNN.from_dataframe(gdf, k=8)

# Distance band (within X meters)
w = weights.DistanceBand.from_dataframe(gdf, threshold=5000, binary=False)
```

Rules:
- Check for islands: `w.islands` returns GEOIDs with zero neighbors. These break Moran's I.
- Row-standardize (`w.transform = "r"`) for most analyses — makes weights a weighted average.
- Cache `W` objects — they're expensive to build for large geographies.

### Moran's I — global spatial autocorrelation

```python
from esda.moran import Moran

moran = Moran(gdf["median_income"], w)
print(f"Moran's I: {moran.I:.3f} (p={moran.p_sim:.3f})")
```

Interpretation:
- `I` ≈ 1: strong positive spatial autocorrelation (similar values cluster)
- `I` ≈ 0: random spatial pattern
- `I` ≈ -1: strong negative autocorrelation (dissimilar values adjacent — rare in real data)

Always report `p_sim` (permutation-based p-value) not the analytic p-value. Spatial data violates the IID assumption.

### LISA — local indicators

```python
from esda.moran import Moran_Local

lisa = Moran_Local(gdf["median_income"], w)
gdf["lisa_q"] = lisa.q  # 1=HH, 2=LH, 3=LL, 4=HL
gdf["lisa_sig"] = lisa.p_sim < 0.05

# Classify for mapping
def lisa_category(row):
    if not row["lisa_sig"]:
        return "Not significant"
    return {1: "High-High", 2: "Low-High", 3: "Low-Low", 4: "High-Low"}[row["lisa_q"]]
gdf["lisa_cat"] = gdf.apply(lisa_category, axis=1)
```

LISA clusters are where real stories live: "this block group is a Low-Low island in a High-High region" is much more informative than a global Moran's I.

### splot — consistent LISA maps

```python
from splot.esda import lisa_cluster

fig, ax = lisa_cluster(lisa, gdf, p=0.05)
```

Use `splot` rather than rolling your own choropleth — the color scheme is the GDS book's standard and readers can interpret across analyses.

## Spatial regression (from chapter 11 of the book)

| Model | When |
|---|---|
| **OLS** | Baseline; check Moran's I of residuals. If significant, OLS is underspecified. |
| **Spatial lag** | The dependent variable spills over space (crime contagion, house prices) |
| **Spatial error** | Unobserved factors are spatially correlated (missing neighborhood fixed effects) |
| **SARAR** | Both lag and error — use when diagnostics say both |
| **GWR (mgwr)** | Coefficients themselves vary over space |

### Diagnostic workflow

```python
from spreg import OLS, ML_Lag, ML_Error

ols = OLS(y, X, w=w, name_y="income", name_x=["var1", "var2"], spat_diag=True)
print(ols.summary)  # includes LM tests for lag and error

# If LM_Lag p < 0.05 → try spatial lag
lag = ML_Lag(y, X, w=w)

# If LM_Error p < 0.05 → try spatial error
err = ML_Error(y, X, w=w)
```

### Never skip

- Plot residuals spatially — clustering is a diagnostic failure
- Report Moran's I of residuals alongside any coefficient
- If the dependent variable is count-data, don't use OLS — use a Poisson variant

## Geocoding (GDS chapter 4)

The book's recommendation aligns with this repo's `spatial/SKILL.md` Step 2:

| Volume | Accuracy | Method |
|---|---|---|
| <100 addresses | High | Census Geocoder or Google API |
| 100–10K | Medium | Batched Census Geocoder (free, US) |
| 10K–1M | Medium | Self-hosted Nominatim or Pelias |
| >1M | Approximate | ZIP / tract centroid lookup |

Python:
```python
import geopandas as gpd
from census_geocoder import geocoder  # hypothetical; check current lib

result = geocoder(addresses, returntype="locations", benchmark="Public_AR_Current")
```

## Reproducibility — the book's discipline

1. **Notebooks for exploration, modules for production.** Copy-paste from a notebook into `.py` once the analysis is stable.
2. **Pin data versions.** Store the dataset URL + a checksum alongside the notebook. Census URLs change.
3. **Every figure exports as both PNG (for docs) and PDF (for print).**
4. **Use `contextily` for basemaps** — it handles Web Mercator reprojection automatically and attributes the tile provider. Don't hand-roll basemap loading.
5. **`pyproj` has a `Transformer.from_crs` caching pattern** — use it for repeated reprojections in loops.

## Canonical references

- **Rey, Arribas-Bel, Wolf — *Geographic Data Science with Python*** (geographicdata.science/book)
- **PySAL documentation** — pysal.org
- **Luc Anselin's work (GeoDa author)** — foundational spatial econometrics literature
- **Fotheringham, Brunsdon, Charlton — *Geographically Weighted Regression*** — GWR canon

Every ESDA operation above has a worked example in one of the book chapters. Link to the relevant chapter in any analysis that uses the method.
