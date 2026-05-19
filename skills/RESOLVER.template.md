# Skill Resolver

This is the top-level dispatcher. Skills live under category directories. **Read the skill file before acting.** If two skills could match, read both — they chain.

## Conventions (apply to everything)

| File | Purpose |
|---|---|
| [rule:output] | Commit trailers, attribution policy, docstring minimums, markdown style — shared across all skills that write anything |
| [rule:data-trust] | Default assumption: tabular data lies. Validate at boundaries. — applied before any spatial / identifier work |
| [rule:principles] | Clean Code maxims (naming, function size, error handling) — always-on for any code task |
| [rule:python] | Effective Python idioms — applied when touching `*.py` |
| [rule:jvm] | Effective Java + Effective Kotlin merged — applied when touching JVM languages, including Scala on Spark |
| [rule:typescript] | Effective TypeScript idioms — applied when touching `*.ts` / `*.tsx` |
| [rule:rust] | Rust idioms — applied when touching `*.rs` |
| [rule:siege-utilities] | Prefer `siege_utilities` for utility-shaped problems before writing a new helper. If `siege_utilities` almost solves it but doesn't, consider a PR upstream. |
| [rule:definition-of-done] | Five hard criteria for "done": code-reviewed, edge cases explored, tests written, ticket updated, ticket exists. Behavior changes are not finished until all five pass. |

## Routing table

### Coding

| Trigger | Skill |
|---|---|
| Writing or reviewing any `.py`, `.sql`, `.ts`, `.go`, `.tsx`, `.jsx` | [skill:coding] router |
| "Review this PR", "review this diff" | [skill:code-review] |
| Library code architecture — DRY, dataclass discipline, interface integrity, runtime types | [skill:python-patterns] |
| "Why is this try/except too broad?", silent-failure patterns, `except Exception: pass` | [skill:python-exceptions] |
| Django models, views, forms, migrations, settings | [skill:django] |
| Data pipeline, scheduled job, Rundeck YAML, Airflow DAG | [skill:pipeline-jobs] |
| PySpark DataFrame work, tuning, shuffle / skew | [skill:spark] |
| Scala on Spark / Databricks (`.scala`, `%scala`, `Dataset[T]`) | [skill:scala-on-spark] |
| SQL query structure, joins, window functions, Postgres performance | [skill:sql] |
| PostGIS — ST_* functions, spatial indexes, spatial joins | [skill:postgis] |
| GeoPandas + Shapely — `import geopandas`, `gpd.`, `.sjoin`, raw `from shapely.geometry import` | [skill:geopandas] |
| Apache Sedona — `from sedona`, `SedonaContext`, ST_* in Spark SQL, `%scala` Sedona | [skill:sedona] |
| DuckDB-spatial — `import duckdb` + `INSTALL spatial` / `LOAD spatial` / `ST_Read` (single-node SQL on Parquet, GDAL-less) | [skill:duckdb-spatial] |
| QML component review — properties-in / signals-out, MuseScore plugins, Qt Quick decomposition | [skill:qml-component-review] |

### Analysis

| Trigger | Skill |
|---|---|
| Geospatial data — pick engine + GDAL-availability path, cross-engine principles | [skill:spatial] (router; dispatches to `coding/{postgis,geopandas,sedona,duckdb-spatial}/`) |
| Statistical modeling, regression, hypothesis tests | `analysis/statistical/SKILL.md` (if present) |
| Graph / network analysis, entity relationships | `analysis/graph/SKILL.md` (if present) |
| Record linkage, dedup, fuzzy matching | `analysis/entity-resolution/SKILL.md` (if present) |
| NLP, text classification, extraction | `analysis/nlp/SKILL.md` (if present) |

### Maintenance

| Trigger | Skill |
|---|---|
| Renaming a public function, changing a default, dropping a column | [skill:library-api-evolution] |
| Redundant docs across repos, "same thing in five places" | [skill:consolidate] |

### Git workflow

| Trigger | Skill |
|---|---|
| Create a new branch | [skill:branch] |
| Commit changes | [skill:commit] |
| Open a PR | [skill:create-pr] |
| Merge a PR | [skill:merge] |
| Protect `develop` / `main` | [skill:develop-guard] |

### Session

| Trigger | Skill |
|---|---|
| CodeRabbit or other bot review on a PR | [skill:coderabbit-response] |
| Inline PR discussion threads | [skill:pr-comments] |
| End-of-session summary, close the loop | [skill:wrap-up] |

### Planning

| Trigger | Skill |
|---|---|
| Create a Linear / Jira / GitHub issue | [skill:create-ticket] |
| Update ticket status | [skill:update-ticket] |
| Close a ticket | [skill:close-ticket] |
| "What should I work on next?", opportunity surfacing | [skill:im-feeling-lucky] |
| Starting work on a ticket — claim it, mark in-progress, branch, then code | [skill:pre-work-check] |

### Documentation

| Trigger | Skill |
|---|---|
| Central docs consolidation across repos | [skill:cascading-documentation] |
| Notion knowledge base | [skill:notion-knowledge-base] |

### Thinking

| Trigger | Skill |
|---|---|
| Break down a problem, decision framework | [skill:think] |

### Meta

| Trigger | Skill |
|---|---|
| "Create a skill", "audit skills", "fix this skill" | [skill:skillbuilder] |
| "Is every skill reachable from the resolver?" | [skill:check-resolvable] |
| "Test that the right skill fires for each input" | [skill:resolver-evals] |

### Shelves (book-derived libraries)

DBrain book-skill library. Each shelf is itself a router — load the shelf, it tells you which book to read in full. See [skill:shelves] for the meta-router.

| Trigger | Shelf |
|---|---|
| Engineering practice question, code review rationale, refactoring justification | [skill:engineering-principles] |
| Distributed system design, storage engine choice, replication, scaling | [skill:systems-architecture] |
| Language-specific idiom or best practice (Python, JVM, TS, Rust) | [skill:languages] |
| Data pipeline design, scheduled-job patterns, batch/stream | [skill:data-and-pipelines] |
| Product discovery, feature scoping, JTBD, user research | [skill:product] |
| Marketing copy, conversion, positioning messaging | [skill:marketing] |
| Sales motion, pricing, negotiation | [skill:sales] |
| Strategy, market entry, competitive positioning | [skill:strategy] |
| UI/UX design, visual hierarchy, typography, microinteractions | [skill:design] |
| Team motivation, ways of working, organizational practice | [skill:team] |
| Communicating data, presenting findings, animation in slides | [skill:storytelling] |

> **Status:** shelves are added incrementally via the `feat/dbrain-*` PR stack. Rows above pointing at not-yet-merged shelf files will resolve as PRs land.

### Infrastructure

| Trigger | Skill |
|---|---|
| Databricks workspace, jobs, DLT, Delta, Unity Catalog, Photon, liquid clustering | [skill:databricks] |
| Unity Catalog permissioning specifics (standalone) | [skill:unity-catalog] |
| Operating shared infra — cyberpower, K8s, Rundeck — process and concurrency limits | [skill:ops] |

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
