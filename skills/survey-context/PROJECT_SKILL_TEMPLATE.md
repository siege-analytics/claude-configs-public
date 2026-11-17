# Project-skill template: survey-context

Copy the structure below to `<repo>/.agents/skills/survey-context/` to adopt the doc-as-canonical loop in your project.

## Required files

```
<repo>/.agents/skills/survey-context/
  config.md              <- this skeleton, filled in
  templates/entity.md    <- doc-page template (copy from this template dir)
  entities/              <- per-entity doc pages, grows over time
  recipes/               <- project-specific surveyor recipes (optional)
```

## `config.md` skeleton

```markdown
# survey-context project skill -- <project name>

## Doc root
<absolute repo path where entity pages live, e.g. `docs/entities/`>

## Entity catalog
| Name | Type | Namespace | Doc page |
|---|---|---|---|
| DimGeography | Django model | warehouse.models | docs/entities/dim_geography.md |
| Address | Django model | geo.models | docs/entities/address.md |
| ...

## Ownership
Drift findings file as tickets in <issue-tracker>; route to <team / individual>.
Doc-update DoD reviewed by <reviewer rotation or role>.

## Recipe extensions
List project-specific surveyor recipes in `recipes/`. Examples:
- recipes/census-vintage.md  <- TIGER vintage handling, summary_level conventions
- recipes/spark-delta.md     <- Delta table introspection (CDF, history, OPTIMIZE state)
```

## `templates/entity.md` skeleton

```markdown
# <Entity name> (<type>, <namespace>)

**Definition:** <file:line>
**Watched paths:** `<glob1>`, `<glob2>`  <!-- Optional v2.2 field. Backtick-quoted comma-separated globs (bash `case`-pattern; no `**`). Hook fires if any diff file matches. Use sparingly; intended for important callers that should track contract changes. Leave the field absent if not needed. -->
**Surveyed at:** <YYYY-MM-DD>
**Owner:** <team / role>

## Shape

### Fields / signature / columns
<list -- declared fields with type + constraints>

### Constraints
<unique_together, indexes, FK targets, NOT NULL, defaults>

### Lookups / methods of interest
<for Django models: lookups callers rely on; for functions: documented contract>

## Callers / consumers
<grep result trimmed to load-bearing references>

## Cross-references
<FKs in/out, related models, downstream tables / endpoints>

## Known assumptions / gotchas
<things authors get wrong; e.g. "object_id is CharField geoid-string, NOT integer PK">

## Survey log
- YYYY-MM-DD: <what changed / who verified / why update>
```

## `entities/<name>.md` example

Use the template above. The first entity added in a project doesn't need full coverage -- seed with what you know, expand on next touch. The doc-page-exists check is what the skill needs; completeness grows organically.

## `recipes/<class>.md` skeleton

```markdown
# Recipe: <entity class>

**Surveyor command:** <how to introspect this class in this project>

**What to record in the entity page:** <field list, particular constraints worth naming>

**Drift signals:** <what indicates the doc is stale>

**Common-mistake patterns:** <author errors this recipe should catch>
```

## Where this layer lives in the resolver

Project skills are resolved at `<projectRoot>/.agents/skills/<slug>/SKILL.md` per the existing three-tier scheme (global > workspace > project). The global `survey-context` SKILL looks for the project layer at the conventional path; if present, uses it; if absent, falls back to v1 introspection-only behavior.

## Bootstrap order

1. Drop `config.md` + `templates/entity.md` into the project skill dir.
2. Seed `entities/` with 3-6 of the highest-traffic entities (the ones that appear in incident postmortems or hostile-review findings).
3. Let the skill grow the catalog organically -- every survey that hits `NO-DOC` offers to seed the doc page from live introspection.
4. Once coverage is meaningful (~20 entities), enable the hook (`survey-context.sh`, v2.1) to make the shape-change → doc-touch DoD enforced.
