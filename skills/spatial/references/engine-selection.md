> **Scope:** Siege Utilities calls, imports, proposed upstream work, and SU-specific workflows below are historical examples only for the exact `github.com/siege-analytics/siege_utilities` origin. In other repositories, use only verified dependencies and local project instructions; none of these examples is a global prerequisite.

# Spatial Engine Selection

Given a spatial task, pick the engine. Three axes: **data scale**, **GDAL availability**, **workload pattern**.

## The matrix

| Workload | < 1 GB | 1–10 GB | 10–100 GB | > 100 GB |
|---|---|---|---|---|
| One-off / exploration | GeoPandas | GeoPandas or DuckDB | DuckDB | Sedona |
| Repeated batch | DuckDB or PostGIS | DuckDB or PostGIS | DuckDB or Sedona | Sedona |
| Multi-user serving | PostGIS | PostGIS | PostGIS (partitioned) | PostGIS (partitioned) or Sedona for batch + PostGIS for serve |
| In a Spark pipeline already | n/a | n/a | Sedona | Sedona |

Then overlay GDAL availability:

| | GDAL available | No GDAL |
|---|---|---|
| Single-node | GeoPandas / DuckDB | DuckDB (only) |
| Server (PostGIS) | PostGIS | PostGIS (Postgres has GDAL via postgis_raster) |
| Distributed (Sedona) | Sedona | Sedona (JVM-side) |

DuckDB-spatial is the universal answer for "GDAL not available, single-node" -- it bundles its own.

## Decision tree

```
START: I have a spatial task.
  │
  ├─ Apply _data-trust-rules.md first.
  │  Is the tabular path going to silently lie? (Usually yes for civic/Census/FEC.)
  │      → if yes, you NEED geometry. Continue.
  │      → if no, consider a string lookup before any spatial engine.
  │
  ├─ Verify installed engines and declared dependencies on this host.
  │      GDAL/GeoPandas? PostGIS? DuckDB spatial? Spark/Sedona?
  │      In the exact Siege Utilities repo only, SU's geo_capabilities()
  │      is an optional project-specific capability check.
  │
  ├─ Data scale?
  │      < 1 GB → single-node options
  │      1–100 GB → single-node with care, OR distributed if cluster available
  │      > 100 GB → distributed (Sedona) or partitioned PostGIS
  │
  ├─ Workload pattern?
  │      One-off exploration → faster-startup tool wins
  │      Repeated batch → operational SQL or scheduled Spark
  │      Multi-user serving → persistent Postgres
  │
  ├─ Specific signals → engine
  │   ├─ Spark already in the picture → Sedona
  │   ├─ Persistent multi-user → PostGIS
  │   ├─ Parquet on disk + want SQL + no server → DuckDB-spatial
  │   ├─ Pandas idiom + in-memory → GeoPandas
  │   └─ No GDAL + minimal env → DuckDB-spatial
  │
  └─ Only for exact github.com/siege-analytics/siege_utilities:
      → consult siege-utilities-spatial.md for existing helpers.
      → other repositories use their verified dependency policy.
```

## When to use multiple engines together

| Combination | Use case |
|---|---|
| **PostGIS (storage) + GeoPandas (analysis)** | Authoritative data lives in Postgres; pull a working set into GeoPandas for ad-hoc analysis. |
| **PostGIS (storage) + DuckDB (export pipeline)** | Server-side authoritative data, but build derived GeoParquet for downstream consumers via DuckDB. |
| **Sedona (batch processing) + PostGIS (serving)** | Sedona produces enriched derived datasets; load into PostGIS for low-latency serving. |
| **DuckDB (one-shot conversion) + GeoPandas (analysis)** | Use DuckDB's `ST_Read` to ingest a shapefile in a GDAL-less env; convert to GeoParquet; analyze in GeoPandas. |

Don't combine for fun -- each engine adds operational surface. Combine only when one tool's strength compensates for another's weakness.

## Anti-patterns

- **Sedona on a single-node Spark cluster.** All the overhead, none of the distribution. Use DuckDB or GeoPandas instead.
- **GeoPandas on a 50 GB GeoJSON.** GeoJSON parser will OOM long before GeoPandas does. Convert to GeoParquet via DuckDB first.
- **PostGIS for one-shot exploratory analysis.** Standing up Postgres just to count points-in-polygons once is inefficient -- DuckDB does the same in 30 seconds with no server.
- **DuckDB for multi-user serving.** It's single-process. Use PostGIS.
- **GeoPandas with `to_file('out.shp')` in a GDAL-less env.** Use `to_parquet` (no GDAL).

## Quick rules of thumb

- "I have a Parquet, need SQL, no server" → **DuckDB-spatial**
- "I have a Parquet, want Pandas idiom" → **GeoPandas** (or DuckDB if larger than RAM)
- "Multiple users querying a database" → **PostGIS**
- "Already on Spark" → **Sedona**
- "GDAL not available" → **DuckDB-spatial** (bundles it) or pre-convert to GeoParquet on a GDAL machine
- In the exact Siege Utilities repository, existing SU helpers may apply (see [`siege-utilities-spatial.md`](siege-utilities-spatial.md)); never infer this dependency for another host/repo.
