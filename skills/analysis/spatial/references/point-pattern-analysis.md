# Point Pattern Analysis

When the data is a set of point locations and the question is **about the pattern of the points themselves** — are they clustered, random, or dispersed? — point pattern analysis is the right toolset.

GDSPy Chapter 8 reverses my earlier "out of scope" call. For donor-cluster questions, polling-place placement, event-location work, and surveillance-of-rare-events, the methods below are concise and load-bearing.

## When point pattern analysis is the right framing

| Question | Use |
|---|---|
| "Are donations clustered geographically (vs uniformly distributed)?" | **Ripley's K, Complete Spatial Randomness test** |
| "Where are the high-density areas, smoothly?" | **Kernel density estimation (KDE)** |
| "Find clusters of points (group them)" | **DBSCAN** (see [`spatial-statistics.md`](spatial-statistics.md) §7) |
| "Are these two point patterns related (co-occurring)?" | **Cross-K function, bivariate Ripley's K** |
| "Is this point near other points more than chance?" | **Nearest-neighbor distance distribution** |

The distinction from clustering algorithms (DBSCAN): clustering *groups* the points; point pattern analysis *characterizes the overall pattern* and tests against null hypotheses.

## Ripley's K function

The canonical point-pattern test. For each point, count how many other points are within distance `r`. Average across all points. Compare to what you'd expect under Complete Spatial Randomness (CSR — points placed independently and uniformly).

```python
from pointpats import PointPattern, k_test

# Create the pattern from a (n, 2) array of coordinates (in projected meters)
coords = gdf[["x", "y"]].values
pp = PointPattern(coords)

# Run K test
k_result = k_test(pp, support=20)  # 20 distance bands
print(k_result)
```

**Interpretation:**
- If observed K > expected K at distance r → points are **clustered** at scale r
- If observed K < expected K → points are **dispersed** (regular spacing) at scale r
- If observed K ≈ expected K → consistent with CSR

The output is a function — clustering at small distances, randomness at large distances is the most common pattern (donations cluster within a city; cities are roughly random).

### Visualizing K

```python
import matplotlib.pyplot as plt

plt.plot(k_result.support, k_result.statistic, label="Observed K")
plt.plot(k_result.support, k_result.simulations.mean(axis=0), label="Expected K (CSR)")
plt.fill_between(
    k_result.support,
    k_result.simulations.min(axis=0),
    k_result.simulations.max(axis=0),
    alpha=0.2, label="CSR envelope (99%)",
)
plt.xlabel("Distance")
plt.ylabel("K(r)")
plt.legend()
```

The envelope is the 99% range of K under simulated CSR. Observed K outside the envelope = significant deviation from random.

## L function — variance-stabilized K

K grows quadratically with distance, which makes the plot hard to read. The L function transforms K to be linear under CSR:

```python
from pointpats import l_test

l_result = l_test(pp, support=20)
plt.plot(l_result.support, l_result.statistic - l_result.support, label="L(r) - r")
# Under CSR, L(r) - r ≈ 0
# Above zero = clustered; below zero = dispersed
```

L is the more common version for inspection.

## Nearest-neighbor distance — the F, G, J functions

| Function | What it measures |
|---|---|
| **G(r)** | Distribution of nearest-neighbor distances (point-to-point) |
| **F(r)** | Distribution of empty-space distances (random-location-to-point) |
| **J(r)** | (1 - G) / (1 - F) — combines both; J=1 under CSR |

```python
from pointpats import g_test, f_test, j_test

g_result = g_test(pp, support=20)
```

G is more common than F; J is a useful diagnostic but rarely the primary test.

## Kernel density estimation (KDE)

Smooth density surface from point locations:

```python
from sklearn.neighbors import KernelDensity
import numpy as np

coords = gdf[["x", "y"]].values
kde = KernelDensity(kernel="gaussian", bandwidth=1000).fit(coords)  # 1km bandwidth

# Evaluate on a grid
x_grid = np.linspace(coords[:, 0].min(), coords[:, 0].max(), 200)
y_grid = np.linspace(coords[:, 1].min(), coords[:, 1].max(), 200)
xx, yy = np.meshgrid(x_grid, y_grid)
log_density = kde.score_samples(np.c_[xx.ravel(), yy.ravel()])
density = np.exp(log_density).reshape(xx.shape)

import matplotlib.pyplot as plt
plt.imshow(density, extent=[x_grid.min(), x_grid.max(), y_grid.min(), y_grid.max()],
           origin="lower", cmap="viridis")
```

Or use `scipy.stats.gaussian_kde` for a quick alternative.

**Bandwidth choice** dominates everything else. Too small → lumpy noise. Too large → blurred to uselessness. Common defaults:
- **Silverman's rule** — automatic, conservative
- **Scott's rule** — automatic, moderate
- **Cross-validation** — optimal but expensive

Try several bandwidths; the right one looks "right" visually for the substantive question.

## Cross-K — relating two point patterns

When you have two point types and want to know if they cluster *together*:

```python
# Are donor locations near polling places?
from pointpats import cross_k_test

donors = PointPattern(donors_coords)
polls = PointPattern(polls_coords)

ck_result = cross_k_test(donors, polls, support=20)
```

If observed cross-K > expected → the two patterns are spatially associated (donors cluster near polls). Useful for accessibility studies, geographic-impact analysis.

## Spatial point process models (advanced)

When you want to **model** the point pattern as a generative process:

- **Homogeneous Poisson process** — CSR; the null model
- **Inhomogeneous Poisson process** — intensity varies with covariates (population density, road network)
- **Cluster process (Neyman-Scott, Matern)** — points cluster around unobserved parents
- **Hardcore process** — points avoid each other (regular spacing; e.g., trees in a managed forest)

For Siege civic work, fitting these is rare — the testing tools (Ripley's K, KDE) are usually sufficient. For deep modeling, R's `spatstat` package is the canonical tool; Python equivalents are limited.

## Bandwidth and edge effects

### Bandwidth selection (KDE)

Run with multiple bandwidths and inspect:

```python
import matplotlib.pyplot as plt

fig, axes = plt.subplots(1, 4, figsize=(16, 4))
for ax, bw in zip(axes, [200, 1000, 5000, 20000]):
    kde = KernelDensity(bandwidth=bw).fit(coords)
    log_density = kde.score_samples(np.c_[xx.ravel(), yy.ravel()])
    ax.imshow(np.exp(log_density).reshape(xx.shape), origin="lower")
    ax.set_title(f"bw = {bw}m")
```

Pick the smallest bandwidth that still looks coherent (not noisy).

### Edge correction (Ripley's K)

Points near the boundary have fewer neighbors than they "should" — leading to underestimated K at short distances. Edge corrections:

- **Ripley's edge correction** — weights neighbors by the proportion of their search annulus that lies inside the study area
- **Border method** — exclude points within distance r of the edge
- **Toroidal** — treat the study area as a torus (rare in real geography)

```python
k_result = k_test(pp, support=20, method="ripley")
```

For tightly-bounded study areas (a single county), edge correction matters substantially. For very large areas (continental US), it matters less.

## Per-engine implementation

| Engine | Point pattern support |
|---|---|
| **GeoPandas + pointpats** | Native — Ripley's K, L, G, F, J, KDE. **Default.** |
| **PostGIS** | Manual SQL for K (recursive `ST_DWithin` aggregation). KDE via grid + density join. Plausible for large datasets. |
| **DuckDB-spatial** | Same as PostGIS — manual SQL with `ST_DWithin`. KDE one-shot. |
| **Sedona** | Distributed K function via spatial join + aggregate. KDE via grid join. Good for billions of points. |

For the K-function family, the **distance computation is the bottleneck**, and engines do it well. **Significance testing via simulation is single-node Python** (run 99 simulated CSR patterns; pull statistics back to compare). Hybrid: PostGIS / Sedona compute observed K; Python runs the simulation envelope.

## Pitfalls

- **Forgot to project** — running K on lat/lng gives K in degrees. Project to meters first.
- **No edge correction in a small study area** — K underestimates at small r; clustering looks weaker than it is.
- **Wrong null model** — CSR assumes uniform intensity. If your study area has population-density structure, an inhomogeneous Poisson null is more appropriate.
- **Bandwidth too small (KDE)** — produces noise that looks like structure.
- **Treating individual high-density blobs as significant** — KDE is descriptive; it doesn't test significance. Combine with K function or scan statistics for inference.
- **Comparing observed K to "expected" without simulating** — `pointpats` simulates by default; if you compute K manually, run 99+ CSR realizations for the envelope.
- **Point thinning to fit memory** — random thinning preserves CSR but distorts cluster patterns. Use the full data or stratified subsamples, not random.

## Use cases for civic / Census work

| Question | Method |
|---|---|
| "Are donations spatially clustered?" | Ripley's K with CSR null |
| "Where are donor hot spots?" | KDE with appropriate bandwidth |
| "Are polling places well-distributed across population?" | Cross-K (polls vs population centroids) |
| "Are reported violations clustered around specific buildings?" | K + LISA on a regular grid |
| "Where to place new clinics?" | KDE of underserved population + accessibility analysis |

## Cross-links

- [`spatial-statistics.md`](spatial-statistics.md) §7 — DBSCAN clustering (the "group the points" alternative to point pattern analysis's "characterize the pattern")
- [`spatial-statistics.md`](spatial-statistics.md) §1–§3 — Moran's I / Gi* on aggregated point counts (the polygon-aggregated alternative)
- [`spatial-weights.md`](spatial-weights.md) — distance-band weights are conceptually similar to K function bands

## Citation

Rey, S.J., Arribas-Bel, D., Wolf, L.J. *Geographic Data Science with Python*. CRC Press, 2023. Chapter 8 ("Point Pattern Analysis"). Online edition: https://geographicdata.science/book/notebooks/08_point_pattern_analysis.html

PySAL `pointpats` package: https://pysal.org/pointpats/

For deep modeling: Baddeley, A., Rubak, E., Turner, R. *Spatial Point Patterns: Methodology and Applications with R*. Chapman and Hall/CRC, 2015. (R-focused but the methodology transfers.)

Paraphrase + commentary; not redistribution.
