---
name: survey-context
description: "Author-time entity-shape verification through documentation. Before writing or modifying code that references existing entities (models, tables, functions, files, APIs, env vars), consult the project's entity docs, diff the live model against what the docs say, and surface drift as a finding. Shape changes in code carry a Definition-of-Done requirement to update the corresponding doc page. Composes with `think` Step 1 (Context) and the static scanner."
user-invocable: true
allowed-tools: Read Grep Glob Bash
---

# Survey Context Before Writing

Before you write or modify code that touches existing entities, **consult the entity's doc page first**, **diff what's there against the live model**, and **update the doc when your change alters shape**. Docs are the canonical record of entity shape; the survey is the moment when drift surfaces; the work that follows includes keeping the docs honest.

This is the counterpart to the static scanner: the scanner catches code-vs-model drift at write time; this skill catches doc-vs-model drift at author time and prevents both from accumulating.

## Why

A recurring failure shape: code references entities — imports, model fields, table columns, function names, env vars — that don't exist or have a different shape than the author assumed. The reference looks plausible. CI doesn't exercise the path. The bug ships.

Without a canonical doc layer, every author re-pays the introspection cost on every task, and drift between author-mental-model and reality goes undetected until it ships. With a doc layer, the survey becomes a cheap diff against committed truth, and drift becomes a tracked finding instead of a per-task surprise.

Observed instances grounding this skill (writing-claims:6, N≥9):

- `assign_boundaries.py` referenced `models.Q(...)` without importing `models`.
- `swh/census.py` imported `PostGISConnector` from a non-existent module.
- `dimension_loader.py` called `DimTime.objects.update_or_create(defaults={...})` with 6 keys that aren't fields on DimTime.
- `dimension_loader.py` did the same for `DimRedistrictingCycle`.
- `boundary_detail` applied class-based-view decorator shape on a function-based DRF view.
- A reviewer declared `DemographicSnapshot.object_id` was an integer PK without checking; it's a CharField geoid-key.

## When to survey

Required before:
- Adding a new caller of an existing model, function, or table.
- Changing the shape (signature, schema, field set) of any entity with callers elsewhere.
- Wiring a new endpoint, command, or job to existing infrastructure.
- Writing a decorator, mixin, or generic-FK reference.

Trivial-change escape: pure typographical, docs, or single-line literal changes do not require a survey.

## The loop

```
        +-----------------------------+
        |  Entity docs (canonical)    |
        |  e.g. /docs/entities/*.md   |
        +--------------+--------------+
                       |
        consult        |        update (if work changed shape)
                       v
+---------------+  +--------------------+  +------------------+
| Task touches  |->| Survey artifact    |->| DoD: doc touched |
| entity X      |  | = diff(docs, model)|  | iff shape changed|
+---------------+  +----------+---------+  +------------------+
                              |
                              | drift detected (docs != model)
                              v
                  +---------------------------+
                  |  Drift finding / ticket   |
                  +---------------------------+
```

Three outcomes per entity touched:

- **Match.** Live introspection agrees with docs. Survey notes the consult; task proceeds.
- **Drift.** Live introspection disagrees with docs. Survey records a Drift finding; operator decides whether the doc is wrong (update) or the model is wrong (fix).
- **No doc page.** Skill offers to seed one from live introspection; task proceeds with a Survey-Seed deliverable that updates the project's entity catalog.

## Project-skill contract

The global skill defines the loop. **Each project provides the local layer** at `.agents/skills/survey-context/`:

```
<repo>/.agents/skills/survey-context/
  config.md              <- entity catalog, doc root, conventions
  templates/entity.md    <- doc-page template
  entities/<name>.md     <- per-entity doc pages (the canonical record)
  recipes/<class>.md     <- project-specific surveyor recipes (optional)
```

`config.md` must declare:
- **Doc root** — where entity pages live (absolute repo path).
- **Entity catalog** — list of entities tracked (name, type, doc-page path).
- **Ownership** — who reviews drift findings.
- **Recipe extensions** — project-specific surveyor recipes beyond the universal set.

If `.agents/skills/survey-context/` does not exist in the project, the skill falls back to v1 behavior: produce a per-task Survey artifact from live introspection only, no doc-consult / no DoD enforcement. A consult-warning is emitted so the operator knows the project hasn't adopted the doc layer.

See `PROJECT_SKILL_TEMPLATE.md` for the project-layer skeleton.

## Survey artifact format

```
## Survey
Task: <one-line description>
Project skill: <path-to-project-config-or-"none-(v1-fallback)">
Touched entities: <list>
Referenced entities: <list>

### Entity: <name> (<type>, <namespace>)
- Doc page: <path-to-doc-or-"none-(will-seed)">
- Live introspection at: <timestamp> via <command-or-tool>
- Diff vs docs: MATCH | DRIFT | NO-DOC
- If DRIFT: <what disagrees; doc-say vs model-say>
- ASSUMPTIONS my task makes about this entity: <named explicitly>
- VERIFICATION STATUS: VERIFIED | ASSUMED | UNKNOWN

### Drift findings
For each DRIFT: doc location, what's stale, recommended owner action.
Each drift gets a ticket (or named decision to defer) before the task proceeds.

### Doc updates required
For each shape-changing modification in this task: doc page that must be
updated in the same PR (or sibling PR with an explicit link).
```

## Surveyor recipes (universal)

Each entity class has a canonical introspection. Project skills extend this set.

| Entity class | Surveyor |
|---|---|
| Django model | `Model._meta.get_fields()`; field-type via `_meta.get_field("name").get_internal_type()` |
| Django decorator shape | function- vs class-based view; method_decorator(name="dispatch") only applies to classes |
| Database table | `\d+` (psql); `SHOW CREATE TABLE` (mysql); INFORMATION_SCHEMA |
| Spark DataFrame | `df.printSchema()`, `df.explain()`, `df.rdd.getNumPartitions()` |
| Spark catalog table | `spark.catalog.listColumns(tableName)` |
| Python function/class | Read source; `inspect.signature`; grep callers |
| Python module/import | `python -c "import X; print(X.__file__)"`; grep `__all__` |
| File on disk | `ls -la`, `head`, `wc -l`, `file` |
| HTTP API | WebFetch / curl + response shape, status, headers |
| Environment variable | grep config + dump from target environment |
| FK / cross-app reference | `_meta.get_fields()` filtered to ForeignKey types |
| ContentType / generic FK | Check `object_id` field type — int PK vs string-keyed differ in semantics |

## Definition of Done (shape-change → doc-touch)

When the work changes entity shape (adds/removes/renames a field; changes a function signature; alters a decorator shape that callers rely on), the same PR must update the corresponding entity doc page.

The companion hook (`survey-context.sh`, see Known Limitations) enforces this when present. Without the hook the rule is operator-auditable: the Survey artifact's "Doc updates required" section names what must change; the PR's diff is checked against that list at self-review time.

## Composition with existing primitives

- **`brain-first` universal check** — this skill IS its full expansion for entity shape.
- **`think` Step 1 (Context)** — survey systematizes Step 1 with per-entity recipes + a doc-consult step.
- **writing-code:4 (verify symbol exists)** — survey batches across all symbols a task references.
- **writing-code:5 (no hypothetical code)** — runtime version; survey is the static / pre-write counterpart.
- **self-review `Goal source:` field** — survey populates it.
- **scan_ast.py Django ORM check** — runtime enforcement of the field-name shape; survey is the author-time complement that also catches doc drift.

## Hard parts (acknowledged)

- **Doc-layer bootstrap cost.** N existing entities × hand-written doc page is a real one-time cost. Mitigation: skill's no-doc → seed path lets coverage grow organically; a separate bootstrap tool can mass-seed from introspection.
- **Doc-rot.** Without the shape-change → doc-touch DoD enforced by hook, docs decay. The skill makes the requirement visible; the hook (v2.1 follow-up) makes it enforced.
- **Coverage gap.** A survey of entities X, Y, Z doesn't catch that W is also load-bearing. Mitigation: the artifact's "Referenced entities" field forces enumeration.
- **Survey paralysis.** Exhaustive survey kills throughput. Mitigation: depth heuristics — DEEP for touched entities (full doc + introspection + diff), SHALLOW for referenced (doc citation only), SKIP for transitively-pulled-in dependencies that the diff doesn't engage.
- **Recipe staleness.** Surveyor recipes for Spark 3 vs 4, Django 4 vs 5 differ. Universal recipes live in this skill; project-specific recipes live in the project skill's `recipes/`.

## Hard rules

**No survey = no write** for non-trivial entity-touching work. The Survey artifact's existence is the floor.

**Drift is not invisible.** A DRIFT outcome must produce a ticket or a named-and-justified decision to defer. Silent drift is a writing-claims:5 violation.

**Shape change = doc change.** When work changes entity shape, the doc page is updated in the same PR (or a sibling PR with an explicit link). No PR opened with stale docs on touched entities.

**Project-skill absence is noisy.** When `.agents/skills/survey-context/` is missing, the skill emits a consult-warning and runs v1-fallback. Don't silently degrade — the operator should know the project hasn't adopted the doc layer.

## Trigger conditions

- Always-on for non-trivial work that touches existing entities (same gate as `think`).
- Triggered by entity-naming in the task description.
- Operator-invokable as `/survey-context`.

## v2.2: optional Watched paths (evidence-collection minimal)

Entity doc pages may declare an optional `**Watched paths:**` field listing glob patterns (relative to repo root, backtick-quoted, comma-separated). When the pushed diff touches a file matching any of these patterns, the same doc-touch DoD applies as for the Definition file. Use this to extend protection to important callers, sibling modules, or related infrastructure that doesn't live at the entity's Definition.

Format:

```
**Definition:** `socialwarehouse/warehouse/models/dimensions.py:218`
**Watched paths:** `socialwarehouse/warehouse/services/dimension_loader*.py`, `socialwarehouse/warehouse/migrations/*.py`
```

Globs use bash's `case`-pattern syntax (`*` `?` `[]`; no `**`). Per-pattern backtick-quoted; the parser walks the line and extracts every `pattern` token. Order does not matter. Empty / missing field → no watched paths, v2.1 behavior unchanged.

v2.2 is an **evidence-collection minimal** — operator-curated glob patterns rather than mechanical caller-discovery. The BLOCK message distinguishes `[v2.1 definition-file match]` from `[v2.2 watched-path match]` so the firing log can separate the two trigger families. Use v2.2 firings over the next several sessions to evaluate whether caller-side enforcement is justified at higher coverage, or whether the file-based shape is the right ceiling.

Carve-outs for v2.2 watched paths:
- Patterns are operator-declared per-entity. No automatic caller discovery.
- Test files / generated files / vendored code can be excluded by simply not listing them.
- No AST awareness. Touching the file in any way (including unrelated edits to other functions in the same file) counts as a watched-path touch. Bigger granularity tradeoff than file-based mechanical detection would require if v2.3 brings it.

## Known limitations

- **Hook enforcement** for v2.1 (definition-file match) shipped at `hooks/git/survey-context.sh`. v2.2 extends the same hook with Watched-path glob matching as of this skill's v2.2 revision.
- **Caller-side enforcement coverage** is bounded by what operators put in Watched paths. v2.3 (symbol-based AST detection) is deferred until evidence from v2.2 firings either justifies the broader scope or argues it would over-cover.
- **Bootstrap tool deferred.** Mass-seeding entity docs from introspection across a repo is its own scope, filed separately.
- **Drift-ticket auto-filing deferred.** Currently the survey records drift; the operator files the ticket manually. Future tooling can auto-file.
- **Doc-page rendering / search deferred.** Docs are plain markdown; readable in repo. A search UI is not in scope.
