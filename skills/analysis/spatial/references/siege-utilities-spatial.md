# siege_utilities + Spatial Router — What SU Obviates

Cross-engine map. Before reaching for any engine's native API, check whether SU already does the work. SU is the spine for Siege spatial pipelines; engine APIs fill the gaps.

## SU coverage by task category

### Boundary sourcing → use SU (any engine)

```python
from siege_utilities.geo.spatial_data import (
    get_geographic_boundaries,
    discover_boundary_types,
    BOUNDARY_TYPE_CATALOG,
)

# Discover what's available
print(discover_boundary_types())  # 40+ types

# Fetch a specific boundary
counties_tx = get_geographic_boundaries(
    boundary_type="county",
    state_fips="48",
    vintage=2020,
    crs="EPSG:4326",
)
# Returns GeoDataFrame ready to push to PostGIS / DuckDB / Sedona / GeoPandas
```

For non-US (GADM):

```python
from siege_utilities.geo.providers.boundary_providers import GADMProvider

p = GADMProvider()
mexico = p.fetch(country_iso="MEX", level=1)
```

**Skip:** writing your own `requests.get(census_tiger_url)` boilerplate.

### CRS coercion → use SU

```python
from siege_utilities.geo.crs import set_default_crs, get_default_crs, reproject_if_needed

set_default_crs("EPSG:4326")  # session-wide default

# Idempotent reproject — no-op if already correct
gdf = reproject_if_needed(gdf, "EPSG:4326")
```

**Skip:** writing your own check-then-reproject blocks.

### Census API → use SU

```python
from siege_utilities.geo.census_api_client import CensusAPIClient

client = CensusAPIClient(api_key="...")
df = client.get_census_data_with_geometry(
    variables=["B01001_001E"],  # total population
    geography="tract",
    state_fips="48",
    year=2022,
)
```

**Skip:** rolling your own Census API client.

### Census dataset selection → use SU

For "which Census dataset is right for this analysis?":

```python
from siege_utilities.geo.census_dataset_mapper import get_best_dataset_for_analysis

best = get_best_dataset_for_analysis(
    analysis_type="redistricting",
    geography_level="block",
    year_range=(2020, 2024),
)
print(best.dataset_id, best.confidence_score, best.rationale)
```

**Skip:** spending half a day reading Census documentation.

### GEOID manipulation → use SU

```python
from siege_utilities.geo.geoid_utils import (
    normalize_geoid, construct_geoid, parse_geoid,
    extract_parent_geoid, validate_geoid, geoid_to_slug,
)

normalize_geoid("48", "01", "0003")           # "48010003"
extract_parent_geoid("481010003001", level="tract")  # "48101000300"
geoid_to_slug("48101000300")                   # "us-tx-tract-101000300"
```

**Skip:** FIPS regex by hand; zero-padding logic.

### Areal interpolation → use SU

For "redistribute population from 2010 tracts to 2020 tracts":

```python
from siege_utilities.geo.interpolation.areal import interpolate_areal

result = interpolate_areal(
    source=tracts_2010,
    target=tracts_2020,
    extensive_variables=["pop"],         # sums when split
    intensive_variables=["density"],     # averages when split
)
```

**Skip:** writing your own area-weighting math; using `gpd.overlay` + manual aggregation.

### Choropleth maps → use SU

```python
from siege_utilities.geo.choropleth import create_choropleth, create_bivariate_choropleth

fig = create_choropleth(
    gdf=counties,
    column="population",
    classification="quantile",
    cmap="viridis",
)
```

**Skip:** 30 lines of matplotlib + mapclassify boilerplate.

### Isochrones → use SU

```python
from siege_utilities.geo.isochrones import get_isochrone, OpenRouteServiceProvider

p = OpenRouteServiceProvider(api_key="...")
gdf = get_isochrone(
    provider=p,
    locations=[(-98.49, 29.42)],
    range_seconds=[600, 1200, 1800],
    profile="driving-car",
)
```

**Skip:** rolling your own OpenRouteService / Valhalla client.

### Geocoding → use SU

```python
from siege_utilities.geo.geocoding import use_nominatim_geocoder
from siege_utilities.geo.providers.census_geocoder import geocode_batch_chunked

# Free Census Geocoder for US addresses
df = geocode_batch_chunked(addresses_df, address_col="address")
```

**Skip:** writing your own batch geocoder; rate-limit handling.

### Crosswalks → use SU

For "given 2010-vintage data, allocate to 2020 boundaries":

```python
from siege_utilities.geo.crosswalk.crosswalk_client import CrosswalkClient
from siege_utilities.geo.crosswalk.crosswalk_processor import apply_crosswalk

client = CrosswalkClient()
crosswalk = client.get_crosswalk(source_year=2010, target_year=2020, geography="tract", state_fips="48")

reallocated = apply_crosswalk(
    data_2010,
    crosswalk,
    weight_method="population",
    extensive_variables=["pop", "households"],
)
```

**Skip:** NHGIS API by hand; allocation math.

### H3 indexing → use SU (key for GDAL-less envs)

```python
from siege_utilities.geo.h3_utils import h3_index_points, h3_index_polygon, h3_spatial_join

points_indexed = h3_index_points(points_df, lat_col="lat", lng_col="lng", resolution=8)
polys_indexed = h3_index_polygon(polys_df, geom_col="geometry", resolution=8)
joined = h3_spatial_join(points_indexed, polys_indexed)
```

**Skip:** writing your own H3 cell binning.

### Capability detection → use SU

```python
from siege_utilities.geo.capabilities import geo_capabilities
caps = geo_capabilities()
# caps["tier"], caps["geopandas"], caps["sedona"], caps["duckdb"], etc.
```

**Skip:** try/except ImportError chains.

### Spark/Sedona runtime detection → use SU

```python
from siege_utilities.geo.spatial_runtime import resolve_spatial_runtime_plan
from siege_utilities.geo.databricks_fallback import select_spatial_loader

plan = resolve_spatial_runtime_plan()  # returns SpatialRuntimePlan
loader = select_spatial_loader(...)    # for Databricks specifically
```

**Skip:** detecting Spark/Sedona/native-spatial availability by hand.

### Geometry encoding for cross-stage Spark safety → use SU

```python
from siege_utilities.geo.spatial_runtime import encode_geometry, decode_geometry

payload = encode_geometry(geom)   # Spark-safe WKB payload
geom = decode_geometry(payload)
```

**Skip:** pickling Shapely (breaks across versions); WKT (loses precision).

## SU coverage by engine

### PostGIS

- ✓ Boundary sourcing, CRS coercion, Census API, GEOID manipulation, capability detection
- ✗ Connection helpers (bring-your-own psycopg2)
- ✗ ST_* query wrappers (write SQL directly)
- ✗ COPY-based bulk load helpers (use psycopg2 `copy_expert`)
- ✗ Spatial index management (write SQL: `CREATE INDEX ... USING GIST`)

### GeoPandas

- ✓ Most things — SU is GeoPandas-first internally
- ✗ pyogrio fallback for fiona (SU-6 candidate)
- ✗ `read_geoparquet`/`write_geoparquet` without GDAL (SU-1 candidate)

### Sedona

- ✓ Runtime detection, geometry encoding for cross-stage safety, Databricks loader plan
- ✗ Spatial join wrappers (SU-4 candidate)
- ✗ ST_* function wrappers
- ✗ Partition tuning helpers

### DuckDB-spatial

- ✗ SU pulls DuckDB as `performance` extra but only uses it for format conversion
- ✗ No `read_geoparquet`/`write_geoparquet` via DuckDB-WKB (SU-1 candidate)
- ✗ No DuckDB spatial query helpers (SU-9 candidate)

## What SU does NOT do

For any of these, write directly in the appropriate engine:

- Raw spatial queries (ST_Within, ST_DWithin, etc.)
- Spatial index management
- Geometry validation tier — `validate_geometry`, `simplify_geometry`, `fix_invalid_geometries` (SU-3 candidate)
- CRS validation helpers — `crs_distance_operations_safe`, `crs_to_projection_family` (SU-2 candidate)

## Per-engine deeper dive

For the engine-specific SU-interop maps:

- [`coding/postgis/references/siege-utilities-postgis.md`](../../coding/postgis/references/siege-utilities-postgis.md)
- [`coding/geopandas/references/siege-utilities-geopandas.md`](../../coding/geopandas/references/siege-utilities-geopandas.md)
- [`coding/sedona/references/siege-utilities-sedona.md`](../../coding/sedona/references/siege-utilities-sedona.md)
- (DuckDB-spatial doesn't have a separate SU map yet — use the DuckDB SKILL.md's "What SU does and doesn't do" section)

## The check-before-write workflow

Per [`_siege-utilities-rules.md`](../../_siege-utilities-rules.md):

1. **Reach for SU first.** Most spatial tasks have a SU function.
2. **If SU almost does it but doesn't:** evaluate whether the gap is generic (every Siege project would benefit) or project-specific.
3. **Generic** → file a SU PR before adding the local helper.
4. **Project-specific** → write locally, but in a `utils/` module shaped like `siege_utilities` for future lift.

Don't import SU for one-line stdlib equivalents. The rule is "prefer it for utility-shaped problems."
