# Spatial Statistics

When the analysis goes beyond joins and measurements into inference, clustering, smoothing, or diagnostic work. Civic / Census / FEC / redistricting data is exactly where these methods earn their keep — the patterns you're looking for usually aren't obvious from a map alone.

This file is method-first; per-engine implementation matrix at the bottom.

## Decision matrix — pick the method

| You want to know… | Method | Strongest engine |
|---|---|---|
| "Is this variable spatially clustered overall?" | **Moran's I** (global autocorrelation) | GeoPandas + `esda` |
| "Where are the hot spots?" | **Getis-Ord Gi*** (hot-spot detection) | GeoPandas + `esda`; PostGIS SQL |
| "Where are clusters of high-near-high (or low-near-low)? Where are outliers?" | **LISA / Local Moran's I** (local autocorrelation, cluster types) | GeoPandas + `esda` |
| "Does X predict Y when controlling for spatial neighbors?" | **Spatial regression** (SAR / SEM / SLX) | GeoPandas + `pysal.spreg` |
| "Does the relationship between X and Y vary across space?" | **GWR** (geographically weighted regression) | GeoPandas + `mgwr` |
| "Are these rates real or just noise from small-area instability?" | **Empirical Bayes / spatial smoothing** | GeoPandas + `esda.smoothing`; PostGIS SQL |
| "Where do donations cluster geographically?" (point-pattern) | **DBSCAN / OPTICS** | sklearn / GeoPandas |
| "How far does this trend extend before it fades?" | **Spatial autocorrelation by distance band** (correlogram) | `esda.Moran` over distance bands |
| "How segregated is this population?" | **Dissimilarity / isolation / entropy indices** | GeoPandas + custom; PostGIS SQL |
| "How accessible is X from population Y?" | **2-step floating catchment area (2SFCA)** | GeoPandas + isochrones; PostGIS + pgRouting |
| "If I sum points to coarser polygons, do my conclusions change?" | **MAUP sensitivity testing** | All engines (re-run analysis at multiple scales) |
| "Where should I prioritize intervention?" | **Suitability analysis / weighted overlay** | GeoPandas + raster math; PostGIS |
| "Did the spatial pattern change between two periods?" | **Diff-in-diff with spatial weights** | GeoPandas + `pysal.spreg` |

## Use cases — depth

### 1. Global spatial autocorrelation — Moran's I

**When:** You want a single answer to "is this variable spatially clustered?" Useful as a first-pass diagnostic before deciding whether to use a spatial regression.

**Method:** Computes the correlation between a value and the spatial-lag of itself (the average of neighbors). Values:
- ~0 with high p_sim → spatially random (use OLS, not spatial regression)
- Significantly positive → clustered (similar values cluster)
- Significantly negative → dispersed (checkerboard pattern; rare in real data)

**Recipe (GeoPandas + esda):**

```python
import geopandas as gpd
from libpysal.weights import Queen
from esda.moran import Moran

gdf = gpd.read_parquet("counties_with_turnout.parquet")
w = Queen.from_dataframe(gdf)  # adjacency: counties sharing edges
mi = Moran(gdf["turnout"], w)
print(f"Moran's I: {mi.I:.3f}, p_sim: {mi.p_sim:.3f}")
```

**Methodological choices:**

- **Weights matrix:** Queen (shared edge or vertex), Rook (shared edge only), distance-band, k-nearest. Queen is the default for irregular polygons; k-nearest is typical for points.
- **Standardization:** Always row-standardize (`w.transform = "r"`) for interpretability — neighbors sum to 1 per row.
- **Inference:** Use Monte Carlo `p_sim` (default `permutations=999`), not analytical p-values. The latter assume normality.

**Pitfalls:**
- Sensitive to the weights matrix. Run with two W's (Queen + 4-NN, e.g.) and report both.
- Global → can mask interesting local patterns. Always run LISA after.

### 2. Hotspot analysis — Getis-Ord Gi*

**When:** You need to identify *where* the high (or low) values cluster, not just whether clustering exists. The output is per-feature, mappable.

**Method:** For each feature, computes a Z-score reflecting whether it (and its neighbors) have higher / lower values than the global mean. The * version includes the focal feature in its own neighborhood.

**Recipe (GeoPandas + esda):**

```python
from esda.getisord import G_Local

g_local = G_Local(gdf["turnout"], w, star=True)  # star=True for Gi*
gdf["gi_z"] = g_local.Zs
gdf["gi_p"] = g_local.p_sim
gdf["hotspot"] = (gdf["gi_z"] > 1.96) & (gdf["gi_p"] < 0.05)
gdf["coldspot"] = (gdf["gi_z"] < -1.96) & (gdf["gi_p"] < 0.05)
```

Then map:

```python
gdf["status"] = "neither"
gdf.loc[gdf["hotspot"], "status"] = "hotspot"
gdf.loc[gdf["coldspot"], "status"] = "coldspot"
gdf.plot(column="status", categorical=True, legend=True, figsize=(10, 6))
```

**Methodological choices:**

- **Distance band vs adjacency:** For point data or coarse polygons, distance-band weights (`libpysal.weights.DistanceBand`) often produce more interpretable hotspots than adjacency. The band width *is* the spatial scale of the analysis — pick deliberately.
- **Fixed vs adaptive bandwidth:** Fixed band = same distance for everyone; adaptive = same number of neighbors. Use adaptive when density varies dramatically (urban vs rural counties).
- **Significance threshold:** 95% (z > 1.96) is conventional; 99% (z > 2.58) for stricter hotspot maps. Always report both `z` and `p_sim`.
- **Multiple-testing correction:** Pseudo-p values from Monte Carlo aren't FDR-corrected. For maps with thousands of features, apply Bonferroni or FDR (`statsmodels.stats.multitest.multipletests`) to avoid spurious hotspots.

**Pitfalls:**
- "Hotspot" is sensitive to the spatial scale. The same data at block-group vs county levels can show different hotspots — see MAUP below.
- Rate denominators matter: a "hot spot of donations" might just be a hot spot of population. Normalize before testing.
- Edge effects: features at dataset boundaries have fewer neighbors; their Gi* is less reliable. Buffer with neighboring jurisdictions when possible.

**Recipe (PostGIS — manual Gi* via SQL):**

```sql
WITH neighbors AS (
    SELECT
        a.id,
        a.value AS value_i,
        AVG(b.value) AS mean_neighbor,
        COUNT(b.id) AS n_neighbors,
        STDDEV(b.value) AS sd_neighbor
    FROM features a
    JOIN features b ON ST_DWithin(a.geom, b.geom, 5000)  -- 5km band
    GROUP BY a.id, a.value
),
global_stats AS (
    SELECT AVG(value) AS mean_g, STDDEV(value) AS sd_g, COUNT(*) AS n
    FROM features
)
SELECT
    n.id,
    (n.mean_neighbor - g.mean_g) /
    (g.sd_g * SQRT((n.n_neighbors * (g.n - n.n_neighbors)) /
                   (g.n - 1.0) / n.n_neighbors)) AS gi_z
FROM neighbors n CROSS JOIN global_stats g;
```

(Approximate — for production use the GeoSiLK or `pgxn`-installed `pysal-pg` extensions if available, or pull data into pysal for the actual Gi* computation.)

### 3. LISA — local clusters and outliers

**When:** You want to distinguish *types* of local patterns: high values surrounded by high (HH), low surrounded by low (LL), high surrounded by low (HL — outlier), low surrounded by high (LH — outlier).

**Method:** Local Moran's I. Each feature gets a quadrant assignment (HH/LL/HL/LH) and a significance test.

**Recipe:**

```python
from esda.moran import Moran_Local

mi_local = Moran_Local(gdf["turnout"], w)
gdf["lisa_q"] = mi_local.q  # 1=HH, 2=LH, 3=LL, 4=HL
gdf["lisa_p"] = mi_local.p_sim
gdf["lisa_sig"] = gdf["lisa_p"] < 0.05

# Map: only show significant
gdf["lisa_label"] = "ns"
gdf.loc[(gdf["lisa_q"] == 1) & gdf["lisa_sig"], "lisa_label"] = "HH"
gdf.loc[(gdf["lisa_q"] == 3) & gdf["lisa_sig"], "lisa_label"] = "LL"
gdf.loc[(gdf["lisa_q"] == 2) & gdf["lisa_sig"], "lisa_label"] = "LH (outlier)"
gdf.loc[(gdf["lisa_q"] == 4) & gdf["lisa_sig"], "lisa_label"] = "HL (outlier)"
```

**When LISA beats Gi*:**
- You care about outliers (HL, LH), not just hot/cold spots.
- The narrative is "this place behaves like an island in a sea of opposites" — the literal frame for HL/LH.

**When Gi* beats LISA:**
- You only need hot vs cold (continuous Z-score interpretation).
- Audience expects a hot-spot map, not a four-color cluster map.

### 4. Rate smoothing / empirical Bayes — fixing small-area instability

**When:** You're mapping rates (per-capita turnout, per-capita donations) and small areas have wild swings because the *denominator* is small. A precinct with 50 voters and 5 anomalous donations has a per-capita rate that's not real signal.

**Method:** Empirical Bayes shrinks raw rates toward a mean (global mean, or local-neighborhood mean). The amount of shrinkage depends on the variance — small areas get shrunk more.

**Recipe:**

```python
from esda.smoothing import Empirical_Bayes_Rate_Smoother

# Smooth rate = donations / population, where small areas get pulled toward the global rate
smoother = Empirical_Bayes_Rate_Smoother(
    gdf["donations"].values,
    gdf["population"].values,
)
gdf["smoothed_rate"] = smoother.r
```

For *spatial* smoothing (pull toward neighborhood mean):

```python
from esda.smoothing import Spatial_Empirical_Bayes

ses = Spatial_Empirical_Bayes(
    gdf["donations"].values,
    gdf["population"].values,
    w,  # weights matrix
)
gdf["smoothed_rate_spatial"] = ses.r
```

**When to use:**
- Mapping rates for any small geography (block group, precinct).
- Detecting "true" hot spots that aren't artifacts of small denominators.

**When NOT to use:**
- Very small numerators (<5 events per area) — smoothing isn't enough; use a spatial model with covariates.
- Extreme heterogeneity where neighborhood mean is meaningless.

### 5. Spatial regression — when neighbors predict the outcome

**When:** Your independent variables don't fully explain Y, and Moran's I on the residuals is significant. That's the diagnostic that you need a spatial model.

**Methods:**
- **SAR (Spatial Autoregressive Lag, `spreg.GM_Lag`):** Y depends on the spatial lag of Y. Captures contagion / diffusion.
- **SEM (Spatial Error, `spreg.GM_Error`):** Errors are spatially correlated; the spatial structure is a nuisance, not a substantive effect.
- **SLX (Spatially Lagged X):** Y depends on the spatial lag of X (neighbors' covariates). Often a good first model.

**Recipe (SAR):**

```python
from spreg import GM_Lag

y = gdf["turnout"].values.reshape(-1, 1)
X = gdf[["median_income", "college_pct"]].values
w.transform = "r"

model = GM_Lag(y, X, w=w, name_y="turnout", name_x=["income", "college"])
print(model.summary)
# Look at: rho (spatial AR coefficient), p-values
```

If `rho` is significant, OLS would have given biased / inefficient estimates. SAR is the right model.

**Methodological choices:**
- Pick weights matrix deliberately (same care as for Moran's I).
- Test SAR vs SEM via Lagrange Multiplier tests (`spreg.utils.MoranR`).
- For panel data, use `spreg.Panel_FE_Lag`.

### 6. GWR — when relationships vary across space

**When:** You suspect the coefficient on a variable changes by location (e.g., income predicts turnout differently in urban vs rural counties).

**Method:** Fits a separate regression at each location with a spatial kernel weighting.

**Recipe (mgwr):**

```python
from mgwr.gwr import GWR
from mgwr.sel_bw import Sel_BW

coords = list(zip(gdf.centroid.x, gdf.centroid.y))
y = gdf[["turnout"]].values
X = gdf[["median_income", "college_pct"]].values

# Find optimal bandwidth (adaptive, AICc criterion)
selector = Sel_BW(coords, y, X, kernel="bisquare", fixed=False)
bw = selector.search(criterion="AICc")

gwr_model = GWR(coords, y, X, bw, kernel="bisquare", fixed=False).fit()
gdf["coef_income"] = gwr_model.params[:, 1]  # local coefficient on income
gdf["coef_college"] = gwr_model.params[:, 2]
```

Then map the local coefficients to see where each variable matters more.

**Methodological choices:**
- Adaptive bandwidth (k-nearest) for irregular density; fixed for uniform.
- Bisquare or Gaussian kernel — both common.
- Multi-Scale GWR (MGWR) lets each variable have its own bandwidth — more accurate but slower.

**Pitfalls:**
- Computationally expensive (O(n²) per fit).
- Local coefficients can flip sign in low-data regions — interpret with confidence intervals, not point estimates.

### 7. Cluster detection on points — DBSCAN / OPTICS

**When:** You have point data (donor addresses, event locations) and want to find spatial clusters without polygon boundaries.

**Recipe:**

```python
from sklearn.cluster import DBSCAN
import numpy as np

coords_rad = np.radians(gdf[["lat", "lng"]].values)
# eps in radians: 1km on Earth ≈ 1/6371 ≈ 0.000157 rad
clusterer = DBSCAN(eps=0.000785, min_samples=10, metric="haversine")
gdf["cluster"] = clusterer.fit_predict(coords_rad)
# cluster == -1 means noise (not in any cluster)
```

For projected meter coordinates, use Euclidean and `eps` in meters.

**OPTICS** is similar but doesn't require a fixed eps — it builds a reachability ordering you can threshold afterward. Useful when cluster scales vary.

**Tradeoffs:**
- DBSCAN scales linearly with n; great for millions of points.
- HDBSCAN handles varying densities better but is slower.
- For *contiguous polygon* clustering (regionalization, redistricting), use `pysal.region.spenc` or graph-based methods, not DBSCAN.

### 8. Segregation indices — measuring spatial separation of groups

**When:** Civic / demographic work where the question is "how separated are populations?" Standard for redistricting analysis, education access, housing studies.

**Indices:**
- **Dissimilarity (D):** "What fraction of group A would have to move to achieve even distribution?" Range 0 (perfect mix) to 1 (full segregation).
- **Isolation (xPx):** "Average exposure of group A to itself." High = isolated.
- **Spatial Dissimilarity:** D adjusted for spatial proximity (penalizes adjacent same-group areas more than distant ones).
- **Entropy / Theil's H:** Information-theoretic; works for >2 groups.

**Recipe (segregation library):**

```python
from segregation.singlegroup import Dissim, Isolation
from segregation.multigroup import MultiInfoTheil

d = Dissim(gdf, "group_a", "total")
print(f"Dissimilarity: {d.statistic:.3f}")

iso = Isolation(gdf, "group_a", "total")
print(f"Isolation: {iso.statistic:.3f}")

# Multi-group entropy
h = MultiInfoTheil(gdf, ["group_a", "group_b", "group_c"])
print(f"Theil's H: {h.statistic:.3f}")
```

The `segregation` package (formerly `pysal.segregation`) is comprehensive — 30+ indices.

### 9. Accessibility — 2-step floating catchment area (2SFCA)

**When:** "How accessible is a service to a population?" — clinics, polling places, schools. The classic question for civic / health geography.

**Method:**
1. For each service location, compute the population within travel time T. The service "load."
2. For each population location, sum the (service capacity / load) for all services within travel time T. The accessibility score.

**Recipe:** Combine SU's isochrone helpers with manual aggregation:

```python
from siege_utilities.geo.isochrones import get_isochrone, OpenRouteServiceProvider

provider = OpenRouteServiceProvider(api_key="...")

# Step 1: catchment for each service
catchments = []
for _, service in services.iterrows():
    iso = get_isochrone(provider, [(service.lng, service.lat)],
                       range_seconds=[1800], profile="driving-car")
    pop_in_catchment = pop_polygons.sjoin(iso, predicate="within")["population"].sum()
    catchments.append({"service_id": service.id, "load": pop_in_catchment})

services["load"] = pd.DataFrame(catchments).set_index("service_id")["load"]
services["service_to_load"] = services["capacity"] / services["load"]

# Step 2: accessibility for each population area
# (Repeat the isochrone calculation from population centroids, sum services["service_to_load"] within)
```

### 10. MAUP sensitivity testing

**When:** Always, before publishing any spatial-pattern claim. The Modifiable Areal Unit Problem is the *most-cited and least-respected* gotcha in spatial analysis.

**Method:** Re-run the analysis at multiple aggregation levels and check whether the conclusion holds.

**Recipe:**

```python
results = {}
for level in ["block_group", "tract", "county"]:
    gdf_level = gdf.dissolve(by=level, aggfunc={"value": "sum"})
    w_level = Queen.from_dataframe(gdf_level)
    mi = Moran(gdf_level["value"], w_level)
    results[level] = {"moran_I": mi.I, "p_sim": mi.p_sim}

print(pd.DataFrame(results).T)
```

If Moran's I is positive at all levels, the claim holds. If it flips, you have a MAUP problem and should report results at multiple scales rather than picking one.

### 11. Spatial sampling — stratified / balanced

**When:** Drawing a sample for survey or audit purposes. Naive random sampling under-represents low-density areas; stratified or spatially-balanced sampling fixes this.

**Stratified by jurisdiction:**

```python
def stratified_sample(gdf, n_per_stratum, strata_col):
    return gdf.groupby(strata_col, group_keys=False).apply(
        lambda g: g.sample(n=min(n_per_stratum, len(g)), random_state=42)
    )

sample = stratified_sample(gdf, n_per_stratum=10, strata_col="state")
```

**Spatially balanced (GRTS — generalized random tessellation stratified):**

Use the `spsurvey` R package (via `rpy2`) — Python-native equivalents are limited. The output is a sample where points are spread across the spatial extent rather than clustered.

## Per-engine implementation matrix

Engines and what they can natively do.

| Method | PostGIS | GeoPandas + pysal | Sedona | DuckDB-spatial |
|---|---|---|---|---|
| Moran's I | manual SQL | **`esda.Moran`** | manual + collect to driver | manual SQL |
| Local Moran (LISA) | manual SQL | **`esda.Moran_Local`** | manual | manual |
| Getis-Ord Gi* | manual SQL (recipe above) | **`esda.G_Local`** | manual | manual SQL |
| Spatial regression (SAR/SEM) | n/a | **`spreg`** | n/a | n/a |
| GWR | n/a | **`mgwr`** | n/a | n/a |
| Empirical Bayes smoothing | manual SQL | **`esda.smoothing`** | manual | manual |
| DBSCAN on points | manual (PL/pgSQL) | **`sklearn.cluster.DBSCAN`** | mllib K-means; no DBSCAN native | manual |
| Segregation indices | manual SQL | **`segregation` package** | manual | manual SQL |
| 2SFCA accessibility | **pgRouting + window functions** | GeoPandas + isochrones | manual | manual |
| Spatial weights matrix | manual SQL or use `pysal.lib.weights` directly | **`libpysal.weights`** | not directly | manual |
| MAUP sensitivity | re-aggregate via SQL | re-aggregate via dissolve | re-aggregate via Sedona | re-aggregate via SQL |

**The pattern:** Spatial statistics in 2026 is **single-node Python territory.** The four engines are best for *data prep / aggregation*; pull the prepared data into a GeoDataFrame and use `pysal` / `mgwr` / `segregation` for the inference.

Exceptions:
- PostGIS can handle simple Gi* / Moran-style aggregations via SQL when the data is already there and you want to avoid the round-trip. Worth doing for very large spatial datasets where pulling to Python is expensive.
- pgRouting + 2SFCA in PostGIS is cleaner than the GeoPandas equivalent for road-network accessibility analysis.

## Pitfalls

### Modifiable Areal Unit Problem (MAUP)

Same data → different conclusions at different aggregation scales. The classic example: poverty rates show different spatial patterns at block-group vs tract vs county levels, and choosing one is choosing the conclusion.

**Mitigation:** Always run sensitivity (above). Document the unit choice and why. Refuse strong conclusions that flip at different scales.

### Ecological fallacy

Cross-area correlations don't imply individual-level relationships. "Counties with more X also have more Y" doesn't mean "individuals with more X have more Y."

**Mitigation:** Be explicit about the unit of analysis in any claim. Multi-level models (`statsmodels.GEE`, R `lme4`) when individual-level data is available.

### Edge effects

Boundary features have fewer neighbors. Their statistics (Moran, Gi*, LISA) are less stable.

**Mitigation:** Buffer with neighboring jurisdictions' data when possible. Report sensitivity to edge-handling choice. For continental US, edge effects matter only at the borders; for state-level analysis where the state is the boundary, they can dominate.

### Sample size for inference

Most spatial statistics need ~30+ areas for stable inference. Pseudo p-values (`p_sim`) handle small samples better than analytical p-values, but neither rescues a 10-area dataset.

**Mitigation:** Don't run Moran's I on 5 counties. Aggregate to the smallest scale that gives ≥30 areas, or use individual-level models if you have them.

### Computational cost

Spatial weights matrices are O(n²) memory. For n=100K (block-group level), the W matrix would be ~80 GB.

**Mitigation:** Sparse representations are default in `pysal` (`libpysal.weights.W` stores sparse). For very large datasets, tile by region and analyze tiles independently.

### Multiple-testing correction

Mapping ~3000 counties' Gi* Z-scores at α=0.05 expects ~150 false positives by chance. The "hot spot map" is half noise.

**Mitigation:** Apply Bonferroni or FDR correction (`statsmodels.stats.multitest.multipletests`) before presenting maps to non-statistician audiences.

### Spatial autocorrelation ≠ causation

Moran's I tells you values cluster — not why. Hot spots may be artifacts of underlying spatial structure (cities cluster), not the phenomenon you're studying.

**Mitigation:** Always normalize the variable (per-capita, per-area) before testing. Use spatial regression with covariates, not just unconditional clustering.

## Companion references (deeper coverage)

- [`spatial-weights.md`](spatial-weights.md) — the W matrix in depth (kernel / KNN / distance-band / hybrid; standardization; sensitivity)
- [`regionalization.md`](regionalization.md) — constrained spatial clustering (max-p, SKATER, AZP); redistricting
- [`spatial-inequality.md`](spatial-inequality.md) — Gini, Theil, decomposition into between- and within-region inequality
- [`spatial-feature-engineering.md`](spatial-feature-engineering.md) — features for spatial ML, plus spatial cross-validation (the non-negotiable)
- [`point-pattern-analysis.md`](point-pattern-analysis.md) — Ripley's K, KDE, CSR tests for point data
- [`geographic-data-science-distilled.md`](geographic-data-science-distilled.md) — the GDSPy book's chapter map and how it threads through these refs

## Reference

- `pysal` ecosystem docs: https://pysal.org
- `mgwr`: https://github.com/pysal/mgwr
- `segregation`: https://github.com/pysal/segregation
- `pointpats`: https://pysal.org/pointpats/
- `spopt`: https://pysal.org/spopt/
- `inequality`: https://pysal.org/inequality/
- *Geographic Data Science with Python* (Rey, Arribas-Bel, Wolf, 2023) — https://geographicdata.science/book/intro.html (free online; the canonical modern textbook)
- *Geographic Information Analysis* (O'Sullivan & Unwin, 3rd ed.) — textbook for the principles
- *Spatial Regression Models* (Ward & Gleditsch) — deep regression treatment
- ESRI's online documentation has good methodological intros (concepts are universal even though their implementations are proprietary)

## Out of scope for this skill

- Geostatistics / kriging: out of typical Siege civic-data scope; reach for `pykrige` or R's `gstat` if needed
- Network analysis on spatial graphs: see [`postgis`](../../../coding/postgis/SKILL.md) (`pgrouting`) or future `analysis/graph/` sub-skill
