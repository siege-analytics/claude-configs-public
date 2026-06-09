# Skill Resolver

This is the top-level dispatcher. Skills live under category directories. **Read the skill file before acting.** If two skills could match, read both -- they chain.

## Conventions (apply to everything)

| File | Purpose |
|---|---|
| [rule:output] | Commit trailers, attribution policy, docstring minimums, markdown style -- shared across all skills that write anything |
| [rule:data-trust] | Default assumption: tabular data lies. Validate at boundaries. -- applied before any spatial / identifier work |
| [rule:principles] | Clean Code maxims (naming, function size, error handling) -- always-on for any code task |
| [rule:python] | Effective Python idioms -- applied when touching `*.py` |
| [rule:jvm] | Effective Java + Effective Kotlin merged -- applied when touching JVM languages, including Scala on Spark |
| [rule:typescript] | Effective TypeScript idioms -- applied when touching `*.ts` / `*.tsx` |
| [rule:rust] | Rust idioms -- applied when touching `*.rs` |
| [rule:siege-utilities] | Prefer `siege_utilities` for utility-shaped problems before writing a new helper. If `siege_utilities` almost solves it but doesn't, consider a PR upstream. |
| [rule:definition-of-done] | Five hard criteria plus one opt-in for "done": code-reviewed, edge cases explored, tests written, ticket updated, ticket exists, KB delta validated. Behavior changes are not finished until all five mandatory criteria pass. |
| [rule:knowledge-base] | Knowledge-base consultation discipline -- read before claiming, tag every assumption, update on contradiction, silence is a finding. Applied when the project declares `knowledge_base:` in PROJECT.md. |
| [rule:robustness] | Robust Python (Viafore) -- type safety, invariant enforcement, fail fast, constrain mutability. Applied when writing or reviewing Python code. |
| [rule:architecture-patterns] | Architecture Patterns with Python (Percival & Gregory) -- repository pattern, service layer, dependency inversion. Applied when designing service layers or data-access boundaries. |
| [rule:property-testing] | Hypothesis property-testing patterns -- strategies, round-trip/invariant/oracle properties. Applied when writing tests for functions with numeric, string, or collection inputs. |
| [rule:scipy-spec] | Scientific Python SPECs 0, 4, 6 -- version support, deprecation timelines, lazy loading. Applied when managing dependency versions or API lifecycle in library packages. |
| [rule:packaging] | PyPA Packaging Guide -- pyproject.toml, dependency spec, version management. Applied when modifying pyproject.toml, managing dependencies, or publishing packages. |
| [rule:security-scanning] | Bandit/OWASP security standards -- injection prevention, credential handling, TLS, serialization safety. Applied when writing code that handles user input, credentials, shell commands, or network requests. |
| [rule:testing-frameworks] | Test framework declaration and enforcement -- projects declare frameworks per layer in PROJECT.md; agents use the declared frameworks; `test-guard.sh` verifies test evidence at push time. Applied when writing tests or choosing a test runner. |

## Routing table

### Coding

| Trigger | Skill |
|---|---|
| Writing or reviewing any `.py`, `.sql`, `.ts`, `.go`, `.tsx`, `.jsx` | [skill:coding] router |
| "Review this PR", "review this diff" | [skill:code-review] |
| Library code architecture -- DRY, dataclass discipline, interface integrity, runtime types | [skill:python-patterns] |
| "Why is this try/except too broad?", silent-failure patterns, `except Exception: pass` | [skill:python-exceptions] |
| Django models, views, forms, migrations, settings | [skill:django] |
| Data pipeline, scheduled job, Rundeck YAML, Airflow DAG | [skill:pipeline-jobs] |
| PySpark DataFrame work, tuning, shuffle / skew | [skill:spark] |
| Scala on Spark / Databricks (`.scala`, `%scala`, `Dataset[T]`) | [skill:scala-on-spark] |
| SQL query structure, joins, window functions, Postgres performance | [skill:sql] |
| PostGIS -- ST_* functions, spatial indexes, spatial joins | [skill:postgis] |
| GeoPandas + Shapely -- `import geopandas`, `gpd.`, `.sjoin`, raw `from shapely.geometry import` | [skill:geopandas] |
| Apache Sedona -- `from sedona`, `SedonaContext`, ST_* in Spark SQL, `%scala` Sedona | [skill:sedona] |
| DuckDB-spatial -- `import duckdb` + `INSTALL spatial` / `LOAD spatial` / `ST_Read` (single-node SQL on Parquet, GDAL-less) | [skill:duckdb-spatial] |
| QML component review -- properties-in / signals-out, MuseScore plugins, Qt Quick decomposition | [skill:qml-component-review] |
| Auditing error-path test coverage, writing-tests:5 compliance | [skill:test-coverage-audit] |
| Choosing a test framework, declaring test layers in PROJECT.md, test-guard enforcement | [skill:testing-frameworks] |
| Fix a bug or issue identified by code review / audit / static analysis | [skill:think] Step 1 sibling-grep gate is MANDATORY. The audit finding is a hypothesis, not an investigation. The ticket must state: (a) the sibling-set from grep, (b) a falsification criterion per [skill:evaluate-ticket] criterion 6, (c) the test that goes red on revert. Without these three, the fix is untested speculation that happened to compile. |

### Analysis

| Trigger | Skill |
|---|---|
| Geospatial data -- pick engine + GDAL-availability path, cross-engine principles | [skill:spatial] (router; dispatches to `coding/{postgis,geopandas,sedona,duckdb-spatial}/`) |
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
| Ensure a ticket destination exists before non-trivial work | [skill:ticket-guard] |

### Session

| Trigger | Skill |
|---|---|
| CodeRabbit or other bot review on a PR | [skill:coderabbit-response] |
| Inline PR discussion threads | [skill:pr-comments] |
| End-of-session summary, close the loop | [skill:wrap-up] |
| "Drive while I'm gone," "monitor X overnight," any continuous-cadence handoff longer than a typical turn | [skill:drive-while-away] -- sibling of `[rule:writing-prose]` writing-prose:5; the rule says "use a mechanism," this skill says "which mechanism for which cadence" and mandates the same-turn `ScheduleWakeup` call. |

### Planning

| Trigger | Skill |
|---|---|
| Create a Linear / Jira / GitHub issue | [skill:create-ticket] |
| Update ticket status | [skill:update-ticket] |
| Close a ticket | [skill:close-ticket] |
| "What should I work on next?", opportunity surfacing | `im-feeling-lucky` (planned) |
| Starting work on a ticket -- claim it, mark in-progress, branch, then code | [skill:pre-work-check] |
| Create ≥2 tickets in one session (epic breakdown, audit findings, batch triage) | [skill:create-ticket] + [skill:evaluate-ticket] per ticket. **Test-before-bulk applies:** create the first ticket, run `evaluate-ticket`, fix gaps until it PASSes, THEN continue to the next. Each ticket is an independent act of investigation, not a line item in a list. |
| Making or recognizing a strategic decision (scope, architecture, deferral, standing approval, completion claim) | [skill:decision-to-ticket] -- fires in real time during work, not at PR time. Consumes the destination configured by [skill:ticket-guard]. |

### Documentation

| Trigger | Skill |
|---|---|
| Central docs consolidation across repos | [skill:cascading-documentation] |

### Thinking

| Trigger | Skill |
|---|---|
| Break down a problem, decision framework | [skill:think] |
| Consulting project knowledge base, tagging assumptions against docs, updating KB on contradiction | [skill:knowledge-base] |

### Meta

| Trigger | Skill |
|---|---|
| "Create a skill", "audit skills", "fix this skill" | [skill:skillbuilder] |
| "Is every skill reachable from the resolver?" | `check-resolvable` (planned) |
| "Test that the right skill fires for each input" | `resolver-evals` (planned) |

### Shelves (book-derived libraries)

DBrain book-skill library. Each shelf is itself a router -- load the shelf, it tells you which book to read in full. See [skill:shelves--shelves] for the meta-router.

| Trigger | Shelf |
|---|---|
| Engineering practice question, code review rationale, refactoring justification | [skill:shelves--engineering-principles] |
| Distributed system design, storage engine choice, replication, scaling | [skill:shelves--systems-architecture] |
| Language-specific idiom or best practice (Python, JVM, TS, Rust) | [skill:shelves--languages] |
| Data pipeline design, scheduled-job patterns, batch/stream | [skill:shelves--data-and-pipelines] |
| Product discovery, feature scoping, JTBD, user research | [skill:shelves--product] |
| Marketing copy, conversion, positioning messaging | [skill:shelves--marketing] |
| Sales motion, pricing, negotiation | [skill:shelves--sales] |
| Strategy, market entry, competitive positioning | [skill:shelves--strategy] |
| UI/UX design, visual hierarchy, typography, microinteractions | [skill:shelves--design] |
| Team motivation, ways of working, organizational practice | [skill:shelves--team] |
| Communicating data, presenting findings, animation in slides | [skill:shelves--storytelling] |

> **Status:** shelves are added incrementally via the `feat/dbrain-*` PR stack. Rows above pointing at not-yet-merged shelf files will resolve as PRs land.

### Infrastructure

| Trigger | Skill |
|---|---|
| Databricks workspace, jobs, DLT, Delta, Unity Catalog, Photon, liquid clustering | [skill:databricks] |
| Unity Catalog permissioning specifics (standalone) | [skill:unity-catalog] |
| Operating shared infra -- cyberpower, K8s, Rundeck -- process and concurrency limits | [skill:ops] |

## Project-specific rules and skills

Some repositories have project-specific rules and skills that supplement (and can override) the general set. Project source lives under `projects/<project-slug>/` in this repo; when published, **project skills and rules are prefix-flattened so the slug fully encodes the project** (no shadowing, no per-context disambiguation). See [`projects/CONTRIBUTING.md`](../projects/CONTRIBUTING.md) for the authoring convention.

### Naming convention (prefix-flatten)

| Source path | Flat slug | Flat file |
|---|---|---|
| `projects/<project>/skills/<skill>/SKILL.md` | `<project>--<skill>` | `skills/<project>--<skill>/SKILL.md` |
| `projects/<project>/_rules.md` | `<project>--rules` | `skills/_<project>--rules.md` |
| `projects/<project>/PROJECT.md` | (not a routing target) | `projects/<project>/PROJECT.md` |

Tokens use the prefixed slug directly: `[skill:siege-utilities--hostile-review]`, `[rule:siege-utilities-]`.

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
| `siege-utilities` | `siege-analytics/siege_utilities` | [rule:siege-utilities-] | [skill:siege-utilities--hostile-review], [skill:siege-utilities--notebook-impact], [skill:siege-utilities--error-path-tests] |

### siege-utilities-specific routing

These triggers apply only when the working directory matches `siege-analytics/siege_utilities`.

| Trigger | Skill |
|---|---|
| Any PR or code review in siege_utilities | [skill:siege-utilities--hostile-review] |
| Any change to a function signature, return type, or exception contract | [skill:siege-utilities--notebook-impact] |
| Adding or backfilling error-path tests, SU-4b compliance | [skill:siege-utilities--error-path-tests] |
| Auditing error-path test coverage for any module | [skill:test-coverage-audit] |
| `except Exception: pass` or `except: pass` anywhere | Bug -- see [rule:siege-utilities-] (SU-1) |
| Function returns empty DataFrame/list/dict/string on error path | Bug -- see [rule:siege-utilities-] (SU-1) |
| Code under `examples/` or `notebooks/` | Held to library standard -- see [rule:siege-utilities-] (SU-3) |

## Universal pre-action checks

These skills fire automatically before non-trivial work, regardless of which routing entry matched. They are gates, not destinations.

| Check | Skill | When it fires |
|---|---|---|
| Branch correctness | [skill:develop-guard] | Before any branch creation or merge that touches `develop` / `main` |
| Ticket destination exists | [skill:ticket-guard] | Before non-trivial work begins (once per session, memoized). Ensures strategic decisions have a durable, human-visible home. |
| Strategic decisions surfaced | [skill:decision-to-ticket] | When making scope, architecture, sequencing, deferral, standing approval, or completion claim decisions. Fires in real time during work, not at session end. Includes a completion guard that prevents scope-reduction rationalization. |
| Evidentiary fact-finding | [skill:investigate] | After think Step 7 approves, before implementation begins. Required for any work that touches existing entities, modifies data flow, or changes downstream behavior. Produces a Fact Sheet artifact with file:line citations. **Mechanically enforced**: `investigate-gate-guard.sh` blocks implementation writes when think-gate exists but investigate-gate does not. Level 2 spot-checks file:line citations. Self-review enforces artifact reference at push time (v1.3). For transformation code (SQL, DataFrame pipelines), Level 3 requires `Pre-ship-dry-run:` trailer with behavioral verification evidence (#255, #275). |
| Adversarial risk classification | [skill:pre-mortem] | After investigate completes, before implementation begins. Classifies failure scenarios as Tiger/Paper Tiger/Elephant. Launch-Blocking Tigers halt implementation. Self-review enforces artifact reference at push time (v1.3). |

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
