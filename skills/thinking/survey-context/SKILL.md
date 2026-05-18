---
name: survey-context
description: "Author-time enforcement of entity-shape verification. Before writing or modifying code that references existing entities (models, tables, functions, files, APIs, env vars), produce a structured Context Survey naming what was verified, what was assumed, and what's unknown. Pairs with the static scanner (claude-configs-public#114) as the pre-write counterpart. Composes with `think` Step 1 (Context)."
user-invocable: true
allowed-tools: Read Grep Glob Bash
---

# Survey Context Before Writing

Before you write or modify code that touches existing entities, **survey those entities first.** Produce a Context Survey artifact naming what shape each entity actually has, what your task assumes about that shape, and which assumptions remain unverified.

This is the counterpart to the static scanner at `claude-configs-public#114`: the scanner catches what shipped; this skill prevents the original miss.

## Why

A recurring failure shape: code references entities — imports, model fields, table columns, function names, env vars — that don't exist or have a different shape than the author assumed. The reference looks plausible. CI doesn't exercise the path. The bug ships.

Observed instances (all same shape, different surface):

- `assign_boundaries.py` referenced `models.Q(...)` without importing `models`.
- `swh/census.py` imported `PostGISConnector` from a non-existent `siege_utilities.connectors` module.
- `dimension_loader.py` called `DimTime.objects.update_or_create(defaults={...})` with 6 keys that aren't fields on DimTime.
- `boundary_detail` applied `@method_decorator(cache_page, name="dispatch")` — class-based-view shape — on a function-based DRF view with no `dispatch` attribute.
- A reviewer (this skill's own author) declared `DemographicSnapshot.object_id` was an integer PK without checking; it's a CharField geoid-key.

Per writing-claims:6, N≥5 same-shape failures crosses the threshold for systemic intervention. **This skill is that intervention at the author side.**

## When to survey

Required before:
- Adding a new caller of an existing model, function, or table.
- Changing the shape (signature, schema, field set) of any entity with callers elsewhere.
- Wiring a new endpoint, command, or job to existing infrastructure.
- Writing a decorator, mixin, or generic-FK reference (the shape errors above are over-represented here).

Optional but recommended:
- Reviewing code that does any of the above (the survey doubles as the verification step in a hostile review).

Trivial-change escape: pure typographical, docs, or single-line literal changes do not require a survey.

## Artifact format

```
## Survey
Task: <one-line description>
Touched entities: <list>
Referenced entities: <list>

### Entity: <name> (<type>, <namespace>)
- Definition: <file:line>
- Surveyed at: <timestamp> via <command-or-tool>
- Verified attributes: <list of fields / signatures / methods actually present>
- Constraints: <unique_together, indexes, FK targets, type system>
- Callers (grep): <files referencing this entity>
- ASSUMPTIONS my task makes about this entity: <named explicitly>
- VERIFICATION STATUS: VERIFIED | ASSUMED | UNKNOWN

### Gaps
For each UNKNOWN: what would resolve it, and why proceeding without it is acceptable (or not).
```

The artifact is the durable thing. The survey activity is ephemeral. If the artifact is missing or unstructured, the survey didn't happen.

## Surveyor recipes

Each entity class has a canonical way to introspect its actual shape. The list below is the starting set; recipes grow with the codebase.

| Entity class | Surveyor |
|---|---|
| Django model | `Model._meta.get_fields()`; `python manage.py inspectdb` for raw DB shape; migration history walk |
| Django model field type | `Model._meta.get_field("name").get_internal_type()` — confirms CharField vs IntegerField, etc. |
| Django decorator shape | Check whether the view is function-based (`@api_view`) or class-based; `method_decorator(..., name="dispatch")` only applies to classes |
| Database table | `\d+ table_name` (psql); `SHOW CREATE TABLE` (mysql); `PRAGMA table_info` (sqlite); INFORMATION_SCHEMA |
| Spark DataFrame | `df.printSchema()`, `df.explain()`, `df.rdd.getNumPartitions()` |
| Spark catalog table | `spark.catalog.listColumns(tableName)` |
| Python function/class | Read the source; `inspect.signature`; grep callers |
| Python module/import | `python -c "import X; print(X.__file__)"`; grep for actual exported names in `__init__.py` |
| File on disk | `ls -la`, `head`, `wc -l`, `file` for format sniff |
| HTTP API | WebFetch / curl + inspect response shape, status code, headers |
| Environment variable | grep config files + dump from target environment |
| FK / cross-app reference | `_meta.get_fields()` filtered to ForeignKey types |
| ContentType / generic FK | Check `object_id` field type — int PK vs string-keyed differ in semantics |

When a recipe for the entity class isn't listed, add one. The library grows by use.

## Worked example (the api/geo views case)

Task: fix `boundary_detail` decorator and `_forward_geocode` / `_reverse_geocode` exception handling.

```
## Survey
Task: A1+A3 fix in socialwarehouse/api/geo/views.py
Touched entities: views.boundary_detail, views._forward_geocode, views._reverse_geocode
Referenced entities: cache_page (Django), api_view (DRF), method_decorator (Django),
                     siege_utilities.geo.geocoding.get_coordinates, geopy.geocoders.Nominatim

### Entity: cache_page (Django decorator)
- Definition: django/views/decorators/cache.py (verified via python -c)
- Surveyed at: 2026-05-18 via Read + Django docs
- Verified attributes: applies as @cache_page(seconds); wraps a callable (request -> response)
- ASSUMPTIONS: works as plain decorator on function-based @api_view views
- VERIFICATION STATUS: VERIFIED — Django docs + existing SW usage in other endpoints

### Entity: method_decorator (Django util)
- Definition: django/utils/decorators.py
- Surveyed at: 2026-05-18 via Django source
- Verified attributes: name="dispatch" references the class's dispatch method
- ASSUMPTIONS: requires the wrapped object to have an attribute named by `name=`
- VERIFICATION STATUS: VERIFIED — function-based views have no dispatch attribute, so
  @method_decorator(..., name="dispatch") silently no-ops or raises. The original code's
  cache was non-functional.

### Entity: boundary_detail
- Definition: socialwarehouse/api/geo/views.py:247
- Surveyed at: 2026-05-18 via Read
- Verified attributes: function-based, @api_view(["GET"]), takes (request, boundary_type, geoid)
- ASSUMPTIONS: no class-based-view machinery; no dispatch attribute
- VERIFICATION STATUS: VERIFIED — fix replaces method_decorator wrapper with bare @cache_page

### Entity: DemographicSnapshot (NOT touched, but originally implicated by A2/#113)
- Definition: siege_utilities/geo/django/models/demographics.py:157
- Surveyed at: 2026-05-18 via Read
- Verified attributes: object_id is CharField(max_length=20), geoid-keyed
- ASSUMPTIONS the original review made: object_id was IntegerField (WRONG)
- VERIFICATION STATUS: VERIFIED — A2 retracted as false positive; survey would have prevented
  authoring the false review in the first place
```

The DemographicSnapshot row is the load-bearing one: had this skill been run **on the review itself** (treating "produce a review claim about object_id type" as the task that references DemographicSnapshot), the false positive in #113 would not have been authored.

## Composition with existing primitives

- **`brain-first` universal check** (resolver) — this skill IS its full expansion for "do I know the shape of what I'm touching?"
- **`think` Step 1 (Context)** — this skill systematizes Step 1 with per-entity recipes and a structured artifact.
- **writing-code:4 (verify symbol exists)** — same shape applied per-symbol; this skill batches across all symbols a task references.
- **writing-code:5 (no hypothetical code)** — runtime version; this skill is the static / pre-write counterpart.
- **self-review SKILL.md `Goal source:` field** — names external context; the survey populates it.
- **scan_ast.py extension (#114)** — runtime / review-time enforcement; this skill is author-time. Together = belt + suspenders.

## Hard parts (acknowledged, not solved)

- **Coverage gap.** A survey of entities X, Y, Z doesn't catch that W is also load-bearing. Mitigation: the "Referenced entities" field forces enumeration; the `_writing-claims-rules.md` discipline applies — declare what you didn't survey.
- **Survey paralysis.** Exhaustive survey kills throughput. Mitigation: depth heuristics — DEEP for touched entities, SHALLOW (definition + verified attributes) for referenced, SKIP for transitively-pulled-in dependencies that the diff doesn't engage.
- **Stale recipes.** Surveyor recipes for Spark 3 vs 4, Django 4 vs 5, FastAPI vs Flask differ. The recipe table is open for amendment; PRs adding recipes are the maintenance path.
- **Domain expertise required.** Each surveyor recipe encodes what's worth checking in that domain. The library grows from the operator's accumulated expertise + observed failure shapes.

## Hard rules

**No survey = no write.** If the entities in your task touch existing infrastructure and the survey artifact does not exist, do not author the code.

**ASSUMED status counts as a finding.** Mark assumptions explicitly. A survey with no assumptions is a survey that didn't actually examine the entity's shape.

**UNKNOWN must be resolved or named.** Either close the gap (run the recipe) or declare in the Gaps section why proceeding without resolution is acceptable.

## Trigger conditions

- Always-on for non-trivial work that touches existing entities (same gate as `think`).
- Triggered by entity-naming in the task description.
- Operator-invokable as `/survey-context`.

## Known limitations

- The skill does not (yet) automate recipe execution. Authors run the recipes themselves and write up findings. A future tooling layer could partially automate the Django-model and Python-import recipes.
- The artifact format is not yet hook-enforced. The self-review hook checks for `Goal source:`; a future hook extension could check for a `Survey:` trailer pointing at a Survey artifact for non-trivial diffs.
- Coverage of the survey itself is operator-auditable, not automated. The scanner at #114 catches a subset of survey-misses; together they're complementary, not redundant.
