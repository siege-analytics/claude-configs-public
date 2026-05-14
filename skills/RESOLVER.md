# Skill Resolver

This is the top-level dispatcher. Skills live under category directories. **Read the skill file before acting.** If two skills could match, read both — they chain.

## Conventions (apply to everything)

| File | Purpose |
|---|---|
| [`output`](_output-rules.md) | Commit trailers, attribution policy, docstring minimums, markdown style — shared across all skills that write anything |
| [`data-trust`](_data-trust-rules.md) | Default assumption: tabular data lies. Validate at boundaries. — applied before any spatial / identifier work |
| [`principles`](_principles-rules.md) | Clean Code maxims (naming, function size, error handling) — always-on for any code task |
| [`python`](_python-rules.md) | Effective Python idioms — applied when touching `*.py` |
| [`jvm`](_jvm-rules.md) | Effective Java + Effective Kotlin merged — applied when touching JVM languages, including Scala on Spark |
| [`typescript`](_typescript-rules.md) | Effective TypeScript idioms — applied when touching `*.ts` / `*.tsx` |
| [`rust`](_rust-rules.md) | Rust idioms — applied when touching `*.rs` |
| [`siege-utilities`](_siege-utilities-rules.md) | Prefer `siege_utilities` for utility-shaped problems before writing a new helper. If `siege_utilities` almost solves it but doesn't, consider a PR upstream. |
| [`definition-of-done`](_definition-of-done-rules.md) | Five hard criteria for "done": code-reviewed, edge cases explored, tests written, ticket updated, ticket exists. Behavior changes are not finished until all five pass. |

## Routing table

### Coding

| Trigger | Skill |
|---|---|
| Writing or reviewing any `.py`, `.sql`, `.ts`, `.go`, `.tsx`, `.jsx` | [`coding`](coding/SKILL.md) router |
| "Review this PR", "review this diff" | [`code-review`](code-review/SKILL.md) |
| Library code architecture — DRY, dataclass discipline, interface integrity, runtime types | [`python-patterns`](python-patterns/SKILL.md) |
| "Why is this try/except too broad?", silent-failure patterns, `except Exception: pass` | [`python-exceptions`](python-exceptions/SKILL.md) |
| Django models, views, forms, migrations, settings | [`django`](django/SKILL.md) |
| Data pipeline, scheduled job, Rundeck YAML, Airflow DAG | [`pipeline-jobs`](pipeline-jobs/SKILL.md) |
| PySpark DataFrame work, tuning, shuffle / skew | [`spark`](spark/SKILL.md) |
| Scala on Spark / Databricks (`.scala`, `%scala`, `Dataset[T]`) | [`scala-on-spark`](scala-on-spark/SKILL.md) |
| SQL query structure, joins, window functions, Postgres performance | [`sql`](sql/SKILL.md) |
| PostGIS — ST_* functions, spatial indexes, spatial joins | [`postgis`](postgis/SKILL.md) |
| GeoPandas + Shapely — `import geopandas`, `gpd.`, `.sjoin`, raw `from shapely.geometry import` | [`geopandas`](geopandas/SKILL.md) |
| Apache Sedona — `from sedona`, `SedonaContext`, ST_* in Spark SQL, `%scala` Sedona | [`sedona`](sedona/SKILL.md) |
| DuckDB-spatial — `import duckdb` + `INSTALL spatial` / `LOAD spatial` / `ST_Read` (single-node SQL on Parquet, GDAL-less) | [`duckdb-spatial`](duckdb-spatial/SKILL.md) |
| QML component review — properties-in / signals-out, MuseScore plugins, Qt Quick decomposition | [`qml-component-review`](qml-component-review/SKILL.md) |

### Analysis

| Trigger | Skill |
|---|---|
| Geospatial data — pick engine + GDAL-availability path, cross-engine principles | [`spatial`](spatial/SKILL.md) (router; dispatches to `coding/{postgis,geopandas,sedona,duckdb-spatial}/`) |
| Statistical modeling, regression, hypothesis tests | `analysis/statistical/SKILL.md` (if present) |
| Graph / network analysis, entity relationships | `analysis/graph/SKILL.md` (if present) |
| Record linkage, dedup, fuzzy matching | `analysis/entity-resolution/SKILL.md` (if present) |
| NLP, text classification, extraction | `analysis/nlp/SKILL.md` (if present) |

### Maintenance

| Trigger | Skill |
|---|---|
| Renaming a public function, changing a default, dropping a column | [`library-api-evolution`](library-api-evolution/SKILL.md) |
| Redundant docs across repos, "same thing in five places" | [`consolidate`](consolidate/SKILL.md) |

### Git workflow

| Trigger | Skill |
|---|---|
| Create a new branch | [`branch`](branch/SKILL.md) |
| Commit changes | [`commit`](commit/SKILL.md) |
| Open a PR | [`create-pr`](create-pr/SKILL.md) |
| Merge a PR | [`merge`](merge/SKILL.md) |
| Protect `develop` / `main` | [`develop-guard`](develop-guard/SKILL.md) |

### Session

| Trigger | Skill |
|---|---|
| CodeRabbit or other bot review on a PR | [`coderabbit-response`](coderabbit-response/SKILL.md) |
| Inline PR discussion threads | [`pr-comments`](pr-comments/SKILL.md) |
| End-of-session summary, close the loop | [`wrap-up`](wrap-up/SKILL.md) |

### Planning

| Trigger | Skill |
|---|---|
| Create a Linear / Jira / GitHub issue | [`create-ticket`](create-ticket/SKILL.md) |
| Update ticket status | [`update-ticket`](update-ticket/SKILL.md) |
| Close a ticket | [`close-ticket`](close-ticket/SKILL.md) |
| "What should I work on next?", opportunity surfacing | `im-feeling-lucky` (planned) |
| Starting work on a ticket — claim it, mark in-progress, branch, then code | [`pre-work-check`](pre-work-check/SKILL.md) |

### Documentation

| Trigger | Skill |
|---|---|
| Central docs consolidation across repos | [`cascading-documentation`](cascading-documentation/SKILL.md) |
| Notion knowledge base | [`notion-knowledge-base`](notion-knowledge-base/SKILL.md) |

### Thinking

| Trigger | Skill |
|---|---|
| Break down a problem, decision framework | [`think`](think/SKILL.md) |

### Meta

| Trigger | Skill |
|---|---|
| "Create a skill", "audit skills", "fix this skill" | [`skillbuilder`](skillbuilder/SKILL.md) |
| "Is every skill reachable from the resolver?" | `check-resolvable` (planned) |
| "Test that the right skill fires for each input" | `resolver-evals` (planned) |

### Shelves (book-derived libraries)

DBrain book-skill library. Each shelf is itself a router — load the shelf, it tells you which book to read in full. See [`shelves`](shelves/SKILL.md) for the meta-router.

| Trigger | Shelf |
|---|---|
| Engineering practice question, code review rationale, refactoring justification | [`engineering-principles`](shelves/engineering-principles/SKILL.md) |
| Distributed system design, storage engine choice, replication, scaling | [`systems-architecture`](shelves/systems-architecture/SKILL.md) |
| Language-specific idiom or best practice (Python, JVM, TS, Rust) | [`languages`](shelves/languages/SKILL.md) |
| Data pipeline design, scheduled-job patterns, batch/stream | [`data-and-pipelines`](shelves/data-and-pipelines/SKILL.md) |
| Product discovery, feature scoping, JTBD, user research | [`product`](shelves/product/SKILL.md) |
| Marketing copy, conversion, positioning messaging | [`marketing`](shelves/marketing/SKILL.md) |
| Sales motion, pricing, negotiation | [`sales`](shelves/sales/SKILL.md) |
| Strategy, market entry, competitive positioning | [`strategy`](shelves/strategy/SKILL.md) |
| UI/UX design, visual hierarchy, typography, microinteractions | [`design`](shelves/design/SKILL.md) |
| Team motivation, ways of working, organizational practice | [`team`](shelves/team/SKILL.md) |
| Communicating data, presenting findings, animation in slides | [`storytelling`](shelves/storytelling/SKILL.md) |

> **Status:** shelves are added incrementally via the `feat/dbrain-*` PR stack. Rows above pointing at not-yet-merged shelf files will resolve as PRs land.

### Infrastructure

| Trigger | Skill |
|---|---|
| Databricks workspace, jobs, DLT, Delta, Unity Catalog, Photon, liquid clustering | [`databricks`](databricks/SKILL.md) |
| Unity Catalog permissioning specifics (standalone) | [`unity-catalog`](unity-catalog/SKILL.md) |
| Operating shared infra — cyberpower, K8s, Rundeck — process and concurrency limits | [`ops`](ops/SKILL.md) |

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
