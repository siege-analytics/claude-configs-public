# Principle: Subdivide Complex Polygons

Complex polygons (Census tracts with thousands of vertices, congressional districts with snaky shapes, real-world precinct boundaries) are slow to test against. The exact-predicate cost grows linearly with vertex count, and the bbox pre-filter doesn't help much because the bbox of a complex polygon is the same as a simpler polygon covering similar area.

The fix: **split each complex polygon into pieces with bounded vertex count, once. Query the subdivided pieces forever.** Standard 10-100× speedup on point-in-polygon against real-world boundary data.

## The principle

A point-in-polygon test on a 5,000-vertex Census tract walks 5,000 vertices. If you have 100K points × 3,000 tracts, that's 1.5 billion vertex checks. Slow.

Subdivide each tract into ~20 pieces of ~256 vertices each. Now: 100K points × 60K subdivided pieces, but each piece is a 256-vertex check. The bbox pre-filter eliminates ~99% of pieces per point. Net result: ~100K × 5 candidate pieces × 256 vertices = ~128M vertex checks. **10× speedup.**

For points-in-state-boundary against unsimplified state polygons (which can be 50,000+ vertices because of coastlines), the speedup is more like 100×.

## Per-engine implementation

### PostGIS

```sql
CREATE TABLE districts_subdivided AS
SELECT
    district_id,
    state,
    (ST_Subdivide(geom, 256)).geom AS geom
FROM districts;

CREATE INDEX ON districts_subdivided USING GIST (geom);
ANALYZE districts_subdivided;
```

`ST_Subdivide(geom, max_vertices)` returns multiple rows per input row (one per subdivision piece). Each piece keeps the original `district_id`. Tested with `ST_Contains` / `ST_Within`, the result needs `DISTINCT` because a point can match multiple subdivision pieces of the same district:

```sql
SELECT DISTINCT p.id, b.district_id
FROM points p
INNER JOIN districts_subdivided b ON ST_Contains(b.geom, p.geom);
```

### Sedona

Same `ST_Subdivide` call:

```python
districts_sub = sedona.sql("""
    SELECT district_id, state, ST_Subdivide(geom, 256) AS geom FROM districts
""")
districts_sub.cache()

result = sedona.sql("""
    SELECT DISTINCT p.id, b.district_id
    FROM points p JOIN districts_sub b ON ST_Contains(b.geom, p.geom)
""")
```

### DuckDB-spatial

Same again:

```sql
CREATE TABLE districts_subdivided AS
SELECT district_id, state, ST_Subdivide(geom, 256) AS geom FROM districts;

CREATE INDEX districts_sub_geom_idx ON districts_subdivided USING RTREE (geom);
```

### GeoPandas (manual, no native ST_Subdivide)

Shapely doesn't have a built-in subdivision function. Manual recursive split:

```python
from shapely.geometry import Polygon
from shapely.ops import split

def subdivide_polygon(geom, max_vertices=256):
    """Recursively split a polygon by alternating x/y midplane until each piece has <= max_vertices."""
    if len(geom.exterior.coords) <= max_vertices:
        return [geom]
    minx, miny, maxx, maxy = geom.bounds
    midx = (minx + maxx) / 2
    midy = (miny + maxy) / 2
    width, height = maxx - minx, maxy - miny
    # Split along the longer dimension
    if width >= height:
        splitter = LineString([(midx, miny), (midx, maxy)])
    else:
        splitter = LineString([(minx, midy), (maxx, midy)])
    pieces = list(split(geom, splitter).geoms)
    return [sub for piece in pieces for sub in subdivide_polygon(piece, max_vertices)]

# Apply to a GeoDataFrame
sub_records = []
for _, row in districts.iterrows():
    for piece in subdivide_polygon(row.geometry, 256):
        sub_records.append({**row.to_dict(), "geometry": piece})

districts_sub = gpd.GeoDataFrame(sub_records, crs=districts.crs)
```

For repeated work, prefer round-tripping through PostGIS or DuckDB (which have native `ST_Subdivide`) rather than maintaining custom Python.

## When subdivision matters

The subdivide payoff scales with two factors:

1. **Vertex count of the original polygons.** Tracts (~500 vertices) marginal benefit. Counties (~2,000) noticeable. States with coastlines (~50,000) huge.
2. **Selectivity of the spatial join.** A point-in-polygon join where each point matches one polygon: full benefit. A many-to-many overlay: less because the exact predicate is unavoidable.

**Heuristic:** if your spatial join is slow and the right-side polygons average > 1,000 vertices, try subdivision. Measure before and after.

## When subdivision doesn't help

- Right-side polygons are simple (< ~500 vertices) — `ST_Subdivide` overhead exceeds the benefit
- Workload is many-to-many overlay (`ST_Intersection`, not predicate) — exact intersection is the cost; subdivision doesn't reduce it
- Right-side is small (< 100 polygons) — sequential scan is faster anyway
- Right-side changes per query — pre-processing has no payoff

## Choosing `max_vertices`

`256` is the conventional default and usually right. Tradeoffs:

- **Smaller (128, 64):** more subdivision pieces; finer-grained pre-filter; more rows in result; more index pressure. Faster point-in-polygon, slower other operations.
- **Larger (512, 1024):** fewer pieces; coarser pre-filter. Faster index updates / inserts; slower exact predicate per piece.

For point-in-polygon (the dominant Siege use case), 128–256 is the sweet spot. For polygon-polygon overlay, 256–512 reduces the row-count multiplication of the result.

## Subdivision and DISTINCT

A point that falls inside a polygon will match multiple subdivision pieces of that polygon (along the cut lines, the point is in adjacent pieces). The naive query produces duplicate rows.

**Always `DISTINCT` (or aggregate) on the original polygon ID:**

```sql
-- Wrong: 1 point may produce 2-4 rows
SELECT p.id, b.district_id FROM points p JOIN districts_subdivided b ON ST_Contains(b.geom, p.geom);

-- Right: deduplicate
SELECT DISTINCT p.id, b.district_id FROM points p JOIN districts_subdivided b ON ST_Contains(b.geom, p.geom);
```

Forgetting `DISTINCT` is the single most-common bug with subdivision.

## Subdivision is one-time prep

The expensive operation is the `ST_Subdivide` call itself (linear in vertex count). Run it once during ETL, not per query. Materialize as a separate table:

```sql
-- Pipeline step (run once when source data updates)
TRUNCATE districts_subdivided;
INSERT INTO districts_subdivided
SELECT district_id, state, (ST_Subdivide(geom, 256)).geom FROM districts;

-- Production queries hit districts_subdivided, not districts
```

For sources that update infrequently (Census TIGER ships every 10 years), this is a one-time cost. For sources that update per query (live editing), subdivision isn't worth it; query the unsubdivided table.

## Cross-engine portability

The pattern is universal but the function name varies:

| Engine | Function | Notes |
|---|---|---|
| PostGIS | `ST_Subdivide(geom, max_vertices)` | Returns set; use as `(ST_Subdivide(...)).geom` |
| Sedona | `ST_Subdivide(geom, max_vertices)` | Same syntax |
| DuckDB-spatial | `ST_Subdivide(geom, max_vertices)` | Same syntax |
| Shapely | none — manual recursive split | See recipe above |

When porting code that uses subdivision across engines, the pattern transfers; only the Python (Shapely) case requires custom code.

## Pitfalls

- **Forgot `DISTINCT`** — duplicate rows from points falling on subdivision boundaries.
- **Subdivision in the WHERE clause** — recomputes per query.
- **`max_vertices` too small** — billions of tiny pieces; index update cost dominates.
- **Subdividing simple polygons** — overhead with no benefit.
- **Subdividing without an index on the result** — defeats the purpose.
- **Subdividing then forgetting `ANALYZE`** — planner uses default row-count estimates; bad plans.
- **Subdivision in GeoPandas via Shapely** — slow; round-trip through PostGIS/DuckDB if you can.

## Cross-links

- [`bbox-pre-filter.md`](bbox-pre-filter.md) — subdivision makes the bbox pre-filter much more selective
- [`spatial-indexing-discipline.md`](spatial-indexing-discipline.md) — the subdivided table needs its own spatial index
- [`../../coding/postgis/references/spatial-joins-performance.md`](../../../coding/postgis/references/spatial-joins-performance.md) — Paul Ramsey's worked PostGIS examples
- [`../../coding/sedona/references/partitioning-strategies.md`](../../../coding/sedona/references/partitioning-strategies.md) — for Sedona, subdivision pairs with partitioning
