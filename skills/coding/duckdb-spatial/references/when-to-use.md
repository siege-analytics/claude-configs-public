# When to Use DuckDB-Spatial

Decision criteria vs the alternatives.

## Vs PostGIS

| | DuckDB-spatial | PostGIS |
|---|---|---|
| Setup | `pip install duckdb` + `LOAD spatial` | Postgres server + `CREATE EXTENSION` |
| Persistence | optional file-backed; default in-memory | always persistent |
| Multi-user | single-process only | multi-user, ACID |
| Large queries | spills to disk; up to ~100 GB practical | scales to TB with partitioning |
| GDAL needed in environment | **no** (bundled) | no (server-side) |
| Network round-trip cost | none (in-process) | per-query overhead |
| Indexes | R-tree, ad hoc | GIST/SP-GIST/BRIN, persistent |

**Use DuckDB-spatial when:**
- You're processing data once or rarely; standing up Postgres is overhead.
- You're in a Lambda / cloud function / CI job where in-process is the only option.
- The query is exploratory and you want SQL semantics without infrastructure.

**Use PostGIS when:**
- Multiple users / services need concurrent access.
- Data is the primary operational record (not derived).
- You need persistent indexes and the planner statistics that come from a long-running database.

## Vs GeoPandas

| | DuckDB-spatial | GeoPandas |
|---|---|---|
| Idiom | SQL | Pandas |
| Memory model | spills to disk | in-memory only |
| Larger-than-RAM | yes (with spilling) | no |
| Spatial join performance | very fast for batch | competitive for moderate sizes |
| GDAL needed | **no** | yes for many file formats |
| Output | DataFrame (Pandas), GeoParquet, etc. | GeoDataFrame |

**Use DuckDB-spatial when:**
- You want SQL semantics and joins with non-spatial tables.
- Data is on disk in Parquet/CSV; you don't want to load it all into memory.
- You're in a GDAL-less environment and need to read shapefiles/GPKG.

**Use GeoPandas when:**
- You want Pandas-style chaining and method calls.
- You're doing heavy attribute-side feature engineering.
- The full dataset fits comfortably in RAM.
- You're producing maps / plots (GeoPandas + matplotlib is the stronger viz path).

## Vs Sedona on Spark

| | DuckDB-spatial | Sedona |
|---|---|---|
| Compute model | single-node, in-process | distributed across cluster |
| Setup cost | one pip install | Spark cluster + JARs + tuning |
| Cold start | < 1 s | seconds to minutes (driver + executors) |
| Optimal data size | 1 GB to ~100 GB | 10 GB to TB+ |
| Cost | free, runs on a laptop | cluster compute (Databricks DBUs, etc.) |

**Use DuckDB-spatial when:**
- Data fits on a single beefy machine (32-64 GB RAM, fast SSD).
- You're prototyping; Spark startup overhead exceeds query time.
- You want to run the same code on a laptop and on a server with no scaffolding changes.

**Use Sedona when:**
- Data is genuinely > 100 GB, or queries don't fit one node's RAM × disk-spill margin.
- You're already in a Spark pipeline and adding spatial is one of many transformations.
- You need cross-machine distribution for raw compute power.

## Cost-of-tool decision tree

```
Spatial query, single-node, < 100 GB?
  ├─ GDAL available + Pandas idiom preferred?
  │     └─ GeoPandas
  ├─ GDAL not available (Lambda, minimal image, etc.)?
  │     └─ DuckDB-spatial (bundles GDAL/GEOS/PROJ)
  ├─ SQL idiom + Parquet input + want indexes-on-demand?
  │     └─ DuckDB-spatial
  ├─ Need persistence + multi-user?
  │     └─ PostGIS
Spatial query, distributed, > 100 GB or in Spark pipeline?
  └─ Sedona
```

## A useful side-by-side

The same task — count donations per county — in each tool:

**GeoPandas:**
```python
import geopandas as gpd
points = gpd.read_parquet("donations.parquet")
counties = gpd.read_parquet("counties.parquet")
joined = gpd.sjoin(points, counties, predicate="within")
result = joined.groupby("county_geoid").size().rename("n").reset_index()
```

**DuckDB-spatial:**
```python
import duckdb
con = duckdb.connect()
con.load_extension("spatial")
result = con.execute("""
    SELECT c.county_geoid, COUNT(*) AS n
    FROM read_parquet('donations.parquet') p
    JOIN read_parquet('counties.parquet') c ON ST_Within(p.geom, c.geom)
    GROUP BY c.county_geoid
""").df()
```

**PostGIS (after the data is loaded):**
```sql
SELECT c.county_geoid, COUNT(*) AS n
FROM donations p
JOIN counties c ON ST_Within(p.geom, c.geom)
GROUP BY c.county_geoid;
```

**Sedona:**
```python
result = sedona.sql("""
    SELECT c.county_geoid, COUNT(*) AS n
    FROM points p
    JOIN counties c ON ST_Within(p.geom, c.geom)
    GROUP BY c.county_geoid
""")
```

The tool choice is about *infrastructure context*, not query expressivity. All four have ~equivalent SQL/API ergonomics; pick by what's already in the environment.

## The GDAL-availability axis

This is where DuckDB-spatial wins decisively in modern cloud / minimal-image environments:

- AWS Lambda: no GDAL. DuckDB-spatial works via pip install.
- Google Cloud Functions: same.
- Slim Docker images (e.g., `python:3.12-slim`): no GDAL system packages. DuckDB-spatial works.
- Minimal Databricks runtimes: GDAL availability varies. DuckDB-spatial works on the driver.

If your environment "should have GDAL but you can't be sure," default to DuckDB-spatial for spatial work and skip the configuration roulette.
