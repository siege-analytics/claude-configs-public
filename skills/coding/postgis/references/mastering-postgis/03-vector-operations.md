# Ch 3 — Working with Vector Data

The book's vector chapter is the operational core: `ST_*` functions, spatial joins, geometry processing. Most of the practical SQL work in PostGIS lives here.

The depth lives in the topic-specific reference files in this directory; this chapter file is the principle-level synthesis. See [`../spatial-joins-performance.md`](../spatial-joins-performance.md) for the canonical join recipes.

## The principle

Vector spatial operations decompose into three classes:

1. **Predicates** (yes/no questions about geometric relationships) — `ST_Within`, `ST_Intersects`, `ST_Contains`, `ST_Touches`, `ST_Crosses`, `ST_Overlaps`, `ST_DWithin`. **Fast** when paired with spatial indexes.
2. **Measurements** (numeric outputs) — `ST_Distance`, `ST_Area`, `ST_Length`, `ST_Perimeter`. **CRS-sensitive** (degrees vs meters).
3. **Constructions** (new geometry from input geometries) — `ST_Buffer`, `ST_Centroid`, `ST_Envelope`, `ST_Intersection`, `ST_Difference`, `ST_Union`. **Expensive at scale** (each new geometry is computed).

The book's worked examples cycle through all three, with predicates dominating spatial-join work and measurements / constructions appearing in analysis pipelines.

## Predicates — index-aware vs not

The book emphasizes: **predicates that internally call `&&` (bounding-box intersect) use the GIST index; those that don't, scan.**

Index-using predicates:
- `ST_Within(a, b)`, `ST_Contains(a, b)` — both use `&&` for pre-filter
- `ST_Intersects(a, b)` — uses `&&`
- `ST_Covers(a, b)`, `ST_CoveredBy(a, b)` — use `&&`
- `ST_DWithin(a, b, distance)` — uses `&&` with bounding-box expansion
- `&&` operator directly — pure bounding-box check, fastest

Predicates *not* using the index:
- `ST_Distance(a, b) < d` — scans every row pair (anti-pattern; use `ST_DWithin`)
- `ST_Equals(a, b)` — exact equality, no `&&` shortcut
- Custom predicates inside SQL functions — opaque to the optimizer

If you find yourself writing `WHERE ST_Distance(a.geom, b.geom) < 1000`, replace with `WHERE ST_DWithin(a.geom, b.geom, 1000)`.

## Measurements — units depend on CRS

```sql
-- Wrong: degrees² — meaningless
SELECT ST_Area(geom) FROM districts WHERE state = 'TX';

-- Right: project first
SELECT ST_Area(ST_Transform(geom, 5070)) AS area_m2 FROM districts WHERE state = 'TX';
```

The book hammers this point. See [`../geometry-vs-geography.md`](../geometry-vs-geography.md) and [`../pitfalls.md`](../pitfalls.md).

For high-volume measurement work, materialize a projected geometry column:

```sql
ALTER TABLE districts ADD COLUMN geom_5070 geometry(MultiPolygon, 5070);
UPDATE districts SET geom_5070 = ST_Transform(geom, 5070);
CREATE INDEX districts_geom_5070_idx ON districts USING GIST (geom_5070);
```

Pay storage cost once; query speed forever.

## Constructions — expensive but cacheable

`ST_Buffer`, `ST_Intersection`, `ST_Union`, etc. produce new geometry. Each call computes; results aren't cached unless you cache them.

Patterns:

### Materialize buffers

If you'll repeat "within 5km of facility" many times:

```sql
CREATE TABLE facility_buffers AS
SELECT id, name, ST_Buffer(geom::geography, 5000)::geometry AS buffer_geom
FROM facilities;

CREATE INDEX ON facility_buffers USING GIST (buffer_geom);

-- Subsequent queries
SELECT * FROM features f
JOIN facility_buffers fb ON ST_Intersects(f.geom, fb.buffer_geom);
```

### `ST_Subdivide` for join performance

The canonical optimization. See [`../spatial-joins-performance.md`](../spatial-joins-performance.md).

### `ST_Union` for visualization-only aggregations

```sql
SELECT state, ST_Union(geom) AS geom FROM counties GROUP BY state;
```

This combines all counties of each state into a single state polygon. Useful for choropleth visualization at the state level. **Slow on large datasets** — for 50 states with 3,000 counties, takes seconds. For 10,000 features per group, minutes.

For aggregation-only output (you don't need the geometry as a real polygon), `ST_Envelope_Agg` is much faster.

## Geometry validity — book's core discipline

Invalid geometries break operations silently. The book's prescription:

```sql
-- Check on ingest
SELECT id FROM features WHERE NOT ST_IsValid(geom);

-- Repair
UPDATE features SET geom = ST_MakeValid(geom) WHERE NOT ST_IsValid(geom);

-- Constrain at table level
ALTER TABLE features ADD CONSTRAINT features_geom_valid CHECK (ST_IsValid(geom));
```

`ST_MakeValid` preserves dimensionality (polygons stay polygons, lines stay lines). The legacy `ST_Buffer(geom, 0)` trick is cheaper but lossier — avoid unless you understand what it discards.

For batch repair on bulk loads, run once after ingest and add the constraint to keep the table clean going forward. See [`../pitfalls.md`](../pitfalls.md) for the full validity-debugging discussion.

## Vector overlay — set operations

The book covers `ST_Intersection`, `ST_Difference`, `ST_Union`, `ST_SymDifference`. In civic work, the most common pattern is `ST_Intersection` for clipping:

```sql
-- Clip features to a bounding region
SELECT f.id, ST_Intersection(f.geom, ST_GeomFromText('POLYGON(...)', 4326)) AS clipped
FROM features f
WHERE ST_Intersects(f.geom, ST_GeomFromText('POLYGON(...)', 4326));
```

The `WHERE ST_Intersects` pre-filter is critical — `ST_Intersection` itself doesn't use the index. Pre-filter, then intersect.

For polygon overlay analyses (areal interpolation: redistribute population from old to new boundaries based on area overlap), this is the building block. SU's `interpolate_areal()` wraps this; see [`../siege-utilities-postgis.md`](../siege-utilities-postgis.md).

## Linear referencing

For LineString geometries (roads, rivers, transit lines), PostGIS supports linear referencing:

```sql
-- Where along the line is this point?
SELECT ST_LineLocatePoint(line_geom, point_geom) FROM features;
-- Returns 0.0 (start) to 1.0 (end)

-- What's the point at 25% along the line?
SELECT ST_LineInterpolatePoint(line_geom, 0.25) FROM features;

-- Substring: extract part of the line between two fractions
SELECT ST_LineSubstring(line_geom, 0.25, 0.75) FROM features;
```

Useful for road-network analyses (mile-marker locations, segment extractions). Pairs with pgRouting for full network analysis (see [`09-pgrouting.md`](09-pgrouting.md)).

## Aggregations on geometry

Post-book additions worth knowing:

- `ST_Collect(geom)` — aggregate geometries into a `GeometryCollection` (no merging; just packaging)
- `ST_Union_Agg(geom)` — true topological union (merges overlapping)
- `ST_Envelope_Agg(geom)` — bounding box of all input geometries (very fast)
- `ST_Intersection_Agg(geom)` — common area of all input geometries

`ST_Envelope_Agg` is the right choice when you just need a bounding extent. `ST_Union_Agg` is the right choice when you need the merged shape but slow at scale. `ST_Collect` is rarely what you want unless you specifically need a `GeometryCollection`.

## Cross-engine equivalents

Where the book's vector operations apply across engines:

| PostGIS | GeoPandas | Sedona | DuckDB-spatial |
|---|---|---|---|
| `ST_Within(a, b)` | `gpd.sjoin(predicate="within")` | `sedona.sql("ST_Within")` | `duckdb.sql("ST_Within")` |
| `ST_Distance(a, b)` | `gdf.geometry.distance(other)` | `ST_Distance` | `ST_Distance` |
| `ST_Buffer(geom, d)` | `gdf.geometry.buffer(d)` | `ST_Buffer` | `ST_Buffer` |
| `ST_Intersection(a, b)` | `gpd.overlay(how="intersection")` | `ST_Intersection` | `ST_Intersection` |
| `ST_MakeValid(geom)` | `shapely.validation.make_valid` | `ST_MakeValid` | `ST_MakeValid` |
| `ST_Subdivide(geom, n)` | manual recursive split | `ST_Subdivide` | `ST_Subdivide` |
| `ST_Transform(geom, srid)` | `gdf.to_crs(srid)` | `ST_Transform` | `ST_Transform` |

The function names are mostly identical because Sedona and DuckDB-spatial both follow OGC SFA naming conventions. GeoPandas wraps Shapely (which doesn't follow OGC naming consistently). The principles transfer; the call syntax adjusts.

## Cross-links

- [`../spatial-joins-performance.md`](../spatial-joins-performance.md) — the canonical performance reference for the predicates above
- [`../geometry-vs-geography.md`](../geometry-vs-geography.md) — measurement units by CRS
- [`../pitfalls.md`](../pitfalls.md) — validity, SRID mismatch, predicate confusion
- [`../indexing-strategies.md`](../indexing-strategies.md) — when GIST helps and when it doesn't
- [`../../analysis/spatial/references/spatial-weights.md`](../../../../analysis/spatial/references/spatial-weights.md) — vector predicates as the basis for W matrix construction

## Citation

Witkowski K., Chojnacki B., Mackiewicz M. *Mastering PostGIS*. Packt Publishing, 2017. Chapter 3 ("Working with Vector Data"). Paraphrase + commentary; not redistribution.
