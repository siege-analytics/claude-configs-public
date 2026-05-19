# siege_utilities + GeoPandas — Interop Map

When working in GeoPandas/Shapely in Siege projects, [`siege_utilities`](https://github.com/siege-analytics/siege_utilities) covers a large chunk of the typical pipeline (sourcing, CRS, Census plumbing, choropleth) and explicitly supports GDAL-less environments via its capability tiers.

This file is the per-task map.

## Always start the session with

```python
from siege_utilities.geo.capabilities import geo_capabilities
from siege_utilities.geo.crs import set_default_crs

caps = geo_capabilities()  # returns dict with tier and per-package booleans
set_default_crs("EPSG:4326")
```

`caps["tier"]` is `"geo"` (full), `"geo-lite"` (Shapely+pyproj only), `"geodjango"` (geo + Django GIS), or `"none"`.

## Boundary sourcing — use SU

Don't `requests.get()` a TIGER shapefile by hand:

```python
from siege_utilities.geo.spatial_data import (
    get_geographic_boundaries,
    discover_boundary_types,
    BOUNDARY_TYPE_CATALOG,
)

# What's available?
print(discover_boundary_types())  # 40+ types
# {'state', 'county', 'tract', 'block_group', 'cd118', 'sldu', ...}

# Fetch
states = get_geographic_boundaries(boundary_type="state", vintage=2020, crs="EPSG:4326")
counties_tx = get_geographic_boundaries(boundary_type="county", state_fips="48", vintage=2020)
```

Returns a `GeoDataFrame` ready to use. SU caches downloads.

For non-US (GADM):

```python
from siege_utilities.geo.providers.boundary_providers import GADMProvider

p = GADMProvider()
mexico_admin1 = p.fetch(country_iso="MEX", level=1)
```

## CRS — use SU

```python
from siege_utilities.geo.crs import reproject_if_needed

# Idempotent — no-op if already correct
gdf = reproject_if_needed(gdf, "EPSG:4326")
```

Skip writing your own check-then-reproject blocks.

## Census API — use SU

Don't roll your own Census API client:

```python
from siege_utilities.geo.census_api_client import CensusAPIClient, VARIABLE_GROUPS

client = CensusAPIClient(api_key="...")

# Variable discovery
print(VARIABLE_GROUPS)  # {'demographics', 'income', 'housing', ...}

# Pull demographics joined to geometry
gdf = client.get_census_data_with_geometry(
    variables=["B01001_001E"],  # total population
    geography="tract",
    state_fips="48",
    year=2022,
)
```

## Census dataset selection — use SU

For the meta-question "which Census dataset is right for my analysis?":

```python
from siege_utilities.geo.census_data_selector import select_datasets_for_analysis
from siege_utilities.geo.census_dataset_mapper import get_best_dataset_for_analysis

best = get_best_dataset_for_analysis(
    analysis_type="redistricting",
    geography_level="block",
    year_range=(2020, 2024),
)
print(best.dataset_id, best.confidence_score, best.rationale)
```

This is SU's recommendation engine — saves a half-day of API/documentation slogging per project.

## GEOID manipulation — use SU

```python
from siege_utilities.geo.geoid_utils import (
    normalize_geoid, construct_geoid, parse_geoid,
    extract_parent_geoid, validate_geoid, geoid_to_slug,
)

normalize_geoid("48", "01", "0003")  # "48010003" (correctly zero-padded)
extract_parent_geoid("481010003001", level="tract")  # "48101000300"
geoid_to_slug("48101000300")  # "us-tx-tract-101000300"
validate_geoid("12345")  # False — not a recognized FIPS shape
```

Don't write FIPS regex by hand.

## Areal interpolation — use SU

For "redistribute population from 2010 tracts to 2020 tracts based on area overlap":

```python
from siege_utilities.geo.interpolation.areal import interpolate_areal, ArealInterpolationResult

result = interpolate_areal(
    source=tracts_2010,           # GeoDataFrame with population
    target=tracts_2020,           # GeoDataFrame to allocate to
    extensive_variables=["pop"],  # sums-when-split (population, dollars)
    intensive_variables=["density"],  # averages-when-split (density, percent)
)
result.target  # GeoDataFrame with allocated values
```

(Per upstream PR candidate **SU-8**, this should also return coverage metrics; until then, validate manually.)

## Choropleth maps — use SU

```python
from siege_utilities.geo.choropleth import create_choropleth, create_bivariate_choropleth

fig = create_choropleth(
    gdf=counties,
    column="population",
    classification="quantile",  # 'fisher_jenks', 'equal_interval', 'natural_breaks', etc.
    cmap="viridis",
    title="County Population, 2022",
)
fig.savefig("pop.png", dpi=150)

# Bivariate (two variables on same map)
fig = create_bivariate_choropleth(
    gdf=counties,
    column_x="median_income",
    column_y="college_pct",
    color_scheme="GnBu",
)
```

## Isochrones — use SU

For "all areas reachable within 30 minutes by car from this point":

```python
from siege_utilities.geo.isochrones import get_isochrone, OpenRouteServiceProvider

p = OpenRouteServiceProvider(api_key="...")
gdf = get_isochrone(
    provider=p,
    locations=[(-98.49, 29.42)],  # San Antonio
    range_seconds=[600, 1200, 1800],  # 10, 20, 30 min
    range_type="time",
    profile="driving-car",
)
# Returns a GeoDataFrame with isochrone polygons
```

Or `ValhallaProvider` if you have a Valhalla server.

## Crosswalks — use SU

For "given 2010-vintage census data, allocate to 2020 boundaries":

```python
from siege_utilities.geo.crosswalk.crosswalk_client import CrosswalkClient
from siege_utilities.geo.crosswalk.crosswalk_processor import (
    apply_crosswalk, normalize_to_year, identify_boundary_changes,
)

client = CrosswalkClient()
crosswalk = client.get_crosswalk(
    source_year=2010,
    target_year=2020,
    geography="tract",
    state_fips="48",
)

reallocated = apply_crosswalk(
    data_2010,                # pandas DataFrame
    crosswalk,
    weight_method="population",
    extensive_variables=["pop", "households"],
)
```

This is pure pandas — works in geo-lite tier.

## H3 indexing — use SU

For approximate spatial joins without GeoPandas:

```python
from siege_utilities.geo.h3_utils import (
    h3_index_points, h3_index_polygon, h3_spatial_join, h3_resolution_for_area,
)

# Pick resolution by target hex area (in m²)
res = h3_resolution_for_area(target_area_m2=1_000_000)  # ~1 km² hexes

# Index points and polygons to H3
points_indexed = h3_index_points(points_df, lat_col="lat", lng_col="lng", resolution=res)
polys_indexed = h3_index_polygon(polys_df, geom_col="geometry", resolution=res)

# Join via H3 cell
joined = h3_spatial_join(points_indexed, polys_indexed)
```

H3 doesn't need GDAL — works at geo-lite tier. Approximate but fast.

## Geocoding — use SU

```python
from siege_utilities.geo.geocoding import (
    use_nominatim_geocoder, get_coordinates, NominatimGeoClassifier,
)

addresses = ["1600 Pennsylvania Ave NW, Washington DC", ...]
df = use_nominatim_geocoder(addresses, base_url="https://nominatim.openstreetmap.org")
```

Or `geo.providers.census_geocoder.geocode_batch_chunked()` for the (free, fast) Census Geocoder.

## What SU doesn't yet do

(Upstream PR candidates — pending the other agent's tickets.)

- **SU-1:** `read_geoparquet()` / `write_geoparquet()` without GDAL — major gap for cloud GDAL-less environments.
- **SU-2:** CRS validation helpers (`crs_distance_operations_safe`, `crs_to_projection_family`).
- **SU-3:** Geometry validation tier (`validate_geometry`, `simplify_geometry`, `fix_invalid_geometries`).
- **SU-7:** `csv_to_geoparquet(csv_path, lat_col, lon_col, output_path)`.
- **SU-9:** DuckDB spatial-query helpers.

Until they land, do the equivalent inline. See [`no-gdal-fallbacks.md`](no-gdal-fallbacks.md) for the workarounds.

## Checklist when starting a GeoPandas task

- [ ] `geo_capabilities()` called; tier known
- [ ] `set_default_crs("EPSG:4326")` (or your target) at session start
- [ ] Boundaries via `get_geographic_boundaries`, not hand-fetched
- [ ] CRS reprojection via `reproject_if_needed`
- [ ] GEOID work via `geoid_utils`, not regex
- [ ] Areal interpolation via `interpolate_areal`, not hand-rolled `gpd.overlay` + math
- [ ] Choropleths via `create_choropleth`, not a 30-line matplotlib block
- [ ] If GDAL not available: switched to GeoParquet I/O and H3 joins
