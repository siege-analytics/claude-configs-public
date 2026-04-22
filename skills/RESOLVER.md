# Skill Resolver

This is the top-level dispatcher. Skills live under category directories. **Read the skill file before acting.** If two skills could match, read both — they chain.

## Conventions (apply to everything)

| File | Purpose |
|---|---|
| [`_output-rules.md`](_output-rules.md) | Commit trailers, attribution policy, docstring minimums, markdown style — shared across all skills that write anything |
| [`_data-trust-rules.md`](_data-trust-rules.md) | Default assumption: tabular data lies. Validate at boundaries. — applied before any spatial / identifier work |

## Routing table

### Coding

| Trigger | Skill |
|---|---|
| Writing or reviewing any `.py`, `.sql`, `.ts`, `.go`, `.tsx`, `.jsx` | [`coding/SKILL.md`](coding/SKILL.md) router |
| "Review this PR", "review this diff" | [`coding/code-review/SKILL.md`](coding/code-review/SKILL.md) |
| Library code architecture — DRY, dataclass discipline, interface integrity, runtime types | [`coding/python-patterns/SKILL.md`](coding/python-patterns/SKILL.md) |
| "Why is this try/except too broad?", silent-failure patterns, `except Exception: pass` | [`coding/python-exceptions/SKILL.md`](coding/python-exceptions/SKILL.md) |
| Django models, views, forms, migrations, settings | [`coding/django/SKILL.md`](coding/django/SKILL.md) |
| Data pipeline, scheduled job, Rundeck YAML, Airflow DAG | [`coding/pipeline-jobs/SKILL.md`](coding/pipeline-jobs/SKILL.md) |
| PySpark DataFrame work, tuning, shuffle / skew | [`coding/spark/SKILL.md`](coding/spark/SKILL.md) |
| SQL query structure, joins, window functions, Postgres performance | [`coding/sql/SKILL.md`](coding/sql/SKILL.md) |
| PostGIS — ST_* functions, spatial indexes, spatial joins | [`coding/postgis/SKILL.md`](coding/postgis/SKILL.md) |

### Analysis

| Trigger | Skill |
|---|---|
| Geospatial data, polygons, CRS, coordinates | [`analysis/spatial/SKILL.md`](analysis/spatial/SKILL.md) |
| Statistical modeling, regression, hypothesis tests | `analysis/statistical/SKILL.md` (if present) |
| Graph / network analysis, entity relationships | `analysis/graph/SKILL.md` (if present) |
| Record linkage, dedup, fuzzy matching | `analysis/entity-resolution/SKILL.md` (if present) |
| NLP, text classification, extraction | `analysis/nlp/SKILL.md` (if present) |

### Maintenance

| Trigger | Skill |
|---|---|
| Renaming a public function, changing a default, dropping a column | [`maintenance/library-api-evolution/SKILL.md`](maintenance/library-api-evolution/SKILL.md) |
| Redundant docs across repos, "same thing in five places" | [`maintenance/consolidate/SKILL.md`](maintenance/consolidate/SKILL.md) |

### Git workflow

| Trigger | Skill |
|---|---|
| Create a new branch | [`git-workflow/branch/SKILL.md`](git-workflow/branch/SKILL.md) |
| Commit changes | [`git-workflow/commit/SKILL.md`](git-workflow/commit/SKILL.md) |
| Open a PR | [`git-workflow/create-pr/SKILL.md`](git-workflow/create-pr/SKILL.md) |
| Merge a PR | [`git-workflow/merge/SKILL.md`](git-workflow/merge/SKILL.md) |
| Protect `develop` / `main` | [`git-workflow/develop-guard/SKILL.md`](git-workflow/develop-guard/SKILL.md) |

### Session

| Trigger | Skill |
|---|---|
| CodeRabbit or other bot review on a PR | [`session/coderabbit-response/SKILL.md`](session/coderabbit-response/SKILL.md) |
| Inline PR discussion threads | [`session/pr-comments/SKILL.md`](session/pr-comments/SKILL.md) |
| End-of-session summary, close the loop | [`session/wrap-up/SKILL.md`](session/wrap-up/SKILL.md) |

### Planning

| Trigger | Skill |
|---|---|
| Create a Linear / Jira / GitHub issue | [`planning/create-ticket/SKILL.md`](planning/create-ticket/SKILL.md) |
| Update ticket status | [`planning/update-ticket/SKILL.md`](planning/update-ticket/SKILL.md) |
| Close a ticket | [`planning/close-ticket/SKILL.md`](planning/close-ticket/SKILL.md) |
| "What should I work on next?", opportunity surfacing | [`planning/im-feeling-lucky/SKILL.md`](planning/im-feeling-lucky/SKILL.md) |

### Documentation

| Trigger | Skill |
|---|---|
| Central docs consolidation across repos | [`documentation/cascading-documentation/SKILL.md`](documentation/cascading-documentation/SKILL.md) |
| Notion knowledge base | [`documentation/notion-knowledge-base/SKILL.md`](documentation/notion-knowledge-base/SKILL.md) |

### Thinking

| Trigger | Skill |
|---|---|
| Break down a problem, decision framework | [`thinking/think/SKILL.md`](thinking/think/SKILL.md) |

### Meta

| Trigger | Skill |
|---|---|
| "Create a skill", "audit skills", "fix this skill" | [`meta/skillbuilder/SKILL.md`](meta/skillbuilder/SKILL.md) |
| "Is every skill reachable from the resolver?" | [`meta/check-resolvable/SKILL.md`](meta/check-resolvable/SKILL.md) |
| "Test that the right skill fires for each input" | [`testing/resolver-evals/SKILL.md`](testing/resolver-evals/SKILL.md) |

### Infrastructure

| Trigger | Skill |
|---|---|
| Databricks workspace, jobs, DLT, Delta, Unity Catalog, Photon, liquid clustering | [`infrastructure/databricks/SKILL.md`](infrastructure/databricks/SKILL.md) |
| Unity Catalog permissioning specifics (standalone) | [`infrastructure/unity-catalog/SKILL.md`](infrastructure/unity-catalog/SKILL.md) |

## Disambiguation rules

1. **Prefer the most specific skill.** `coderabbit-response` beats `code-review` when a bot posted the review. `python-exceptions` beats general `python` when the task is `except` refactoring.
2. **Skills chain explicitly.** `create-pr` → `commit` → `branch` in reverse. Each skill's Phases section states predecessors.
3. **Conventions always apply.** Every skill that writes a commit reads `_output-rules.md` first. Every skill that touches tabular identifiers reads `_data-trust-rules.md` first.
4. **Router sub-skills load only when triggered.** A `.py` file without `pyspark` imports doesn't load `coding/spark/`; ambient loading is off.
5. **When in doubt, ask the user.**

## Classification refresher (from `meta/skillbuilder/SKILL.md`)

| Classification | Frontmatter key | Invocation |
|---|---|---|
| Reference | `user-invocable: false` | Auto-loaded by Claude when context matches |
| Router | `user-invocable: false` + `paths:` | Structural — dispatches to sub-skills |
| Action | `disable-model-invocation: true` + `allowed-tools:` | User runs `/skill-name` |
| Analytical | `disable-model-invocation: true` + `allowed-tools: Read Grep Glob` | User runs `/skill-name` for a read-only audit |

## Attribution Policy

NEVER include AI or agent attribution in code, commits, or documentation. Enforced by `_output-rules.md`.
