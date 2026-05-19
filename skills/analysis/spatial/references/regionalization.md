# Regionalization — Constrained Spatial Clustering

Regionalization is clustering with a **contiguity constraint**: the resulting groups must be spatially contiguous. The classic application is redistricting — building districts where every piece of every district touches another piece of the same district.

This is the single most relevant spatial-analysis topic for civic / redistricting work and was missing from our reference set. GDSPy Chapter 10 is the canonical modern treatment.

## When regionalization is the right framing

| You want… | Use |
|---|---|
| Find clusters of similar features (no contiguity required) | **DBSCAN / KMeans** — see [`spatial-statistics.md`](spatial-statistics.md) §7 |
| Group features into contiguous regions (every region's parts touch) | **Regionalization** (this file) |
| Draw electoral districts | **Regionalization** with population-equality constraint |
| Optimize service-catchment territories | **Regionalization** with per-region capacity constraint |
| Assign sales territories | **Regionalization** with travel-distance objective |

The distinction matters because non-spatial clustering (KMeans, DBSCAN) gives you groups where the high-income suburb of Houston might end up in the same cluster as a high-income suburb of Dallas. That's correct for "find similar places," wrong for "draw a contiguous region."

## Algorithms

### Max-p

The most general regionalization algorithm. Builds the **maximum number of regions** that satisfy:
- Contiguity (every region is connected)
- A floor constraint (e.g., minimum population per region)

Then optimizes feature similarity within regions.

```python
from spopt.region import MaxPHeuristic
from libpysal.weights import Queen

w = Queen.from_dataframe(gdf)
model = MaxPHeuristic(
    gdf,
    w=w,
    attrs_name=["median_income", "college_pct"],  # similarity targets
    threshold_name="population",                    # constraint variable
    threshold=50000,                                # min population per region
    top_n=2,                                        # search heuristic depth
)
model.solve()
gdf["region"] = model.labels_
```

**When to use:**
- You have a population / area / capacity floor and want to maximize region count subject to it.
- The number of regions isn't predetermined.

**Pitfall:** Heuristic — not optimal. Run multiple times with different random seeds and compare; report the best. Production-grade max-p uses MIP solvers (commercial: Gurobi, CPLEX; OSS: COIN-OR), but the heuristic is fast enough for most analysis.

### SKATER (Spatial K'luster Analysis by Tree Edge Removal)

Builds a minimum spanning tree on the spatial graph (weighted by feature dissimilarity), then prunes edges to create k contiguous regions.

```python
from spopt.region import Skater

model = Skater(
    gdf,
    w=w,
    attrs_name=["median_income", "college_pct"],
    n_clusters=20,
    floor=10000,             # optional: min population per region
    floor_variable="population",
)
model.solve()
gdf["region"] = model.labels_
```

**When to use:**
- You know how many regions you want (k pre-specified).
- You want a deterministic algorithm (no random seed to worry about).
- The data has clear similarity structure that should drive the cuts.

**Pitfall:** SKATER without a floor can produce wildly unbalanced regions (one region with 90% of the features, the rest tiny). Always set `floor` for civic work.

### AZP (Automatic Zoning Procedure)

Older algorithm; useful for benchmarking. Iteratively swaps features between regions to minimize a within-region heterogeneity objective.

```python
from spopt.region import AZP

model = AZP(
    gdf,
    w=w,
    attrs_name=["median_income"],
    n_clusters=20,
)
model.solve()
gdf["region"] = model.labels_
```

**When to use:**
- Comparison baseline against max-p / SKATER.
- Simpler reproduction of a published method.

Less commonly the production choice. Cited for completeness.

### Random region

Pure baseline — assign features to random contiguous regions. Useful for null-model comparisons.

```python
from spopt.region import RandomRegion

model = RandomRegion(area_ids=gdf["geoid"].tolist(), num_regions=20)
gdf["region_random"] = model.labels_
```

**When to use:** Computing whether a regionalization solution is meaningfully better than chance.

## Choosing the algorithm

| Constraint | Algorithm |
|---|---|
| Floor (min population per region), variable region count | **max-p** |
| Pre-specified region count, no floor | **SKATER** |
| Pre-specified region count + floor | **SKATER** with `floor` |
| Need to compare to baseline | **AZP** or **Random region** |
| Multi-objective, hard constraints | Custom MIP (out of `spopt` scope; use Gurobi / Pyomo) |

## Redistricting-specific patterns

For political redistricting, regionalization is one piece of a larger pipeline:

1. **Build the contiguity W** (block-group or precinct level, Queen contiguity).
2. **Define the constraints** — equal population (within tolerance), Voting Rights Act compliance, jurisdictional boundary respect.
3. **Define the objective** — minimize compactness violation, minimize boundary fragmentation, maximize partisan fairness, etc.
4. **Run the algorithm** — usually iterative, with constraint relaxation.
5. **Validate** — check every district for contiguity (algorithms can fail), population balance, VRA compliance.

`spopt.region.MaxPHeuristic` handles step 4 for the simpler cases. For full redistricting work, use specialized libraries:

- **`gerrychain`** (Metric Geometry and Gerrymandering Group at Tufts) — Markov-chain-based district sampling. Used in academic and litigation work. Not in spopt.
- **`maup`** — boundary-correspondence helpers for redistricting workflows.

GDSPy mentions these but doesn't go deep. For Siege civic work touching real districting, plan to use `gerrychain` for the analysis and `spopt` for warm-start / initial-region generation.

## Compactness — the geometric quality measure

A district can be contiguous but bizarrely shaped (the "salamander" in *gerrymander*). Compactness measures detect this:

| Measure | Computation | Use when |
|---|---|---|
| **Polsby-Popper** | `4π × area / perimeter²` (1.0 = perfect circle) | Standard for political districts |
| **Schwartzberg** | `perimeter / (2π × √(area / π))` (1.0 = perfect circle) | Legal scrutiny in some states |
| **Reock** | `area / area of minimum bounding circle` | Penalizes elongated shapes |
| **Convex hull** | `area / area of convex hull` | Detects bays / deep concavities |

```python
import numpy as np

def polsby_popper(geom):
    return (4 * np.pi * geom.area) / (geom.length ** 2)

gdf["pp_score"] = gdf.geometry.apply(polsby_popper)
# Closer to 1 = more compact
```

For a regionalization run, report the distribution of compactness scores across resulting regions. Outliers (scores < 0.1) are worth visual inspection — they may be artifacts of the input geography (e.g., coastline) rather than algorithmic failure.

## Per-engine implementation

| Engine | Regionalization support |
|---|---|
| **GeoPandas + spopt** | Native — all algorithms above. **Default.** |
| **PostGIS** | Manual SQL (recursive CTE for contiguity). For real work, pull data into Python and use spopt; persist results back. |
| **DuckDB-spatial** | Same as PostGIS — manual. Pull to Python. |
| **Sedona** | No native regionalization. Build the contiguity W via spatial join, collect to driver, run spopt. |

Regionalization, like W matrix construction, is **single-node Python territory** in 2026. The engines are good for the underlying spatial graph; spopt does the constrained clustering.

## Pitfalls

- **Forgetting the contiguity constraint.** KMeans on lat/lng coordinates produces "clusters" that look like districts but aren't contiguous. Use spopt, not sklearn.
- **No floor constraint** → wildly unbalanced regions. Always set `floor` for civic work.
- **Heuristic algorithm + single random seed** → suboptimal solution. Run multiple seeds, take the best (or use median for robustness).
- **Mistaking similarity-clustering for regionalization** — DBSCAN groups similar points; regionalization groups contiguous areas. Different problems.
- **Compactness alone as success criterion** — perfectly compact circles centered on populated areas might still violate VRA or split natural communities. Compactness is one constraint, not the goal.
- **Running on raw FIPS GEOIDs without re-checking adjacency** — Census TIGER ships precise contiguity, but if you've spatially joined or merged geographies, validate adjacency before building W.
- **Output regions that disappear features** — the algorithm assigns every feature to a region by default; if some are silently dropped (e.g., islands without W neighbors), check `gdf["region"].isna().sum()` before reporting results.

## Reading the output

`spopt` algorithms return:
- `model.labels_` — region assignment for each feature (array)
- `model.objective` — within-region heterogeneity objective value (lower = better, for similarity-based)
- `model.solving_time` — wall-clock seconds

The algorithm doesn't tell you whether the output is *good*. Always:

1. **Validate contiguity** per region: `for region_id in gdf["region"].unique(): assert gdf[gdf["region"] == region_id].unary_union.geom_type in ("Polygon", "MultiPolygon")` — and `.is_valid`.
2. **Compute compactness** per region (Polsby-Popper).
3. **Compute constraint satisfaction** — population per region, area per region, etc.
4. **Map it.** The visual sanity check catches more bugs than any metric.

## Cross-links

- [`spatial-weights.md`](spatial-weights.md) — W matrix construction (regionalization needs contiguity W)
- [`spatial-statistics.md`](spatial-statistics.md) §7 — DBSCAN and other non-spatial clustering (the alternative when contiguity isn't required)
- [`spatial-feature-engineering.md`](spatial-feature-engineering.md) — building the similarity attributes that drive regionalization
- [`coding/postgis/references/spatial-joins-performance.md`](../../../coding/postgis/references/spatial-joins-performance.md) — `ST_Subdivide` for fast adjacency builds

## Citation

Rey, S.J., Arribas-Bel, D., Wolf, L.J. *Geographic Data Science with Python*. CRC Press, 2023. Chapter 10 ("Clustering and Regionalization"). Online edition: https://geographicdata.science/book/notebooks/10_clustering_and_regionalization.html

`spopt` documentation: https://pysal.org/spopt/

`gerrychain` documentation: https://gerrychain.readthedocs.io/

Paraphrase + commentary; not redistribution.
