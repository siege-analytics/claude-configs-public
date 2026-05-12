# Spatial Weights — The W Matrix

The spatial weights matrix encodes "what counts as a neighbor." Every spatial-statistics test (Moran's I, Getis-Ord, LISA, spatial regression) takes W as input. **Change W, change the answer.**

This file is the deep dive on weights — when to use which scheme, how to construct, common pitfalls. Companion to [`spatial-statistics.md`](spatial-statistics.md), which uses W in every recipe.

## The principle

W is a model of spatial relationships, not a parameter. Treat its choice as analytically as you'd treat a regression specification.

A naive implementation: pick Queen contiguity, run the analysis, report the result. The defensible implementation: state the W you chose, why it fits the spatial structure of the data, and run sensitivity analysis with at least one alternative W.

## Weight schemes

### Contiguity weights — when polygons share edges

| Scheme | "Neighbor" definition |
|---|---|
| **Queen** | Polygons share an edge OR a vertex (chess-queen moves) |
| **Rook** | Polygons share an edge only (chess-rook moves) |
| **Bishop** | Polygons share a vertex only (rare; usually combined as Queen−Rook) |

Queen is the default for most polygon work. Rook only matters when the corner-touching distinction is substantively meaningful (rare in civic / Census data).

```python
from libpysal.weights import Queen, Rook

w_queen = Queen.from_dataframe(gdf)
w_rook = Rook.from_dataframe(gdf)
```

**When contiguity is wrong:**
- Point data — no shared edges
- Polygon data with isolated features (islands; counties separated by water) — they have no neighbors under contiguity, which silently distorts every test
- Datasets where "neighbor" is functionally about distance, not adjacency (e.g., commuter flows, donor reach)

### Distance-band weights — fixed radius

```python
from libpysal.weights import DistanceBand

w_dist = DistanceBand.from_dataframe(gdf, threshold=10000)  # 10 km
```

Two features are neighbors if within `threshold` distance. Threshold units are CRS units — **project to a meter CRS first** or you get degrees.

**When to use:**
- Point data
- Polygon data where you want to capture a known spatial scale (e.g., commuting catchment, polling-place reach)
- Polygon data with islands (no shared edges; distance-band still finds near neighbors)

**Pitfall:** Picking the threshold is the analytical decision. Run the analysis at multiple thresholds; if the conclusion is unstable, the spatial scale is the question, not a parameter.

### k-Nearest Neighbors (KNN)

```python
from libpysal.weights import KNN

w_knn = KNN.from_dataframe(gdf, k=8)
```

Each feature has exactly `k` neighbors — the closest. **Adapts to density** (urban features have nearby neighbors; rural features have farther ones).

**When to use:**
- Highly skewed density (urban / rural mix)
- You want each feature to have the same neighborhood size (statistical convenience)
- Distance-band gives some features 0 neighbors (rural isolates)

**Pitfall:** k-NN is *not symmetric.* If A is one of B's k nearest, B isn't necessarily one of A's. The W matrix becomes asymmetric, which most spatial-stats software handles, but it surprises people debugging "why isn't W symmetric?"

### Kernel weights — distance-decayed

```python
from libpysal.weights import Kernel

w_kernel = Kernel.from_dataframe(gdf, function="triangular", bandwidth=10000)
```

Continuous weights based on a distance kernel. Closer neighbors weigh more; weights decay smoothly with distance.

Kernels available: `triangular`, `uniform`, `quadratic`, `quartic`, `gaussian`. Triangular is the default and usually fine.

**When to use:**
- The substantive question has a distance-decay structure (donations, gravity models)
- GWR (geographically weighted regression) — *requires* kernel weights
- Smooth interpolation surfaces

**Bandwidth choice** matters as much as kernel choice. Adaptive bandwidth (k-nearest count) for skewed density; fixed bandwidth (meters) for uniform density.

### Hybrid weights

Combine schemes when one alone doesn't fit. Common pattern: contiguity weights with a distance-band fallback for islands.

```python
from libpysal.weights import w_union, w_intersection

w_combined = w_union(w_queen, w_distance)
# A and B are neighbors if EITHER queen-contiguous OR within distance
```

## Standardization

After construction, standardize W:

```python
w.transform = "r"   # row-standardize (most common; rows sum to 1)
# or
w.transform = "b"   # binary (0/1)
# or
w.transform = "v"   # variance-stabilizing
```

**Row-standardization** is the default for spatial regression and most autocorrelation tests. The interpretation is "weighted average of neighbors." Without it, features with more neighbors dominate.

**Binary** is what Getis-Ord uses by default — it counts neighbors rather than averaging.

## Construction patterns

### From a GeoDataFrame

```python
from libpysal.weights import Queen
w = Queen.from_dataframe(gdf, ids="geoid")  # use geoid as the index
```

The `ids` parameter sets the W's labels — usually the geoid / id column. Without it, W uses the integer DataFrame index, which can drift across operations.

### From points (lat/lng)

```python
from libpysal.weights import KNN
import numpy as np

coords = np.column_stack([gdf.geometry.x, gdf.geometry.y])
w = KNN.from_array(coords, k=8)
```

For non-projected coordinates, distances are in degrees. For meaningful results, project the GeoDataFrame first (e.g., to EPSG:5070) before extracting coordinates.

### From an adjacency table (manual)

```python
from libpysal.weights import W

neighbors = {
    "TX_0001": ["TX_0002", "TX_0010"],
    "TX_0002": ["TX_0001", "TX_0003"],
    # ...
}
w = W(neighbors)
```

Useful when the adjacency comes from external data (custom-defined neighborhoods, business rules).

## Diagnostics — always check W before using it

```python
print(w.n)                     # number of features
print(w.s0)                    # sum of weights (n if binary, n if row-standardized)
print(w.histogram)             # neighbor-count distribution
print(w.islands)               # features with 0 neighbors — INVESTIGATE
print(w.percentile_share)      # connectivity percentiles
```

**If `w.islands` is non-empty:**
- Decide whether the islands should be included in the analysis.
- If yes, switch to a scheme that gives them neighbors (KNN, distance-band, hybrid).
- If no, drop them with `w.remap_ids()` and re-run.

Many spatial tests will silently NaN-out island features without warning. Check first.

## Sensitivity analysis — the discipline

Run the analysis with at least two W matrices:

```python
results = {}
for name, w in [("queen", w_queen), ("knn8", w_knn8), ("dist10km", w_dist)]:
    w.transform = "r"
    mi = Moran(gdf["turnout"], w)
    results[name] = {"I": mi.I, "p": mi.p_sim}

print(pd.DataFrame(results).T)
```

If conclusions hold across W's, you have a robust finding. If they flip, the spatial structure of the data is the question, not the test.

## The book's emphasis

GDSPy Chapter 4 makes the case that *most spatial-statistics errors trace to the W matrix*, not the test. The standard analytical move is to:

1. **State W explicitly** — "I used Queen contiguity on counties because adjacent counties share infrastructure / share a media market / etc."
2. **Validate W's structure** — no surprise islands; neighbor distribution makes substantive sense.
3. **Run sensitivity** — at least one alternative W.
4. **Report the W in any published result** — alongside the test statistic. "Moran's I = 0.42 (p < 0.001) using row-standardized Queen contiguity."

The book treats W as a first-class research object. So should we.

## Per-engine implementation

| Engine | W matrix construction |
|---|---|
| **GeoPandas + libpysal** | Native — `Queen.from_dataframe`, `KNN.from_dataframe`, `DistanceBand.from_dataframe`, `Kernel.from_dataframe`. Default. |
| **PostGIS** | Manual SQL (recursive `ST_Touches` for contiguity, `ST_DWithin` for distance-band). For large datasets, build in Python via libpysal and persist as a junction table. |
| **DuckDB-spatial** | Same as PostGIS — manual SQL. The output is a `(feature_a, feature_b, weight)` table you'd feed to whatever does the spatial-stats compute (usually pull to Python). |
| **Sedona** | No native W matrix concept. Build via spatial join on a `ST_Touches` predicate; collect to driver and convert to libpysal `W` for analysis. |

The pattern: **W matrix construction is single-node Python territory in 2026.** Engines are good for the underlying spatial join; pull the result into libpysal for the W object and the downstream stats.

## Pitfalls

- **Forgetting to project before distance-band / KNN on lat/lng** — distances in degrees are nonsense.
- **Using Queen on point data** — there are no shared edges; W has all-zero rows.
- **Using KNN on data with duplicate locations** — ties in distance produce non-deterministic neighbor selection. Deduplicate first.
- **Forgetting `transform = "r"`** before spatial regression. The model expects row-standardized; without it, coefficients are scaled wrong.
- **Building W on a filtered GeoDataFrame after the analysis was set up on the unfiltered version** — the index labels don't match. `w.remap_ids()` to rebuild.
- **Islands silently swallowed.** Always check `w.islands` length.
- **Asymmetric W (KNN) producing test results that aren't reproducible across software** — KNN W is fine; just be aware some R packages assume symmetric W and your Python results may not match.
- **Using GIST-indexed `ST_Touches` in PostGIS for very large W construction** — can be slow. For >1M features, consider H3-indexing first and building W from H3 cell adjacency.

## Cross-links

- [`spatial-statistics.md`](spatial-statistics.md) — every test that uses W
- [`regionalization.md`](regionalization.md) — uses W as a contiguity constraint
- [`spatial-feature-engineering.md`](spatial-feature-engineering.md) — neighbor-mean features built from W
- [`crs-decision-tree.md`](crs-decision-tree.md) — projection before distance-based W

## Citation

Rey, S.J., Arribas-Bel, D., Wolf, L.J. *Geographic Data Science with Python*. CRC Press, 2023. Chapter 4 ("Spatial Weights"). Online edition: https://geographicdata.science/book/notebooks/04_spatial_weights.html

Paraphrase + commentary; not redistribution.
