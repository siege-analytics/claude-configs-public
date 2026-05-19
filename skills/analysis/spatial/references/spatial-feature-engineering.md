# Spatial Feature Engineering for ML

When the goal is prediction (not inference), spatial structure matters in two places: **the features** (what you use to predict) and **the validation strategy** (how you measure success). Both diverge from non-spatial ML in subtle, easy-to-miss ways.

GDSPy Chapter 12 makes the case that spatial cross-validation is **non-negotiable** for spatial ML. Random K-fold leaks signal across spatially-adjacent train/test rows; reported accuracy will be optimistic, sometimes catastrophically.

## Why spatial ML needs different feature engineering

Two reasons:

1. **Spatial autocorrelation gives you free predictive power.** A feature's neighbor-mean is often a strong predictor — but only useful if you handle the leakage problem (below).
2. **Geographic coordinates aren't features.** Raw lat/lng as an X column gives the model no useful signal; the model learns "Texas-ness" if you're lucky and overfits to specific regions if you're not. Engineered spatial features (neighborhood characteristics, distance to landmarks, density measures) are the actually-useful inputs.

## Feature families

### 1. Neighbor-aggregate features

For each feature, compute summary statistics of its neighbors' values:

```python
from libpysal.weights import Queen, lag_spatial

w = Queen.from_dataframe(gdf)
w.transform = "r"  # row-standardize for "average of neighbors"

gdf["income_neighbor_mean"] = lag_spatial(w, gdf["median_income"].values)
```

Useful neighbor aggregates:
- **Mean** — most common; "what's typical around here"
- **Median** — robust to outlier neighbors
- **Min / Max / Range** — highest income neighbor; range as a "diversity" signal
- **Std deviation** — local heterogeneity
- **Count above threshold** — how many neighboring features are >$100K income, etc.

Usually, the neighbor-mean of Y itself (the target) is the strongest predictor. **Don't include it** if you want generalizable models — it's a proxy for "places similar to this one are similar to this one." Tautological. Use neighbor-means of *other* features instead.

### 2. Distance-to features

How far is each feature from a notable point?

```python
from shapely.geometry import Point

city_centers = gpd.read_parquet("city_centers.parquet")
city_centers_proj = city_centers.to_crs("EPSG:5070")
gdf_proj = gdf.to_crs("EPSG:5070")

gdf["dist_to_nearest_city_m"] = gdf_proj.geometry.apply(
    lambda g: city_centers_proj.distance(g).min()
)
```

Useful distances:
- Distance to nearest urban center
- Distance to nearest highway / transit
- Distance to nearest competitor location
- Distance to coastline / state boundary

For multiple distance features, vectorize via spatial joins rather than per-row apply.

### 3. Density features

How many features (of some type) are nearby?

```python
from libpysal.weights import DistanceBand

# Build a distance-band W from points to a count-source
w_dist = DistanceBand.from_dataframe(gdf, threshold=5000)  # 5 km
gdf["facilities_within_5km"] = w_dist.cardinalities  # neighbor count
```

Or with a per-point count via spatial join:

```python
gdf_5070 = gdf.to_crs("EPSG:5070")
buffers = gdf_5070.geometry.buffer(5000)
gdf["facilities_within_5km"] = [
    facilities.sindex.query(buf, predicate="intersects").size
    for buf in buffers
]
```

Useful densities:
- Population density in surrounding area
- POI density (restaurants, schools, etc.)
- Road density (a proxy for accessibility)
- Same-class feature density (clustering signal)

### 4. Interaction-with-place features

Features that capture "what kind of place is this":
- Median attribute of the encompassing region (median income of the county the tract is in)
- Region-level totals scaled by feature share
- Group-share features (% of population in some demographic, fraction of POIs that are restaurants)

These are **multi-level** features — the feature's value is shaped by both its own attributes and the region it sits in.

### 5. Spatial weights as features

Direct embedding of the spatial graph:

```python
from libpysal.weights import w_to_gal_string
import scipy.sparse as sp

w_sparse = w.sparse  # scipy sparse matrix
# Use as input to graph neural networks, or for neighbor-aware regression
```

Less common in classical ML; central in GNN approaches.

## The validation problem — spatial cross-validation

### Why random K-fold leaks signal

Random K-fold assumes train and test rows are independent. In spatial data they're not — adjacent rows share spatial drivers, so a random split puts highly-correlated rows on both sides:

```
Random K-fold on spatial data:
  Train: tract_001, tract_005, tract_007, tract_010, tract_011
  Test:  tract_002, tract_006, tract_008
                  ↑
  tract_002 is adjacent to tract_001 (in train) — they share neighborhood
  effects, so the model "predicts" tract_002 well because it memorized
  tract_001's pattern, not because it learned anything generalizable.
```

Result: training accuracy and test accuracy both look great. Production accuracy on a different region (truly out-of-sample) collapses.

This is the spatial-stats version of the "did you accidentally test on training data" mistake. Unlike that classic, it can happen even with clean train/test splits — the leak is through spatial autocorrelation, not row overlap.

### Spatial K-fold

Split by spatial location, not random sample:

```python
import numpy as np
from sklearn.model_selection import KFold

# Naive spatial K-fold: split by spatial coordinate buckets
n_folds = 5
gdf_proj = gdf.to_crs("EPSG:5070")
gdf_proj["x_bucket"] = pd.qcut(gdf_proj.geometry.x, n_folds, labels=False)
gdf_proj["fold"] = gdf_proj["x_bucket"]

for fold in range(n_folds):
    train = gdf_proj[gdf_proj["fold"] != fold]
    test = gdf_proj[gdf_proj["fold"] == fold]
    # train model on train, evaluate on test
```

For a more principled split, use spatial blocks:

```python
# Better: square spatial blocks via spatial clustering
from sklearn.cluster import KMeans
coords = np.column_stack([gdf_proj.geometry.x, gdf_proj.geometry.y])
gdf_proj["block"] = KMeans(n_clusters=n_folds, random_state=42).fit_predict(coords)
# Then K-fold by block
```

Or use a dedicated library:

```python
from sklearn.model_selection import GroupKFold
gkf = GroupKFold(n_splits=5)
for train_idx, test_idx in gkf.split(X, y, groups=gdf["state"]):
    # Train on some states, test on others
    ...
```

`GroupKFold` with state / region as the group is the simplest way to ensure no train-test spatial overlap.

### Buffered spatial K-fold

For datasets where adjacent groups still leak (e.g., adjacent counties have shared media markets):

```python
from sklearn.cluster import KMeans
import numpy as np

def buffered_spatial_kfold(gdf, n_folds=5, buffer_m=5000):
    coords = np.column_stack([gdf.geometry.x, gdf.geometry.y])
    blocks = KMeans(n_clusters=n_folds, random_state=42).fit_predict(coords)
    
    for fold in range(n_folds):
        test = gdf[blocks == fold]
        # Buffer the test set; exclude train rows within the buffer
        test_buffered = test.geometry.buffer(buffer_m).unary_union
        train = gdf[(blocks != fold) & ~gdf.geometry.intersects(test_buffered)]
        yield train.index, test.index
```

The buffer ensures train rows aren't spatially adjacent to test rows. Conservative; reduces effective training data.

### When non-spatial K-fold is OK

If your model genuinely doesn't use any spatial features and won't be deployed across spatial regions (e.g., predicting an attribute from non-spatial covariates only), random K-fold is fine. But: if you're using *any* of the feature families above, you need spatial K-fold.

Default assumption: **if it's spatial data, you need spatial K-fold.** Justify the exception, not the rule.

## Other spatial-ML gotchas

### Coordinate reference system

If you use raw lat/lng as features, your model learns spurious "Texas vs Maine" patterns based on coordinate magnitude. Either:
- **Project first** so coordinate units are meaningful (meters from a reference point).
- **Don't use raw coordinates** — use derived spatial features (neighbor aggregates, distances) instead.

### Data leakage via coordinates

If your model has access to lat/lng, it can implicitly memorize the train set's spatial layout and "predict" by spatial proximity. Even with spatial K-fold, this is a leakage path. Either drop coordinates or use them only for the spatial-CV split, not as features.

### Imbalanced spatial data

Some spatial classes are rare (e.g., predicting which counties had unusual events). Standard imbalance corrections (oversampling, class weights) apply, but **resample within spatial blocks** — don't oversample across the entire dataset, which would put oversampled rows in both train and test (leak again).

### Time-and-space data

Cross-validation gets harder. Standard approach: hold out a future time period, evaluate on it spatially. Spatiotemporal CV libraries (e.g., `mlxtend.evaluate.GroupTimeSeriesSplit`) help.

## Recipes

### Predicting county-level turnout from demographic + spatial features

```python
import geopandas as gpd
import numpy as np
import pandas as pd
from libpysal.weights import Queen, lag_spatial
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import GroupKFold
from sklearn.metrics import r2_score

gdf = gpd.read_parquet("counties.parquet").to_crs("EPSG:5070")

# Build W
w = Queen.from_dataframe(gdf, ids="geoid")
w.transform = "r"

# Engineer spatial features
gdf["income_neighbor_mean"] = lag_spatial(w, gdf["median_income"].values)
gdf["college_neighbor_mean"] = lag_spatial(w, gdf["college_pct"].values)
# ...etc

X = gdf[["median_income", "college_pct", "income_neighbor_mean", "college_neighbor_mean"]].values
y = gdf["turnout_pct"].values
groups = gdf["state"].values  # state-level CV groups

# Spatial CV
gkf = GroupKFold(n_splits=5)
scores = []
for train_idx, test_idx in gkf.split(X, y, groups=groups):
    model = GradientBoostingRegressor(random_state=42).fit(X[train_idx], y[train_idx])
    pred = model.predict(X[test_idx])
    scores.append(r2_score(y[test_idx], pred))

print(f"Spatial CV R²: mean={np.mean(scores):.3f}, std={np.std(scores):.3f}")
```

### Detecting leakage from spatial autocorrelation in residuals

After training (with random K-fold), compute Moran's I on the residuals:

```python
from esda.moran import Moran

residuals = y - model.predict(X)
mi = Moran(residuals, w)
print(f"Moran's I of residuals: {mi.I:.3f}, p_sim: {mi.p_sim:.3f}")
```

If significant positive Moran's I, your model isn't capturing the spatial structure — and your random-K-fold accuracy is overstating performance.

## Per-engine implementation

| Engine | Spatial features |
|---|---|
| **GeoPandas + libpysal** | Native — `lag_spatial`, distance-band W, all neighbor aggregates. **Default.** |
| **PostGIS** | SQL-friendly: `AVG(b.income) OVER (PARTITION BY ...)` for neighbor means; `ST_DWithin` for distance/density. Fast for very large datasets where pulling to Python is expensive. |
| **DuckDB-spatial** | Same as PostGIS — SQL works well for feature engineering. |
| **Sedona** | Spatial joins for neighbor aggregates; collect to driver for libpysal-style W operations. |

For ML training, **pull engineered features into a single-node Python frame**. Distributed ML on spatial data exists (Spark MLlib, etc.) but adds complexity for usually-marginal gain at scales where DuckDB/single-node Python work.

## Pitfalls (recap)

- **Random K-fold on spatial data** — leaks signal. Use spatial K-fold or GroupKFold.
- **Raw lat/lng as features** — model memorizes coordinate patterns. Use derived spatial features.
- **Including the target's spatial lag as a feature** — tautological. Use other variables' lags.
- **Spatial-block CV without buffer** — adjacent blocks may still share signal. Buffer if conservative.
- **Forgetting to check Moran's I on residuals** — the diagnostic that catches missed spatial structure.
- **Resampling for imbalance globally instead of within spatial blocks** — re-introduces leakage.
- **Standard MLOps tools assuming i.i.d. data** — model registries / drift monitors etc. may not flag spatial drift. Add spatial diagnostics manually.

## Cross-links

- [`spatial-weights.md`](spatial-weights.md) — W matrix construction (foundation for neighbor aggregates)
- [`spatial-statistics.md`](spatial-statistics.md) — diagnostic tests (Moran's I on residuals)
- [`siege-utilities-spatial.md`](siege-utilities-spatial.md) — SU helpers for boundary / density data sourcing
- [`coding/postgis/references/spatial-joins-performance.md`](../../../coding/postgis/references/spatial-joins-performance.md) — PostGIS-side feature engineering with `ST_DWithin`

## Citation

Rey, S.J., Arribas-Bel, D., Wolf, L.J. *Geographic Data Science with Python*. CRC Press, 2023. Chapter 12 ("Spatial Feature Engineering"). Online edition: https://geographicdata.science/book/notebooks/12_feature_engineering.html

Paraphrase + commentary; not redistribution.
