---
name: analysis-methods
description: "Analysis methodology. TRIGGER: geographic data, spatial joins, statistical modeling, graph analysis, entity matching, or text processing. Routes to the method."
user-invocable: false
paths: "**/*.py,**/*.geojson,**/*.shp,**/*.gpkg,**/*.parquet"
---

# Analysis Methods Router

Select the appropriate analysis methodology based on the problem type. **First question: is your tabular representation trustworthy? If not, you need geometry precisely because the identifiers are dirty — skip crosswalk shortcuts.** See `_data-trust-rules.md` at skills root.

## Routing Table

| Signal | Sub-Skill | Path |
|--------|-----------|------|
| Geographic data, coordinates, polygons, boundaries, PostGIS, spatial joins | Spatial analysis | [spatial/SKILL.md](spatial/SKILL.md) |
| Statistical modeling, regression, hypothesis testing, distributions, sampling | Statistical methods | [statistical/SKILL.md](statistical/SKILL.md) |
| Network/graph data, entity relationships, community detection, path finding | Graph analysis | [graph/SKILL.md](graph/SKILL.md) |
| Record linkage, deduplication, fuzzy matching, identity resolution | Entity resolution | [entity-resolution/SKILL.md](entity-resolution/SKILL.md) |
| Text classification, extraction, NLP, embeddings, language models | NLP methods | [nlp/SKILL.md](nlp/SKILL.md) |

Not all sub-skills exist yet. If a routing table entry points to a file that doesn't exist, apply general best practices for that methodology.

## Rules

1. **Consult the decision framework before loading.** The spatial sub-skill leads with "do you trust your tabular representation?" — real-world civic / census / redistricting data is usually dirty, which is the reason spatial methods exist. The older question "do you need geometry?" is Step 2.
2. **Load only the relevant methodology.** Most analysis tasks need exactly one sub-skill.
3. **Stack rarely.** Entity resolution + graph analysis may combine for network deduplication. Spatial + statistical may combine for geographic modeling. But the default is one sub-skill.
4. **Reference files load on demand.** Each sub-skill may have a `reference.md`. Load it only when directed.
5. **Conventions always apply.** `_data-trust-rules.md` applies to any skill that ingests or joins external data. `_output-rules.md` applies to anything that produces output.

## Gotchas

- Problems described with geographic language ("donors near this district", "campaigns in neighboring states") may actually be graph problems about connections between entities, not positions in space. Check the spatial sub-skill's decision tree first.
- Entity resolution and NLP overlap for name matching. Entity resolution is the right choice when the goal is deduplication or identity linkage. NLP is right when the goal is extraction, classification, or generation.
- Statistical methods and graph analysis overlap for community detection. If the communities are defined by explicit edges (donations, memberships), use graph analysis. If defined by feature similarity (demographics, behavior), use statistical clustering.
- "Machine learning" is not a methodology — it's a tool that appears in several methodologies. Route by the problem type, not the technique.
