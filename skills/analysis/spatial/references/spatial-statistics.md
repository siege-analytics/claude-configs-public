# Spatial Statistics

When the analysis goes beyond joins and measurements into inference. Brief survey of what's worth knowing and which engine handles each.

## When this matters

You're doing hypothesis testing, cluster detection, or spatial regression — not just "which polygon contains this point." Common signals:

- "Are donations spatially clustered?" → Moran's I
- "Where are the hot spots?" → Getis-Ord Gi*
- "Does income predict turnout when controlling for spatial neighbors?" → spatial regression (SAR / SEM / GWR)
- "Which precincts behave like neighbors but differently from the rest?" → LISA cluster maps
- "How do I sample fairly across geographic strata?" → spatial sampling

## Tools and engines

| Concern | Tool | Why |
|---|---|---|
| Spatial autocorrelation (global) — Moran's I | `pysal` (esda) | Canonical Python lib |
| Spatial autocorrelation (local) — LISA | `pysal` (esda) | Local Indicators of Spatial Association |
| Hot-spot / cold-spot detection — Getis-Ord Gi* | `pysal` (esda) | Standard implementation |
| Spatial regression — SAR / SEM | `pysal` (spreg) or R `spatialreg` | spreg works in pure Python |
| Geographically Weighted Regression (GWR) | `mgwr` (Python) or R `GWmodel` | Local-coefficient regression |
| DBSCAN spatial clustering | `sklearn.cluster.DBSCAN` with `metric='haversine'` | General-purpose; works on lat/lng directly |
| K-means on geographic features | `sklearn.cluster.KMeans` | Standard ML; project to meters first |
| Spatial sampling (stratified by geometry) | `geopandas` + custom logic | No turnkey lib |

`pysal` is the spatial statistics ecosystem. Sub-packages: `esda` (descriptive), `spreg` (regression), `mgwr` (GWR), `splot` (visualization), `tobler` (areal interpolation).

## Engine support

| Operation | PostGIS | GeoPandas | Sedona | DuckDB |
|---|---|---|---|---|
| Compute spatial weights matrix | manual SQL | `pysal` (libpysal) | manual | manual |
| Moran's I | manual | `esda.Moran` | manual | manual |
| Getis-Ord Gi* | manual | `esda.G_Local` | manual | manual |
| Spatial regression | n/a | `spreg.GM_Lag` etc. | n/a | n/a |
| GWR | n/a | `mgwr.gwr.GWR` | n/a | n/a |

In practice: pull data into a GeoDataFrame and use `pysal`/`mgwr`. PostGIS, Sedona, and DuckDB are for the data prep / aggregation, not the inference. Spatial statistics is single-node Python territory.

## Quick recipes

### Moran's I (global spatial autocorrelation)

```python
import geopandas as gpd
from libpysal.weights import Queen
from esda.moran import Moran

gdf = gpd.read_parquet("counties_with_turnout.parquet")
w = Queen.from_dataframe(gdf)  # adjacency: counties sharing edges
mi = Moran(gdf["turnout"], w)
print(f"Moran's I: {mi.I:.3f}, p-value: {mi.p_sim:.3f}")
```

If `mi.I` is meaningfully positive and `p_sim` is low, your variable is spatially clustered (similar values cluster together). If negative, dispersed. ~0 with high p_sim means random.

### LISA (local cluster map)

```python
from esda.moran import Moran_Local

mi_local = Moran_Local(gdf["turnout"], w)
gdf["lisa_cluster"] = mi_local.q  # 1=HH, 2=LH, 3=LL, 4=HL
gdf["lisa_significant"] = mi_local.p_sim < 0.05
```

Then map `gdf` colored by cluster type — shows where the clusters and outliers are.

### Getis-Ord Gi* (hot-spot map)

```python
from esda.getisord import G_Local

g_local = G_Local(gdf["turnout"], w)
gdf["gi_z"] = g_local.Zs
gdf["hotspot"] = gdf["gi_z"] > 1.96  # 95% confidence
gdf["coldspot"] = gdf["gi_z"] < -1.96
```

### DBSCAN on lat/lng

```python
from sklearn.cluster import DBSCAN
import numpy as np

coords_rad = np.radians(gdf[["lat", "lng"]].values)
# eps in radians: 1km on Earth ≈ 1/6371 ≈ 0.000157 rad
clusterer = DBSCAN(eps=0.000785, min_samples=5, metric="haversine")
gdf["cluster"] = clusterer.fit_predict(coords_rad)
```

For lat/lng inputs, use `metric='haversine'` and convert to radians. For projected meter coordinates, use default Euclidean and `eps` in meters.

### Spatial regression (SAR — spatial autoregressive)

```python
from spreg import GM_Lag

y = gdf["turnout"].values.reshape(-1, 1)
x = gdf[["median_income", "college_pct"]].values
w.transform = "r"  # row-standardize
model = GM_Lag(y, x, w=w, name_y="turnout", name_x=["income", "college"])
print(model.summary)
```

If the spatial autoregressive coefficient (rho) is significant, neighboring values predict the outcome above and beyond the explanatory variables — your model needs to account for spatial structure or it'll overstate effects.

### Stratified spatial sampling

```python
def stratified_sample(gdf, n_per_stratum, strata_col):
    """Take n_per_stratum samples from each stratum."""
    return gdf.groupby(strata_col, group_keys=False).apply(
        lambda g: g.sample(n=min(n_per_stratum, len(g)), random_state=42)
    )

# By state
sample = stratified_sample(gdf, n_per_stratum=10, strata_col="state")
```

For more sophisticated spatial sampling (balanced, GRTS) use `pysal.lib.weights` + custom logic, or call out to R's `spsurvey` package.

## Pitfalls

### MAUP — Modifiable Areal Unit Problem

The same underlying spatial pattern can yield different statistical results depending on the aggregation unit (block group vs tract vs county). Always:

- Test at multiple scales if the conclusion matters.
- Document your unit choice and why.
- Don't over-interpret findings sensitive to aggregation.

### Spatial autocorrelation ≠ causation

Moran's I tells you values cluster — not why. Hot spots may be artifacts of the underlying spatial structure (cities cluster), not the phenomenon you're studying.

### Edge effects

Counties at the dataset boundary have fewer neighbors. Spatial weight matrices like Queen contiguity treat them differently. For continental US analysis, this often doesn't matter; for state-level analysis where the state is the boundary, it can bias results. Consider:

- Buffer with neighboring states' data (don't analyze the buffer; just include in the weights).
- Use a distance-band weights matrix instead of contiguity.
- Report sensitivity to edge handling.

### Sample size for inference

Spatial statistics often need at least 30+ areas for stable inference. Block-level analysis at the precinct level may have enough; small-area analysis often doesn't. Pseudo p-values from Monte Carlo simulation (`p_sim`) handle this better than analytical p-values, but neither rescues a 10-area dataset.

### Computational cost

Computing the W matrix for n areas is O(n²) memory. For n=100K (block group level), that's ~80 GB just for the matrix. Use sparse representations (`pysal.lib.weights.W` does by default) and consider tiling.

## Reference

- `pysal` ecosystem docs: https://pysal.org
- `mgwr` (GWR): https://github.com/pysal/mgwr
- "Geographic Information Analysis" (O'Sullivan & Unwin) — textbook covering most of this ground
- For deep regression: "Spatial Regression Models" (Ward & Gleditsch)

## Out of scope for this skill

- Spatial point process analysis (Ripley's K, kernel density estimation): see specialist refs
- Geostatistics / kriging: out of typical Siege civic-data scope; reach for `pykrige` or R's `gstat` if needed
- Network analysis on spatial graphs: see [`coding/postgis/`](../../coding/postgis/SKILL.md) (`pgrouting`) or the analysis/graph sub-skill
