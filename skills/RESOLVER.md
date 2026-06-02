# Skill Resolver

This is the top-level dispatcher. Skills live under category directories. **Read the skill file before acting.** If two skills could match, read both -- they chain.

## Conventions (apply to everything)

| File | Purpose |
|---|---|
| [`output`](_output-rules.md) | Commit trailers, attribution policy, docstring minimums, markdown style -- shared across all skills that write anything |
| [`data-trust`](_data-trust-rules.md) | Default assumption: tabular data lies. Validate at boundaries. -- applied before any spatial / identifier work |
| [`principles`](_principles-rules.md) | Clean Code maxims (naming, function size, error handling) -- always-on for any code task |
| [`python`](_python-rules.md) | Effective Python idioms -- applied when touching `*.py` |
| [`jvm`](_jvm-rules.md) | Effective Java + Effective Kotlin merged -- applied when touching JVM languages, including Scala on Spark |
| [`typescript`](_typescript-rules.md) | Effective TypeScript idioms -- applied when touching `*.ts` / `*.tsx` |
| [`rust`](_rust-rules.md) | Rust idioms -- applied when touching `*.rs` |
| [`siege-utilities`](_siege-utilities-rules.md) | Prefer `siege_utilities` for utility-shaped problems before writing a new helper. If `siege_utilities` almost solves it but doesn't, consider a PR upstream. |
| [`definition-of-done`](_definition-of-done-rules.md) | Five hard criteria for "done": code-reviewed, edge cases explored, tests written, ticket updated, ticket exists. Behavior changes are not finished until all five pass. |
| [`robustness`](_robustness-rules.md) | Robust Python (Viafore) -- type safety, invariant enforcement, fail fast, constrain mutability. Applied when writing or reviewing Python code. |
| [`architecture-patterns`](_architecture-patterns-rules.md) | Architecture Patterns with Python (Percival & Gregory) -- repository pattern, service layer, dependency inversion. Applied when designing service layers or data-access boundaries. |
| [`property-testing`](_property-testing-rules.md) | Hypothesis property-testing patterns -- strategies, round-trip/invariant/oracle properties. Applied when writing tests for functions with numeric, string, or collection inputs. |
| [`scipy-spec`](_scipy-spec-rules.md) | Scientific Python SPECs 0, 4, 6 -- version support, deprecation timelines, lazy loading. Applied when managing dependency versions or API lifecycle in library packages. |
| [`packaging`](_packaging-rules.md) | PyPA Packaging Guide -- pyproject.toml, dependency spec, version management. Applied when modifying pyproject.toml, managing dependencies, or publishing packages. |
| [`security-scanning`](_security-scanning-rules.md) | Bandit/OWASP security standards -- injection prevention, credential handling, TLS, serialization safety. Applied when writing code that handles user input, credentials, shell commands, or network requests. |

## Routing table

### Coding

| Trigger | Skill |
|---|---|
| Writing or reviewing any `.py`, `.sql`, `.ts`, `.go`, `.tsx`, `.jsx` | [`coding`](coding/SKILL.md) router |
| "Review this PR", "review this diff" | [`code-review`](code-review/SKILL.md) |
| Library code architecture -- DRY, dataclass discipline, interface integrity, runtime types | [`python-patterns`](python-patterns/SKILL.md) |
| "Why is this try/except too broad?", silent-failure patterns, `except Exception: pass` | [`python-exceptions`](python-exceptions/SKILL.md) |
| Django models, views, forms, migrations, settings | [`django`](django/SKILL.md) |
| Data pipeline, scheduled job, Rundeck YAML, Airflow DAG | [`pipeline-jobs`](pipeline-jobs/SKILL.md) |
| PySpark DataFrame work, tuning, shuffle / skew | [`spark`](spark/SKILL.md) |
| Scala on Spark / Databricks (`.scala`, `%scala`, `Dataset[T]`) | [`scala-on-spark`](scala-on-spark/SKILL.md) |
| SQL query structure, joins, window functions, Postgres performance | [`sql`](sql/SKILL.md) |
| PostGIS -- ST_* functions, spatial indexes, spatial joins | [`postgis`](postgis/SKILL.md) |
| GeoPandas + Shapely -- `import geopandas`, `gpd.`, `.sjoin`, raw `from shapely.geometry import` | [`geopandas`](geopandas/SKILL.md) |
| Apache Sedona -- `from sedona`, `SedonaContext`, ST_* in Spark SQL, `%scala` Sedona | [`sedona`](sedona/SKILL.md) |
| DuckDB-spatial -- `import duckdb` + `INSTALL spatial` / `LOAD spatial` / `ST_Read` (single-node SQL on Parquet, GDAL-less) | [`duckdb-spatial`](duckdb-spatial/SKILL.md) |
| QML component review -- properties-in / signals-out, MuseScore plugins, Qt Quick decomposition | [`qml-component-review`](qml-component-review/SKILL.md) |
| Auditing error-path test coverage, writing-tests:5 compliance | [`test-coverage-audit`](test-coverage-audit/SKILL.md) |
| Fix a bug or issue identified by code review / audit / static analysis | [`think`](think/SKILL.md) Step 1 sibling-grep gate is MANDATORY. The audit finding is a hypothesis, not an investigation. The ticket must state: (a) the sibling-set from grep, (b) a falsification criterion per [`evaluate-ticket`](evaluate-ticket/SKILL.md) criterion 6, (c) the test that goes red on revert. Without these three, the fix is untested speculation that happened to compile. |

### Analysis

| Trigger | Skill |
|---|---|
| Geospatial data -- pick engine + GDAL-availability path, cross-engine principles | [`spatial`](spatial/SKILL.md) (router; dispatches to `coding/{postgis,geopandas,sedona,duckdb-spatial}/`) |
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
| Ensure a ticket destination exists before non-trivial work | [`ticket-guard`](ticket-guard/SKILL.md) |

### Session

| Trigger | Skill |
|---|---|
| CodeRabbit or other bot review on a PR | [`coderabbit-response`](coderabbit-response/SKILL.md) |
| Inline PR discussion threads | [`pr-comments`](pr-comments/SKILL.md) |
| End-of-session summary, close the loop | [`wrap-up`](wrap-up/SKILL.md) |
| "Drive while I'm gone," "monitor X overnight," any continuous-cadence handoff longer than a typical turn | [`drive-while-away`](drive-while-away/SKILL.md) -- sibling of `[`writing-prose`](_writing-prose-rules.md)` writing-prose:5; the rule says "use a mechanism," this skill says "which mechanism for which cadence" and mandates the same-turn `ScheduleWakeup` call. |

### Planning

| Trigger | Skill |
|---|---|
| Create a Linear / Jira / GitHub issue | [`create-ticket`](create-ticket/SKILL.md) |
| Update ticket status | [`update-ticket`](update-ticket/SKILL.md) |
| Close a ticket | [`close-ticket`](close-ticket/SKILL.md) |
| "What should I work on next?", opportunity surfacing | `im-feeling-lucky` (planned) |
| Starting work on a ticket -- claim it, mark in-progress, branch, then code | [`pre-work-check`](pre-work-check/SKILL.md) |
| Create ≥2 tickets in one session (epic breakdown, audit findings, batch triage) | [`create-ticket`](create-ticket/SKILL.md) + [`evaluate-ticket`](evaluate-ticket/SKILL.md) per ticket. **Test-before-bulk applies:** create the first ticket, run `evaluate-ticket`, fix gaps until it PASSes, THEN continue to the next. Each ticket is an independent act of investigation, not a line item in a list. |
| Making or recognizing a strategic decision (scope, architecture, deferral, standing approval, completion claim) | [`decision-to-ticket`](decision-to-ticket/SKILL.md) -- fires in real time during work, not at PR time. Consumes the destination configured by [`ticket-guard`](ticket-guard/SKILL.md). |

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

DBrain book-skill library. Each shelf is itself a router -- load the shelf, it tells you which book to read in full. See [`shelves`](shelves/SKILL.md) for the meta-router.

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
| Operating shared infra -- cyberpower, K8s, Rundeck -- process and concurrency limits | [`ops`](ops/SKILL.md) |

## Project-specific rules and skills

Some repositories have project-specific rules and skills that supplement (and can override) the general set. Project source lives under `projects/<project-slug>/` in this repo; when published, **project skills and rules are prefix-flattened so the slug fully encodes the project** (no shadowing, no per-context disambiguation). See [`projects/CONTRIBUTING.md`](../projects/CONTRIBUTING.md) for the authoring convention.

### Naming convention (prefix-flatten)

| Source path | Flat slug | Flat file |
|---|---|---|
| `projects/<project>/skills/<skill>/SKILL.md` | `<project>--<skill>` | `skills/<project>--<skill>/SKILL.md` |
| `projects/<project>/_rules.md` | `<project>--rules` | `skills/_<project>--rules.md` |
| `projects/<project>/PROJECT.md` | (not a routing target) | `projects/<project>/PROJECT.md` |

Tokens use the prefixed slug directly: `[`siege-utilities--hostile-review`](siege-utilities--hostile-review/SKILL.md)`, `[`siege-utilities--rules`](_siege-utilities--rules.md)`.

### Precedence model

Items marked **[build-enforced]** are validated by `bin/build.py`. Items marked **[convention]** are author-discipline; the build cannot check them.

1. **Routing entries are conditional.** [convention] The agent only invokes a `<project>--<skill>` skill when the routing entry that references it is in scope -- typically when the working directory matches the project's `repo:` field. The build validates that token references resolve to existing slugs, but cannot validate trigger semantics.
2. **No implicit shadowing.** [build-enforced] A project skill with the same base name as a general skill (e.g., `projects/siege-utilities/skills/self-review/` and `skills/<category>/self-review/`) produces two distinct flat slugs (`siege-utilities--self-review` and `self-review`). The build rejects collisions between project and general slugs. Which one fires is set by the routing entry, not by precedence rules at load time.
3. **Weakening overrides must be declared.** [convention] If a project rule weakens a general rule (permits something the general rule prohibits), it must appear in the project's Overrides table in `_rules.md`. An undeclared weakening is void -- the general rule wins. The build cannot detect semantic weakening; this is enforced at PR review.
4. **No cross-project inheritance.** [convention] Project B cannot reference or import Project A's rules. Each project is a self-contained overlay on the general set.
5. **Scope is repo-bound.** [convention] Project rules and the conditional routing entries below activate when the working directory matches the `repo` field in `PROJECT.md`. The build validates that `repo:` is present and unique across projects, but does not verify that the repo exists or that the working directory matches at runtime. The prefixed slugs remain visible in the catalog regardless -- they're addressable but not invoked out of scope.

### Active projects

| Project | Repo | Rules | Skills |
|---|---|---|---|
| `siege-utilities` | `siege-analytics/siege_utilities` | [`siege-utilities--rules`](_siege-utilities--rules.md) | [`siege-utilities--hostile-review`](siege-utilities--hostile-review/SKILL.md), [`siege-utilities--notebook-impact`](siege-utilities--notebook-impact/SKILL.md), [`siege-utilities--error-path-tests`](siege-utilities--error-path-tests/SKILL.md) |

### siege-utilities-specific routing

These triggers apply only when the working directory matches `siege-analytics/siege_utilities`.

| Trigger | Skill |
|---|---|
| Any PR or code review in siege_utilities | [`siege-utilities--hostile-review`](siege-utilities--hostile-review/SKILL.md) |
| Any change to a function signature, return type, or exception contract | [`siege-utilities--notebook-impact`](siege-utilities--notebook-impact/SKILL.md) |
| Adding or backfilling error-path tests, SU-4b compliance | [`siege-utilities--error-path-tests`](siege-utilities--error-path-tests/SKILL.md) |
| Auditing error-path test coverage for any module | [`test-coverage-audit`](test-coverage-audit/SKILL.md) |
| `except Exception: pass` or `except: pass` anywhere | Bug -- see [`siege-utilities--rules`](_siege-utilities--rules.md) (SU-1) |
| Function returns empty DataFrame/list/dict/string on error path | Bug -- see [`siege-utilities--rules`](_siege-utilities--rules.md) (SU-1) |
| Code under `examples/` or `notebooks/` | Held to library standard -- see [`siege-utilities--rules`](_siege-utilities--rules.md) (SU-3) |

## Universal pre-action checks

These skills fire automatically before non-trivial work, regardless of which routing entry matched. They are gates, not destinations.

| Check | Skill | When it fires |
|---|---|---|
| Branch correctness | [`develop-guard`](develop-guard/SKILL.md) | Before any branch creation or merge that touches `develop` / `main` |
| Ticket destination exists | [`ticket-guard`](ticket-guard/SKILL.md) | Before non-trivial work begins (once per session, memoized). Ensures strategic decisions have a durable, human-visible home. |
| Strategic decisions surfaced | [`decision-to-ticket`](decision-to-ticket/SKILL.md) | When making scope, architecture, sequencing, deferral, standing approval, or completion claim decisions. Fires in real time during work, not at session end. Includes a completion guard that prevents scope-reduction rationalization. |
| Evidentiary fact-finding | [`investigate`](investigate/SKILL.md) | After think Step 7 approves, before implementation begins. Required for any work that touches existing entities, modifies data flow, or changes downstream behavior. Produces a Fact Sheet artifact with file:line citations. **Mechanically enforced**: `investigate-gate-guard.sh` blocks implementation writes when think-gate exists but investigate-gate does not. Level 2 spot-checks file:line citations. Self-review enforces artifact reference at push time (v1.3). For transformation code (SQL, DataFrame pipelines), Level 3 requires `Pre-ship-dry-run:` trailer with behavioral verification evidence (#255, #275). |
| Adversarial risk classification | [`pre-mortem`](pre-mortem/SKILL.md) | After investigate completes, before implementation begins. Classifies failure scenarios as Tiger/Paper Tiger/Elephant. Launch-Blocking Tigers halt implementation. Self-review enforces artifact reference at push time (v1.3). |

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
| Router | `user-invocable: false` + `paths:` | Structural -- dispatches to sub-skills |
| Action | `disable-model-invocation: true` + `allowed-tools:` | User runs `/skill-name` |
| Analytical | `disable-model-invocation: true` + `allowed-tools: Read Grep Glob` | User runs `/skill-name` for a read-only audit |

## Attribution Policy

NEVER include AI or agent attribution in code, commits, or documentation. Enforced by `_output-rules.md`.
