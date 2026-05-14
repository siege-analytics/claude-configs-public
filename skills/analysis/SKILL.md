---
name: analysis-methods
description: "Analysis methodology. TRIGGER: geographic data, spatial joins, statistical modeling, graph analysis, entity matching, or text processing. Routes to the method."
user-invocable: false
paths: "**/*.py,**/*.geojson,**/*.shp,**/*.gpkg,**/*.parquet"
---

# Analysis Methods Router

Select the appropriate analysis methodology based on the problem type.

## First question: is your tabular representation trustworthy?

Before routing to any methodology, apply [`data-trust`](../_data-trust-rules.md). In Siege civic / Census / FEC / redistricting work, the tabular representation is usually wrong, stale, or missing rows. Spatial methods exist *precisely because* the identifiers are dirty — if your join key isn't trustworthy, you don't get to skip geometry by reaching for a crosswalk. You skip the crosswalk *because* you have geometry.

The same premise applies to entity resolution (the names don't match, that's why you need fuzzy matching) and to graph analysis (the explicit FK relationships are missing or wrong, that's why you need to reconstruct edges). Each sub-skill assumes you've already failed the trust check on the easy path.

## Routing Table

| Signal | Sub-Skill | Path |
|--------|-----------|------|
| Geographic data, coordinates, polygons, boundaries, PostGIS, spatial joins | Spatial analysis | [`spatial`](../analysis/spatial/SKILL.md) |
| Statistical modeling, regression, hypothesis testing, distributions, sampling | Statistical methods | `statistical` (planned) |
| Network/graph data, entity relationships, community detection, path finding | Graph analysis | `graph` (planned) |
| Record linkage, deduplication, fuzzy matching, identity resolution | Entity resolution | `entity-resolution` (planned) |
| Text classification, extraction, NLP, embeddings, language models | NLP methods | `nlp` (planned) |

Not all sub-skills exist yet. If a routing table entry points to a file that doesn't exist, apply general best practices for that methodology.

## Rules

1. **Trust check first.** Apply `_data-trust-rules.md` before routing. If your join key is dirty, you're choosing the methodology that *handles* the dirt (geometry, fuzzy matching, graph reconstruction), not the one that pretends the dirt isn't there.
2. **Consult the decision framework inside each sub-skill.** The spatial sub-skill, having confirmed the trust premise, then asks "given that I have to use geometry, which engine and which path?" Many spatial-sounding problems are still graph or string-lookup problems — but only after the trust check.
3. **Load only the relevant methodology.** Most analysis tasks need exactly one sub-skill.
4. **Stack rarely.** Entity resolution + graph analysis may combine for network deduplication. Spatial + statistical may combine for geographic modeling. But the default is one sub-skill.
5. **`_data-trust-rules.md` applies to any skill that ingests or joins external data.** It's an always-on convention, not a sub-skill — sibling of `_output-rules.md`. Load it once at session start.
6. **Reference files load on demand.** Each sub-skill may have a `reference.md` or per-axis references under `references/`. Load on demand, not eagerly.

## Gotchas

- Problems described with geographic language ("donors near this district", "campaigns in neighboring states") may actually be graph problems about connections between entities, not positions in space. Check the spatial sub-skill's decision tree first.
- Entity resolution and NLP overlap for name matching. Entity resolution is the right choice when the goal is deduplication or identity linkage. NLP is right when the goal is extraction, classification, or generation.
- Statistical methods and graph analysis overlap for community detection. If the communities are defined by explicit edges (donations, memberships), use graph analysis. If defined by feature similarity (demographics, behavior), use statistical clustering.
- "Machine learning" is not a methodology — it's a tool that appears in several methodologies. Route by the problem type, not the technique.
