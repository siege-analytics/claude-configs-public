# PostGIS Topology

`postgis_topology` is for **shared-edge editing of polygon networks**. Don't reach for it unless you actually have that problem.

## When you need it

You have it if:

- You're editing a polygon mesh where moving one vertex must move all adjacent edges (parcel maps, precinct maps, administrative boundaries during redistricting).
- You need to enforce that polygons share edges exactly (no slivers from independently-traced boundaries).
- You're doing topological operations (which polygons are neighbors, which polygons share an edge of length > X, etc.) and the spatial-predicate version is too slow or wrong at the floating-point level.

## When you don't need it

If you're:

- Doing point-in-polygon queries → use `geometry` and GIST.
- Computing area / distance → use `geometry` with a projected CRS.
- Building a routable network → use `pgrouting`, not topology.
- Checking polygon adjacency once per analysis run → use `ST_Touches` and accept it.

## Setup

```sql
CREATE EXTENSION postgis;
CREATE EXTENSION postgis_topology;

-- Create a topology
SELECT topology.CreateTopology('precincts_topo', 4326, 0, false);

-- Add a layer to it
SELECT topology.AddTopoGeometryColumn(
    'precincts_topo',  -- topology name
    'public',          -- schema
    'precincts',       -- table
    'topo',            -- column to add (TopoGeometry type)
    'POLYGON'          -- type
);
```

Now `precincts.topo` is a `TopoGeometry` column referencing nodes/edges/faces in the `precincts_topo` schema.

## Loading existing polygons into topology

```sql
UPDATE precincts
SET topo = topology.toTopoGeom(geom, 'precincts_topo', 1, 0.00001);
-- Args: geometry, topology name, layer ID, tolerance (in topology SRID units)
```

The tolerance matters: too small and you get sliver faces from floating-point noise; too large and adjacent polygons get merged. EPSG:4326 tolerance of `0.00001` ≈ ~1m at the equator — usually a reasonable starting point for political boundaries.

After the load:

```sql
-- Validate
SELECT * FROM topology.ValidateTopology('precincts_topo');
```

Empty result = clean topology. Non-empty rows are issues to fix before relying on edge-sharing.

## Edit operations

The whole point: move a vertex and adjacent edges follow.

```sql
-- Move node 42
SELECT topology.ST_MoveNode('precincts_topo', 42, ST_SetSRID(ST_Point(-98.001, 30.0), 4326));
```

All faces/polygons that share that node update simultaneously. You can't get this from `geometry` columns; each polygon's vertex would need a manual UPDATE and you'd accumulate floating-point drift.

## Querying topology

Adjacent faces:

```sql
-- Faces sharing an edge with face 7
SELECT DISTINCT face_id
FROM precincts_topo.relation
WHERE topogeo_id IN (
    SELECT topogeo_id FROM precincts_topo.relation WHERE face_id = 7
)
AND face_id != 7;
```

This is faster than `ST_Touches` for adjacency queries on large meshes because the topology layer pre-computes the adjacency graph.

## Dropping

```sql
SELECT topology.DropTopology('precincts_topo');
```

This drops the topology *schema* and all its layers. It does **not** drop the user tables that referenced it; they're left with orphan `TopoGeometry` columns. Drop those columns explicitly first if you want a clean removal.

## Honest assessment

`postgis_topology` is **rarely the right tool** in election / civic data work. The common alternative is to:

1. Source authoritative polygon files from one canonical provider per vintage (Census TIGER, state SOS, county GIS).
2. Treat them as immutable; never edit shared edges in-database.
3. Use `geometry` + `ST_Buffer(geom, 0)` or `ST_MakeValid` to clean any sliver issues at ingest.

Reach for topology when you're the *authority* producing the polygons, not when you're a downstream consumer. For consumer workflows, the operational cost (validating topology, managing tolerances, rebuilding after each ingest) usually exceeds the value.

## Further reading

- PostGIS docs: https://postgis.net/docs/Topology.html
- The topology section in *Mastering PostGIS* (see [`mastering-postgis-distilled.md`](mastering-postgis-distilled.md)) — book content here is largely still current; the API hasn't changed.
