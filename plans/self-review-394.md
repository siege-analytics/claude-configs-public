---
propagation-deferred: will post to ticket with PR
---

# Self-review: Confidence tagging on skill recommendations (#394)

Self-Review: 3-tier confidence vocabulary documented in skillbuilder, applied to 4 skills
Self-Review-Source: plans/self-review-394.md
Design-Note-Source: https://github.com/siege-analytics/claude-configs-public/issues/394
Investigate-artifact: TRIVIAL (see ## Trivial-investigation declaration below)
Pre-mortem-artifact: TRIVIAL (see ## Trivial-investigation declaration below)
Hostile-review-artifact: WAIVED prose-only

## Hostile-review-waiver
Reason: Documentation additions to existing skill files, no executable code
Scope: skillbuilder/SKILL.md (vocabulary definition), geopandas/SKILL.md, databricks/SKILL.md, sedona/SKILL.md, duckdb-spatial/SKILL.md (tag application)
Compensating-control: text-only changes; tags are advisory, not enforcement

## Trivial-investigation declaration
Category: documentation addition
Cannot produce error: no executable code modified
Reason: Adding confidence tags to skill recommendation sections
Evidence: git diff --stat shows only .md files changed
Falsification: If a hook validates confidence tags or the build.py quality scorer checks for them, investigation would be required

## Assumptions
Goal source: https://github.com/siege-analytics/claude-configs-public/issues/394
Investigate-artifact: TRIVIAL (see ## Trivial-investigation declaration above)
Pre-mortem-artifact: TRIVIAL (see ## Trivial-investigation declaration above)
Pre-author-inventory: NONE
Trivial-against-state: documentation addition, no state contact
Working as: software engineer
Roles: Junior (applied tags to skills), Senior (verified tag assignments match actual project validation levels)

## Peer review

Shelves checked: writing-prose:1, writing-claims:1

### Gate evidence
- testing-frameworks/SKILL.md already uses [PROVEN]/[RECOMMENDED]/[EXPERIMENTAL] tags (verified reference implementation)
- N/A — no executable files, no tests, no notebooks, no doc build

## Lead review

**[Senior]** Tag assignments are defensible:
- GeoPandas [PROVEN]: core of the spatial stack, used in every geo project
- PostGIS [PROVEN]: primary persistence layer, years of production use
- Shapely [PROVEN]: foundational geometry library
- Sedona [RECOMMENDED]: used but fewer production deployments than GeoPandas/PostGIS
- DuckDB-spatial [EXPERIMENTAL]: promising but limited production validation
- Databricks Unity Catalog [PROVEN]: mandatory in all new workspaces
- Databricks Jobs [PROVEN]: established production pattern
- Databricks Liquid Clustering [RECOMMENDED]: newer feature, strong evidence but less history
- Databricks DLT [RECOMMENDED]: used but not as extensively as raw jobs

The skillbuilder vocabulary definition is clean and includes explicit criteria for each tier.

## Quantified claims

- 5 files modified: skillbuilder, geopandas, databricks, sedona, duckdb-spatial
- 3 confidence tiers: [PROVEN], [RECOMMENDED], [EXPERIMENTAL]
- 9 tags applied across 4 skills (plus reference implementation in testing-frameworks)
- 0 executable code changed

## Findings

No findings.
