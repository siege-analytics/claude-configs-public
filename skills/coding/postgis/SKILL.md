---
name: postgis
description: "PostGIS patterns for spatial queries, indexing, and performance. TRIGGER: SQL with ST_* functions, geometry columns, spatial joins, or PostGIS extension setup. Stacks with sql and (when relevant) spatial sub-skills."
routed-by: coding-standards
user-invocable: false
paths: "**/*.sql,**/postgis/**,**/*.py"
---

# PostGIS

## Companion shelves and references

For storage-engine reasoning (B-tree vs GiST/BRIN indexes, partitioning at scale):
- [`shelves/systems-architecture/data-intensive/`](../../shelves/systems-architecture/data-intensive/SKILL.md)

For *Mastering PostGIS* distillation, deep dives, and the SU-PostGIS interop map:
- [`references/mastering-postgis/`](references/mastering-postgis/index.md) — book-skill-style distillation: index + chapter-themed reference files mirroring the book's structure (Ch 1 importing data, Ch 2 data types, Ch 3 vector ops, etc.) + currency caveats
- [`references/indexing-strategies.md`](references/indexing-strategies.md) — GIST / SP-GIST / BRIN — when to use each
- [`references/geometry-vs-geography.md`](references/geometry-vs-geography.md) — decision rules + SRID hygiene
- [`references/spatial-joins-performance.md`](references/spatial-joins-performance.md) — ST_DWithin / ST_Intersects / planner reads
- [`references/query-optimization.md`](references/query-optimization.md) — EXPLAIN, parallel-safe, index hints
- [`references/topology.md`](references/topology.md) — `postgis_topology` for shared-edge editing
- [`references/vacuuming-and-bloat.md`](references/vacuuming-and-bloat.md) — GIST bloat is the silent ops killer
- [`references/pitfalls.md`](references/pitfalls.md) — SRID mismatch, mixed geom types, 3D coords sneaking in
- [`references/siege-utilities-postgis.md`](references/siege-utilities-postgis.md) — which SU PostGIS helpers to use vs. raw psycopg2

Apply when writing SQL against PostgreSQL with the PostGIS extension enabled. See [reference.md](reference.md) for full query templates, extension setup, and raster operations.

Draws from:
- **Paul Ramsey's blog (blog.cleverelephant.ca)** — PostGIS co-founder; de facto canonical for modern patterns
- **Obe & Hsu — *PostGIS in Action* 3rd ed (2021)** — the authoritative book
- **Crunchy Data "Postgres for Geospatial"** (crunchydata.com/learn/postgres-geospatial)
- **García & Vergara — *pgRouting* (2022)** — for network-on-geography work

## Decision tree

```
START: I'm writing a spatial query
  │
  ├─ Is my join key trustworthy? (apply _data-trust-rules.md)
  │   ├─ YES → consider string-based join first
  │   └─ NO → geometry
  │
  ├─ What operation?
  │   ├─ Containment → ST_Contains / ST_Within / ST_Covers
  │   ├─ Intersection → ST_Intersects (uses index)
  │   ├─ Distance within X → ST_DWithin (uses index)
  │   ├─ Nearest neighbor → index-aware <-> operator + LIMIT
  │   └─ Exact distance → ST_Distance (AFTER candidate narrowing)
  │
  ├─ Is there a spatial index on the geometry column?
  │   ├─ NO → CREATE INDEX USING GIST; come back
  │   └─ YES → continue
  │
  └─ Are polygons complex (> 1000 vertices)?
      ├─ YES → ST_Subdivide to ~256 vertices per piece
      └─ NO → proceed
```

## Geometry vs geography

Pick deliberately:

| Type | Storage | Index | Units | Use for |
|---|---|---|---|---|
| `geometry` | Planar coords in a specific CRS | GiST | CRS units (degrees / meters) | 99% of cases |
| `geography` | WGS84 spheroid | GiST | Always meters | Great-circle distance, global data |

Rule: use `geometry` with a projected CRS (e.g. EPSG:5070 for the continental US) for any area/distance work. Use `geography` only when you need accurate great-circle distance over long distances without thinking about projections.

**Don't** mix: casting `geometry::geography` in a hot loop is a per-row cost.

## Always index

```sql
CREATE INDEX districts_geom_idx ON districts USING GIST (geom);

-- For partitioned tables, index each partition
CREATE INDEX ON donations_2024 USING GIST (geom);
```

Index types for spatial data:
- **GIST** — general purpose geometry/geography
- **SP-GIST** — better for point-heavy datasets and uniform distributions
- **BRIN** — when geometries are physically clustered on disk (time-ordered ingest)

Check usage:
```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT d.district_id FROM districts AS d
WHERE ST_Contains(d.geom, ST_SetSRID(ST_Point(-98, 30), 4326));
-- Look for "Bitmap Index Scan on districts_geom_idx"
```

If the plan shows `Seq Scan`, the index isn't being used (usually CRS mismatch, function on the indexed column, or the table is too small to matter).

## Operator-based queries — use the index

```sql
-- Nearest neighbor (index-aware)
SELECT name, geom <-> ST_SetSRID(ST_Point(-98, 30), 4326) AS dist
FROM places
ORDER BY geom <-> ST_SetSRID(ST_Point(-98, 30), 4326)
LIMIT 5;

-- Bounding-box intersection (index-aware)
SELECT *
FROM features
WHERE geom && ST_MakeEnvelope(-100, 30, -97, 32, 4326);
```

The `<->` operator triggers KNN with spatial index. The `&&` operator is bounding-box intersect — always used under the hood by `ST_Intersects` / `ST_Contains` for pre-filtering.

## Spatial joins — the expensive ones

For large many-to-many spatial joins:

### 1. Subdivide complex polygons (one-time prep)

Complex polygons (many vertices) are slow to test. Break them into tiles:

```sql
CREATE TABLE districts_subdivided AS
SELECT district_id, ST_Subdivide(geom, 256) AS geom
FROM districts;

CREATE INDEX ON districts_subdivided USING GIST (geom);
```

Paul Ramsey's posts have repeatedly shown 10-100x speedups on point-in-polygon against complex boundaries after `ST_Subdivide`. Do this for any Congressional-district / census-tract / precinct dataset that ships "real" polygons.

### 2. Spatial join against the subdivided table

```sql
SELECT DISTINCT d.id, d.amount, b.district_id
FROM donations AS d
INNER JOIN districts_subdivided AS b
    ON ST_Contains(b.geom, d.geom);
```

The `DISTINCT` dedupes the matches from multiple subdivided tiles of the same district.

### 3. Partition by region for horizontal parallelism

If your workload is naturally per-state (election data, etc.), partition both sides by state and process partitions concurrently:

```sql
-- One partition per state
CREATE TABLE donations_tx PARTITION OF donations
    FOR VALUES IN ('TX');
```

Then parallel jobs touch different partitions without contention.

## CRS discipline

Explicit CRS on every geometry:

```sql
-- BAD — SRID 0, no projection info
SELECT ST_Point(-98, 30);

-- GOOD — explicit
SELECT ST_SetSRID(ST_Point(-98, 30), 4326);

-- Transform when needed (for area/distance in meters)
SELECT ST_Area(ST_Transform(geom, 5070)) AS area_m2
FROM districts;
```

**Never** call `ST_Area` / `ST_Distance` / `ST_Length` on EPSG:4326 (lat/lng degrees) and expect meaningful units. Project first (EPSG:5070 for US, UTM for local, etc.).

Store in 4326 (lossless exchange), compute in a projected CRS. See the `spatial` sub-skill's CRS table for the choice by task.

## Validity

PostGIS operations crash silently (or mysteriously) on invalid geometry. Check on ingest:

```sql
UPDATE features
SET geom = ST_MakeValid(geom)
WHERE NOT ST_IsValid(geom);

-- Or at INSERT time
ALTER TABLE features ADD CONSTRAINT features_geom_valid CHECK (ST_IsValid(geom));
```

`ST_MakeValid` preserves dimensionality (polygons stay polygons). `ST_Buffer(geom, 0)` is a cheaper but lossier legacy fix — avoid unless you understand the failure modes.

## Extensions you'll actually want

| Extension | Use |
|---|---|
| `postgis` | Core — always |
| `postgis_raster` | Raster analytics (tiles, pixel operations) |
| `postgis_topology` | Shared-edge editing of polygons |
| `h3` | Hexagonal indexing (Uber's library) — great for binning at scale |
| `pgrouting` | Shortest path / isochrones on road networks |
| `pg_stat_statements` | Query performance introspection (not geo-specific but always install) |

Load order matters: `CREATE EXTENSION postgis;` before anything that depends on PostGIS types.

## Performance checklist

Before running a spatial query in production:

- [ ] Spatial index exists on every geometry column being joined/filtered
- [ ] CRS is consistent (no in-query `ST_Transform` if it can be pre-computed)
- [ ] Complex polygons are subdivided (`ST_Subdivide` or equivalent)
- [ ] EXPLAIN ANALYZE shows Bitmap Index Scan, not Seq Scan on the geo table
- [ ] Materialize intermediate results if the same spatial join runs in multiple queries
- [ ] `work_mem` is large enough for the plan's Sort/Hash steps (watch for "external merge" in EXPLAIN)

## Common mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| No spatial index | Full table scan every query | `CREATE INDEX USING GIST` |
| `ST_Distance` without candidate narrowing | Scans entire other table per row | `ST_DWithin` or `<->` + LIMIT first |
| `ST_Transform` on the indexed column | Index skipped | Transform the query constant instead |
| Storing lat/lng as separate TEXT columns | Can't index, can't query spatially | Convert to `geometry(Point, 4326)` |
| CRS 0 / unknown CRS | Joins return 0 rows | `ST_SetSRID` on ingest; check `Find_SRID()` |
| `ST_Subdivide` in the query | Prep work repeated | Subdivide once into a table |
| Mixing `geometry` and `geography` | Implicit casts per row | Pick one; cast once at boundary |
| Computing area in degrees | Meaningless numbers | Project to equal-area CRS first |
| `ST_Contains` when `ST_Intersects` is meant | Boundaries silently excluded | Know the difference; see reference.md |
| Not running `VACUUM ANALYZE` after bulk load | Planner uses stale stats | `VACUUM (ANALYZE) features;` |

## References

- **Paul Ramsey blog** — blog.cleverelephant.ca (primary modern source)
- **Obe & Hsu** — *PostGIS in Action* 3rd ed (2021)
- **Crunchy Data Geospatial Hub** — crunchydata.com/learn/postgres-geospatial
- **PostGIS docs** — postgis.net/docs/ (reference, not tutorial)
- **PostGIS workshop materials** — postgis.net/workshops/postgis-intro/

## Attribution Policy

See [`../../_output-rules.md`](../../_output-rules.md). NEVER include AI or agent attribution.
