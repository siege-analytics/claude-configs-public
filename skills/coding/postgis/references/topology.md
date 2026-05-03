# PostGIS Topology

`postgis_topology` enforces shared-edge integrity across a polygon mesh. When you're **producing** polygons (especially from points), it's the right tool. When you're a downstream consumer of canonical sources, it's usually overkill.

## When you need it

You have it if:

- **You estimate boundaries from points** — Voronoi tessellation, alpha-shape concave hulls, kernel-density contours, regionalization output. The polygons are *yours*; the shared-edge structure between adjacent polygons matters and shouldn't drift as inputs change.
- You're editing a polygon mesh where moving one vertex must move all adjacent edges (parcel maps, precinct maps under revision, redistricting plans during the drawing phase).
- You need to enforce that polygons share edges exactly (no slivers from independently-traced boundaries).
- You're doing topological queries (which polygons are neighbors, which polygons share an edge of length > X) at scale where adjacency-via-`ST_Touches` is too slow.

## When you don't need it

If you're:

- Doing point-in-polygon queries against canonical boundaries (Census TIGER, state SOS) → `geometry` + GIST.
- Computing area / distance / length on canonical boundaries → `geometry` with a projected CRS.
- Building a routable network → `pgRouting`, not topology (see [`mastering-postgis/09-pgrouting.md`](mastering-postgis/09-pgrouting.md)).
- Checking polygon adjacency once per analysis run → `ST_Touches` and accept the cost.

## The point-derived boundary use case (the load-bearing one for Siege work)

When you generate polygons from points — the common Siege pattern — topology earns its complexity. Three reasons:

1. **Adjacent polygons should share edges exactly.** Naïve Voronoi from a point set produces polygons that *should* share edges, but floating-point drift can leave 0.001m slivers between neighbors. Downstream `ST_Within` joins miss points falling in the slivers; spatial joins double-count points on the shared boundary.
2. **Inputs shift as data improves.** Add 100 more donor points, the Voronoi tessellation re-computes; without topology, every adjacent boundary edge gets drawn independently, producing new sliver risk per re-computation. Topology preserves shared-edge identity across edits.
3. **Auditability.** When boundaries change, you want to know *which edges moved* and which stayed. Topology stores edges as first-class objects with identity; `geometry` columns store polygons whose boundaries are recomputed every time.

### Pattern: Voronoi-from-points with topology

```sql
CREATE EXTENSION postgis;
CREATE EXTENSION postgis_topology;

-- 1. Compute Voronoi from points
CREATE TEMPORARY TABLE voronoi_temp AS
SELECT (ST_Dump(ST_VoronoiPolygons(ST_Collect(geom)))).geom AS geom
FROM source_points;

-- 2. Set up the topology
SELECT topology.CreateTopology('precincts_topo', 4326, 0, false);

SELECT topology.AddTopoGeometryColumn(
    'precincts_topo',
    'public',
    'precincts',
    'topo',
    'POLYGON'
);

-- 3. Create the precincts table referencing the topology
CREATE TABLE precincts (
    id BIGSERIAL PRIMARY KEY,
    name TEXT,
    topo TopoGeometry
);

-- 4. Convert each Voronoi polygon to a TopoGeometry
INSERT INTO precincts (name, topo)
SELECT
    'precinct_' || row_number() OVER (),
    topology.toTopoGeom(geom, 'precincts_topo', 1, 0.00001)
FROM voronoi_temp;

-- 5. Validate
SELECT * FROM topology.ValidateTopology('precincts_topo');
-- Empty result = clean topology
```

Tolerance (`0.00001` ≈ ~1m at the equator for EPSG:4326) controls how aggressively close-but-not-identical vertices snap together. Too small → slivers persist. Too large → distinct boundary points get merged. **Tune to your data scale**; for state-scale boundaries, larger tolerance; for parcel-level work, smaller.

### Pattern: edit operations preserve shared edges

The whole point. Move a node and adjacent polygons' edges follow:

```sql
-- Move node 42 (a shared vertex between three precincts)
SELECT topology.ST_MoveNode('precincts_topo', 42, ST_SetSRID(ST_Point(-98.001, 30.0), 4326));

-- All three precincts that share node 42 now have updated boundaries — automatically
```

Without topology: you'd UPDATE three different polygons' geometry, hope you got the same coordinate in all three, and accumulate drift over edits.

### Pattern: adjacency queries

Adjacent polygons via topology are pre-computed:

```sql
-- Polygons sharing an edge with face 7
SELECT DISTINCT face_id
FROM precincts_topo.relation
WHERE topogeo_id IN (
    SELECT topogeo_id FROM precincts_topo.relation WHERE face_id = 7
)
AND face_id != 7;
```

Faster than `ST_Touches` for adjacency queries on large meshes because the adjacency graph is materialized.

## Other use cases worth knowing

### Cleaning up scanned / digitized boundary data

Old historical boundaries (digitized from paper maps) often have small overlaps and gaps. Topology can enforce a clean mesh:

```sql
SELECT topology.ValidateTopology('historical_boundaries');
-- Returns the specific edges/faces with issues; fix iteratively
```

### Boundary version control

Snapshot the topology at a point in time:

```sql
CREATE TABLE precincts_v2024 AS
SELECT name, ST_GeometryFromText(topology.AsText(topo)) AS geom_snapshot
FROM precincts;
```

You preserve the polygons as static geometry; the topology continues to evolve. Useful for "show me the precincts as they were before the 2024 redistricting."

## Setup recap

```sql
CREATE EXTENSION postgis;
CREATE EXTENSION postgis_topology;

-- Create a topology
SELECT topology.CreateTopology('my_topo', 4326, 0, false);
--                              ↑          ↑    ↑   ↑
--                         topo name     SRID  precision
--                                                 hasZ

-- Add a layer to a user table
SELECT topology.AddTopoGeometryColumn(
    'my_topo',         -- topology name
    'public',          -- schema
    'my_table',        -- table name
    'topo',            -- column name to add (TopoGeometry type)
    'POLYGON'          -- type
);
```

## Loading existing polygons into topology

```sql
UPDATE precincts
SET topo = topology.toTopoGeom(geom, 'precincts_topo', 1, 0.00001);
```

The 4th argument is the snapping tolerance. If your input polygons are already a clean mesh (shared edges identical to floating-point precision), use a tiny tolerance (`0`). If they have noise (digitization artifacts), use a tolerance proportional to the noise scale.

After loading:

```sql
SELECT * FROM topology.ValidateTopology('precincts_topo');
```

Empty result = clean. Non-empty rows are issues to fix before relying on edge-sharing.

## Dropping

```sql
SELECT topology.DropTopology('precincts_topo');
```

Drops the topology *schema* and all its layers. Does **not** drop the user tables that referenced it; they're left with orphan `TopoGeometry` columns. Drop those columns explicitly first if you want a clean removal.

## Cost — be honest

Topology adds operational complexity:

- **Tolerance tuning** is per-dataset; wrong choice = silent corruption (slivers persist or vertices merge inappropriately)
- **Validation is per-edit**; bulk operations need batch-validate-then-fix workflows
- **Storage overhead**: nodes / edges / faces tables grow with edge count; expect 2-3× the storage of a plain `geometry` column
- **No GeoPandas equivalent**: pulling topology data into Python loses the topology layer; you get plain geometries

The tradeoff is worth it when shared-edge integrity is the *requirement* (point-derived boundaries, edited meshes, audit-trail boundaries). For consumer workflows, the cost exceeds the value.

## Cross-engine note

Topology in this strict sense is a **PostGIS-specific feature.** No other engine in the spatial set has it:

| Engine | Topology equivalent |
|---|---|
| **GeoPandas** | None. Adjacent polygon edits don't preserve shared edges; you reconstruct the mesh per operation. |
| **Sedona** | None. Spatial joins use predicate-based adjacency, not topological identity. |
| **DuckDB-spatial** | None. Same as GeoPandas. |

If shared-edge integrity matters and you're working in any of these other engines, the workflow is:
1. Generate polygons in the engine
2. Push to PostGIS (`gdf.to_postgis(...)`)
3. Convert to topology (`topology.toTopoGeom`)
4. Edit / validate in PostGIS
5. Pull cleaned polygons back as needed

PostGIS becomes the topology authority; the other engines are computation layers around it.

## Pitfalls

- **Tolerance too small** → slivers persist; topology validation passes but spatial joins still miss boundary points.
- **Tolerance too large** → distinct boundary vertices merge; "two precincts" become one face silently.
- **Bulk-loading polygons without `ValidateTopology`** → corruption goes undetected; downstream operations produce subtly wrong results.
- **Editing the underlying `geometry` column directly** instead of using `topology.ST_MoveNode`/etc. → topology and geometry diverge; topology becomes lying.
- **Pulling topology data to Python** → topology is lost; only the realized geometries come over.
- **Using topology when you don't actually edit the polygons** → all the cost, none of the benefit. Just use plain `geometry` + GIST.

## Cross-links

- [`mastering-postgis/03-vector-operations.md`](mastering-postgis/03-vector-operations.md) — the alternative (plain `geometry` + ST_* operations)
- [`../../analysis/spatial/references/regionalization.md`](../../../analysis/spatial/references/regionalization.md) — regionalization output is one of the canonical "boundaries from points" workflows
- [`../../analysis/spatial/references/point-pattern-analysis.md`](../../../analysis/spatial/references/point-pattern-analysis.md) — point pattern analysis often produces the points that get tessellated into boundaries

## Further reading

- PostGIS docs: https://postgis.net/docs/Topology.html
- The topology section in *Mastering PostGIS* (see [`mastering-postgis/index.md`](mastering-postgis/index.md)) — book content here is largely still current; the API hasn't changed.
- TerragiS topology workshop materials: https://terragis.net/docs (background on tolerance tuning)
