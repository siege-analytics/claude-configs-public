# Spatial Inequality

How unequally a value is distributed *across space*. Goes beyond the segregation indices in [`spatial-statistics.md`](spatial-statistics.md) §8 by adding inequality measures (Gini, Theil) with explicit spatial decomposition — between-region vs within-region inequality.

GDSPy Chapter 9 frames this as the bridge between economic-inequality measures (originally non-spatial) and the spatial structure that produces them.

## When to use which family

| Question | Method family |
|---|---|
| "How separated are two groups across space?" | **Segregation indices** (Dissimilarity, Isolation, Exposure) — see [`spatial-statistics.md`](spatial-statistics.md) §8 |
| "How unequally is a continuous variable distributed across spatial units?" | **Inequality measures** (Gini, Theil) — this file |
| "Of the inequality I see, how much is between regions vs within them?" | **Theil decomposition** (this file) |
| "Are inequality patterns spatially clustered?" | Inequality + Moran's I on local inequality measures |

The two families answer different questions. Segregation is about *group separation*; inequality is about *value dispersion*. Both can be spatial.

## Inequality measures

### Gini coefficient

Range 0 (perfect equality) to 1 (one feature has everything). The classic:

```python
import numpy as np

def gini(values):
    sorted_v = np.sort(values)
    n = len(values)
    cumsum = np.cumsum(sorted_v)
    return (n + 1 - 2 * np.sum(cumsum) / cumsum[-1]) / n

gdf["income_gini"] = gini(gdf["median_income"].values)
```

Or use `inequality.gini.Gini` from PySAL's `inequality` package:

```python
from inequality.gini import Gini

g = Gini(gdf["median_income"].values)
print(g.g)
```

**Pitfall:** Gini is unit-invariant but not order-of-magnitude-aware. A Gini of 0.4 looks the same whether incomes range $20K–$200K or $20–$200. Always report alongside the underlying scale.

### Theil's T

Information-theoretic measure of inequality. Decomposable — its key advantage over Gini.

```python
from inequality.theil import Theil

t = Theil(gdf["median_income"].values)
print(t.T)
```

**Why decomposable matters:** Theil can be split into between-group and within-group components, enabling the spatial decomposition below.

### Atkinson index

Adds an **inequality aversion parameter** ε. Higher ε weights inequality at the bottom more heavily. Useful when the *kind* of inequality matters (e.g., poverty-focused analysis vs general dispersion).

```python
from inequality.atkinson import Atkinson

a = Atkinson(gdf["median_income"].values, e=0.5)  # ε = 0.5
print(a.A)
```

## Spatial decomposition — Theil's T_BG

The major technique. Decomposes total Theil's T into:

- **T_BG (between-group)** — inequality between regional means
- **T_WG (within-group)** — inequality within each region, averaged

```python
from inequality.theil import TheilD

t_decomp = TheilD(
    gdf["median_income"].values,
    partition=gdf["state"].values,  # group identifier
)
print(f"Total T: {t_decomp.T:.4f}")
print(f"Between groups: {t_decomp.bg:.4f}")
print(f"Within groups: {t_decomp.wg:.4f}")
print(f"Between share: {t_decomp.bg / t_decomp.T:.2%}")
```

**Interpretation:**
- High between-share → inequality is mostly *across* regions (regional effects dominate)
- High within-share → inequality is mostly *within* regions (regions are themselves diverse)

For civic / policy work, the share matters as much as the total. Federal-vs-state policy targeting only matters if between-state share is high.

### Significance via simulation

Compare observed decomposition to randomly-permuted partitions:

```python
from inequality.theil import TheilDSim

t_sim = TheilDSim(
    gdf["median_income"].values,
    partition=gdf["state"].values,
    permutations=999,
)
print(f"Observed BG share: {t_sim.bg[0]:.4f}")
print(f"p-value: {t_sim.bg_pvalue:.4f}")
```

If p < 0.05, the between-group share is significantly different from what random partitioning would produce. If p > 0.05, your "between-state inequality" is consistent with random spatial assignment.

## Spatial autocorrelation of inequality

Beyond decomposition: are inequality measures themselves spatially clustered?

```python
# Compute local Gini per neighborhood (e.g., per county-of-tracts)
gdf_county = gdf.dissolve(by="county", aggfunc={"income": list})
gdf_county["local_gini"] = gdf_county["income"].apply(lambda v: gini(np.array(v)))

# Then run Moran's I on local_gini
from libpysal.weights import Queen
from esda.moran import Moran
w = Queen.from_dataframe(gdf_county)
mi = Moran(gdf_county["local_gini"], w)
print(f"Moran's I of inequality: {mi.I:.3f}")
```

If positive Moran's I, "high-inequality places cluster near high-inequality places" — useful for targeting interventions.

## Lorenz curves

Visualize inequality. The Lorenz curve plots cumulative population share against cumulative value share; the diagonal is perfect equality, the bowed-out curve is unequal.

```python
import matplotlib.pyplot as plt

def lorenz(values):
    sorted_v = np.sort(values)
    n = len(values)
    cumsum = np.cumsum(sorted_v) / np.sum(sorted_v)
    return np.insert(cumsum, 0, 0)

x = np.linspace(0, 1, len(gdf) + 1)
y = lorenz(gdf["income"].values)

plt.plot(x, y, label="Lorenz")
plt.plot([0, 1], [0, 1], "k--", label="Perfect equality")
plt.fill_between(x, x, y, alpha=0.2)
plt.legend()
```

Side-by-side Lorenz curves for different regions / time periods make inequality differences visually obvious in a way single Gini numbers don't.

## Use cases in civic / Census work

| Question | Approach |
|---|---|
| "How unequal is income across this state's tracts?" | Gini on tract-level median income |
| "Of state income inequality, how much is between counties vs within?" | Theil decomposition with `partition=county` |
| "Where are the high-inequality clusters?" | Local Gini per region + Moran's I + LISA |
| "Has between-region inequality grown over time?" | Theil decomposition at multiple snapshots; trend the BG share |
| "How does the rural/urban split contribute to inequality?" | Theil with `partition=urbanicity_class` |
| "Is school-district inequality bigger than county inequality?" | Compute decomposition at both partitions; compare BG shares |

The Theil decomposition is the load-bearing tool — it's what economic geographers and policy analysts actually use to make the rural-urban / center-periphery / between-state arguments.

## Per-engine implementation

| Engine | Inequality measures |
|---|---|
| **GeoPandas + inequality (PySAL)** | Native — Gini, Theil, Atkinson, decomposition. **Default.** |
| **PostGIS** | Manual SQL for Gini (sort + cumsum). Theil + Atkinson are manageable in SQL but verbose. For decomposition, pull to Python. |
| **DuckDB-spatial** | Same as PostGIS — manual SQL works for Gini; pull to Python for the rest. |
| **Sedona** | Aggregate per region, collect to driver, run inequality computation in Python. |

Like other spatial-stats methods, the engine choice is about where the data prep happens. The inequality computation itself is single-node Python.

## Pitfalls

- **Gini on small samples** — high variance. Bootstrap for confidence intervals (`inequality.gini.Gini` doesn't ship them).
- **Theil with zero values** — `T = Σ (x_i / total) × log(x_i / mean)` blows up at x_i = 0. Either drop zeros (with rationale) or add a tiny offset (e.g., 0.01) and document it.
- **Comparing inequality across populations of different sizes** — Gini is size-invariant but Theil's level depends on n. For comparison, use Gini or normalize Theil.
- **Treating between-share as a causal claim** — high between-state inequality doesn't mean states *cause* the inequality. It means inequality varies geographically; unobserved variables may drive both.
- **Forgetting to weight by population** — tract-level Gini treats every tract equally regardless of size. For person-level interpretation, use weights:
  ```python
  Gini(gdf["income"].values, weights=gdf["population"].values)
  ```

## Cross-links

- [`spatial-statistics.md`](spatial-statistics.md) §8 — segregation indices (the related-but-distinct family)
- [`spatial-weights.md`](spatial-weights.md) — W matrix for spatial-autocorrelation tests on inequality
- [`spatial-feature-engineering.md`](spatial-feature-engineering.md) — when inequality measures become features for ML

## Citation

Rey, S.J., Arribas-Bel, D., Wolf, L.J. *Geographic Data Science with Python*. CRC Press, 2023. Chapter 9 ("Spatial Inequality"). Online edition: https://geographicdata.science/book/notebooks/09_spatial_inequality.html

PySAL `inequality` package: https://pysal.org/inequality/

Paraphrase + commentary; not redistribution.
