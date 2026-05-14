# Ch 9 — pgRouting

The book introduces `pgRouting` — a separate extension that adds graph-on-spatial-network capabilities to PostGIS. Shortest paths, isochrones, traveling salesman, vehicle routing.

`pgRouting` has matured significantly since the book. The book's introductory treatment is still valid; the modern landscape adds parallel routing, contraction hierarchies, and integration with OSM data via `osm2pgrouting`.

## When to use pgRouting

| You need | Use |
|---|---|
| Shortest path between two points on a road network | `pgr_dijkstra` |
| Driving-distance isochrone (15-minute drive coverage) | `pgr_drivingDistance` + `ST_ConvexHull` / `pgr_alphaShape` |
| Travel time matrix (N×M routing distances) | `pgr_dijkstraCost` |
| Vehicle routing (multi-stop optimization) | `pgr_vrp*` family or third-party (OR-Tools) |
| Network topology validation | `pgr_analyzeGraph`, `pgr_nodeNetwork` |

Don't use pgRouting when:
- You don't have a road network (it's a graph algorithm, not a spatial-clustering one)
- You need real-time routing across millions of OD pairs (use specialized engines: OSRM, Valhalla, GraphHopper)
- The routing is one-shot and the data is in OpenStreetMap (`osmnx` + `networkx` in Python is faster to set up)

## Setup

```sql
CREATE EXTENSION pgrouting;  -- requires postgis already
```

Then load a road network. Most commonly from OpenStreetMap via `osm2pgrouting`:

```bash
osm2pgrouting --f input.osm.pbf --conf mapconfig.xml --dbname routing --username user --clean
```

Or build manually from a road shapefile:

```sql
CREATE TABLE roads (
    gid SERIAL PRIMARY KEY,
    geom geometry(LineString, 4326),
    speed_kmh INTEGER,
    direction TEXT  -- 'forward', 'backward', 'both'
);

-- Build routable topology (assigns source/target node IDs)
SELECT pgr_createTopology('roads', 0.00001, 'geom', 'gid');

-- After this, roads has source/target columns identifying nodes
```

## Shortest path — `pgr_dijkstra`

```sql
SELECT * FROM pgr_dijkstra(
    'SELECT gid AS id, source, target, ST_Length(geom) / NULLIF(speed_kmh, 0) AS cost FROM roads',
    1234,  -- start node
    5678,  -- end node
    directed := true
);
```

Returns a sequence of edges traversed. Combine with the original `roads` table to reconstruct the path geometry:

```sql
WITH path AS (
    SELECT * FROM pgr_dijkstra(
        'SELECT gid AS id, source, target, cost_seconds AS cost FROM roads',
        1234, 5678
    )
)
SELECT ST_LineMerge(ST_Union(r.geom)) AS path_geom, SUM(p.cost) AS total_seconds
FROM path p JOIN roads r ON p.edge = r.gid;
```

## Isochrones — `pgr_drivingDistance`

"What can you reach within X minutes from here?"

```sql
SELECT * FROM pgr_drivingDistance(
    'SELECT gid AS id, source, target, cost_seconds AS cost FROM roads',
    1234,    -- start node
    600,     -- 600 seconds (10 minutes)
    directed := true
);
```

Returns reachable nodes. To convert to a polygon:

```sql
WITH reachable AS (
    SELECT * FROM pgr_drivingDistance(
        'SELECT gid AS id, source, target, cost_seconds AS cost FROM roads',
        1234, 600
    )
)
SELECT pgr_alphaShape(array_agg(node_geom))
FROM (
    SELECT ST_StartPoint(r.geom) AS node_geom
    FROM reachable rch JOIN roads r ON rch.node = r.source
    UNION
    SELECT ST_EndPoint(r.geom) FROM reachable rch JOIN roads r ON rch.node = r.target
) AS nodes;
```

`pgr_alphaShape` produces a concave hull around reachable nodes — the isochrone polygon.

## Travel-time matrix — `pgr_dijkstraCost`

For "how long does it take from each origin to each destination":

```sql
SELECT * FROM pgr_dijkstraCost(
    'SELECT gid AS id, source, target, cost_seconds AS cost FROM roads',
    ARRAY[1234, 1235, 1236],  -- origins (node IDs)
    ARRAY[5678, 5679, 5680],  -- destinations
    directed := true
);
```

Returns an N×M cost matrix. Useful for accessibility analysis (2SFCA, gravity models — see [`../../analysis/spatial/references/spatial-statistics.md`](../../../../analysis/spatial/references/spatial-statistics.md) §9).

## Cost models

The `cost` column in the SQL passed to pgRouting determines what "shortest" means:

| Cost expression | Optimizes for |
|---|---|
| `ST_Length(geom)` | Shortest distance |
| `ST_Length(geom) / speed_kmh` | Fastest travel time |
| `ST_Length(geom) / speed_kmh + traffic_penalty` | Fastest with traffic |
| `1.0` per edge | Fewest edges (hops) |
| Custom function with elevation, weather, etc. | Multi-criteria |

The book covers basic distance and time costs. Modern routing engines (OSRM, Valhalla) handle multi-criteria better; pgRouting is best for simple cases or when the routing must integrate with PostGIS data.

## Modern alternatives

For production routing at scale, **purpose-built routing engines outperform pgRouting**:

- **OSRM** (Open Source Routing Machine) — C++; pre-builds contraction hierarchies; very fast for distance-matrix queries
- **Valhalla** — Mapbox's open-source engine; multi-modal (driving, walking, cycling, transit); JSON-RPC API
- **GraphHopper** — Java-based; strong for elevation-aware routing

When to stick with pgRouting:
- Routing is one part of a larger PostGIS pipeline (OD matrix joins to demographic data)
- Setup time matters more than query speed
- Network is small and queries are infrequent

When to switch to OSRM / Valhalla:
- Production routing service handling thousands of QPS
- Network is OSM-scale (continental)
- Need vehicle-specific routing (truck weight/height restrictions)

For Siege accessibility analysis, **`siege_utilities.geo.isochrones.OpenRouteServiceProvider`** wraps a hosted routing service (OpenRouteService / Valhalla) — usually the right answer over standing up pgRouting:

```python
from siege_utilities.geo.isochrones import get_isochrone, OpenRouteServiceProvider

p = OpenRouteServiceProvider(api_key="...")
gdf = get_isochrone(
    provider=p,
    locations=[(-98.49, 29.42)],
    range_seconds=[600, 1200, 1800],
    profile="driving-car",
)
```

See [`coding/geopandas/references/siege-utilities-geopandas.md`](../../../geopandas/references/siege-utilities-geopandas.md).

## Pitfalls

- **`pgr_createTopology` tolerance too small** — fragments edges that should connect. Too large — merges nodes that shouldn't.
- **Cost = `ST_Length` on EPSG:4326** — degrees, not meters. Project first or use `geography` length.
- **Forgot `directed := true`** for one-way streets — paths run wrong direction.
- **Network has unconnected components** — Dijkstra returns no path silently. Check with `pgr_analyzeGraph` before serving routes.
- **Using pgRouting for OSM-scale continental routing** — slow. Use OSRM / Valhalla.
- **Live traffic in cost column updated per query** — recomputes contraction hierarchies. pgRouting doesn't support live updates well; use specialized engines.
- **`pgr_alphaShape` with too-small alpha** — produces fragmented isochrone polygons.
- **Routing without a CRS-projected geometry column** — distance costs in degrees corrupt results.

## Cross-links

- [`../../analysis/spatial/references/spatial-statistics.md`](../../../../analysis/spatial/references/spatial-statistics.md) §9 — 2SFCA accessibility uses routing costs
- [`coding/geopandas/references/siege-utilities-geopandas.md`](../../../geopandas/references/siege-utilities-geopandas.md) — SU isochrone helpers (alternative path)
- [`../indexing-strategies.md`](../indexing-strategies.md) — index patterns for routing tables (source/target B-tree indexes)

## Citation

Witkowski K., Chojnacki B., Mackiewicz M. *Mastering PostGIS*. Packt Publishing, 2017. Chapter 9 ("PostGIS and pgRouting"). Paraphrase + commentary; not redistribution.

pgRouting documentation: https://docs.pgrouting.org/
