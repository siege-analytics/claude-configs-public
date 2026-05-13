# siege_utilities + PostGIS — Interop Map

When working with PostGIS in Siege projects, [`siege_utilities`](https://github.com/siege-analytics/siege_utilities) helps with the *upstream* of getting data into Postgres (boundary sourcing, Census data, GEOID wrangling) and the *Django/ORM* side of querying it. It does **not** wrap raw ST_* operations — that's bring-your-own-psycopg2.

This file is the per-task map of what SU gives you vs. what you write directly.

## What SU obviates

### Boundary sourcing → use SU

Don't fetch TIGER/GADM shapefiles by hand. SU has providers:

```python
from siege_utilities.geo.spatial_data import get_geographic_boundaries

gdf = get_geographic_boundaries(
    boundary_type="state",
    vintage=2020,
    crs="EPSG:4326",
)
# gdf is a GeoDataFrame ready to load into PostGIS
```

Discover what's available:

```python
from siege_utilities.geo.spatial_data import discover_boundary_types, BOUNDARY_TYPE_CATALOG

print(discover_boundary_types())  # 40+ boundary types
```

Then `gdf.to_postgis(...)` (GeoPandas) or use SU's GeoDjango models for ingest.

### CRS coercion → use SU

Before writing geometry to PostGIS:

```python
from siege_utilities.geo.crs import set_default_crs, reproject_if_needed

set_default_crs("EPSG:4326")  # session-wide default
gdf = reproject_if_needed(gdf, "EPSG:4326")
```

### Census data → use SU

For loading Census demographics joined to boundaries you'll then push to PostGIS:

```python
from siege_utilities.geo.census_api_client import CensusAPIClient

client = CensusAPIClient(api_key=...)
df = client.get_census_data_with_geometry(
    variables=["B01001_001E"],  # total population
    geography="tract",
    state_fips="48",
    year=2022,
)
df.to_postgis("census_tract_pop", engine, if_exists="replace")
```

### GEOID handling → use SU

Don't write your own FIPS regexes:

```python
from siege_utilities.geo.geoid_utils import normalize_geoid, extract_parent_geoid

normalize_geoid("4810130")  # state+county+tract → "48101000300" (zero-padded canonical)
extract_parent_geoid("481010003001", level="tract")  # "48101000300"
```

### GeoDjango ORM for boundary tables → use SU

SU ships 37 geo-Django models for Census/GADM/NLRB/Federal Judicial boundaries. If your Postgres is also your Django app's database, prefer:

```python
from siege_utilities.geo.django.models import State, County, Tract

texas = State.objects.get(state_fips="48")
counties_in_tx = County.objects.filter(state=texas)
```

over hand-rolled `psycopg2.execute("SELECT ... FROM counties WHERE state_fips = '48'")`.

## What SU does **not** do — write directly

### Raw ST_* spatial queries

SU has no `postgis_nearest()` / `postgis_intersects()` helper. Use `psycopg2` or `SQLAlchemy.text()` directly:

```python
import psycopg2

with psycopg2.connect(dsn) as conn, conn.cursor() as cur:
    cur.execute("""
        SELECT name FROM places
        WHERE ST_DWithin(
            geom::geography,
            ST_SetSRID(ST_Point(%s, %s), 4326)::geography,
            %s
        )
    """, (lng, lat, distance_m))
    rows = cur.fetchall()
```

If you find yourself writing the same wrapper twice, that's a candidate **siege_utilities PR** — see the upstream backlog (item SU-5: PostGIS query-builder layer).

### COPY-based bulk loads

SU has no COPY helper. Use psycopg2's `copy_expert` directly for the fastest bulk load:

```python
with conn.cursor() as cur:
    with open("data.csv") as f:
        cur.copy_expert(
            "COPY features (id, geom_wkt) FROM STDIN WITH CSV HEADER",
            f,
        )
    cur.execute("UPDATE features SET geom = ST_GeomFromText(geom_wkt, 4326)")
```

### Raw ST_DWithin / ST_Subdivide / index management

These are PostGIS-side operations. Issue them as SQL; no SU layer.

### Spatial index creation

```python
cur.execute("CREATE INDEX features_geom_idx ON features USING GIST (geom)")
cur.execute("VACUUM (ANALYZE) features")
```

## Gap map (SU-PR candidates)

If you write the same code in two projects, it likely belongs upstream. Top candidates from the spatial overhaul plan §10:

- **SU-5:** PostGIS query-builder helpers (`postgis_nearest`, `postgis_intersects`, `postgis_within`)
- **SU-1:** GeoParquet I/O without GDAL (helps Postgres-→ GeoParquet export workflows)
- **SU-2:** CRS validation helpers (catches "I called ST_Distance on lat/lng" before it hits the DB)

Apply the [`siege-utilities`](../../_siege-utilities-rules.md) workflow: file an SU PR before adding the helper locally.

## Checklist when starting a PostGIS task

- [ ] Run `siege_utilities.geo.capabilities.geo_capabilities()` to confirm SU's geo tier is available.
- [ ] Source boundary data via SU providers (don't shapefile-curl by hand).
- [ ] Set the default CRS via SU at session start.
- [ ] Use GeoDjango models if the data fits SU's catalog; psycopg2 for queries beyond ORM scope.
- [ ] Spatial indexing, ST_* operations, EXPLAIN tuning — all SQL, no SU.
