---
name: coding-standards
description: "Coding conventions for explicit language/framework work. The executable resolver manifest controls automatic loading; this table is navigation only."
user-invocable: false
---

# Coding Standards Router

Use this as a navigation guide after identifying the language and framework. `catalog/resolver-manifest.json` is the executable authority for automatic selections; a row here alone does not activate a skill. Unknown/ambiguous prompts stay kernel-only until clarified.

## Routing Table

| Signal | Sub-Skill | Path |
|--------|-----------|------|
| `*.py` with Django imports (`from django`, `django.`) | Django conventions | [`django`](../django/SKILL.md) |
| Explicit Django REST Framework (`rest_framework`, DRF) | DRF, Django, Python and coding | [`django-rest-framework`](../django-rest-framework/SKILL.md) + [`django`](../django/SKILL.md) + [`python`](../python/SKILL.md) |
| `*.py` with PySpark imports (`from pyspark`, `import pyspark`) | PySpark patterns | [`spark`](../spark/SKILL.md) |
| `*.py` (general) | Python style | [`python`](../python/SKILL.md) |
| `*.py` library code, especially on re-review / CR feedback touching architecture | Python engineering patterns (DRY, dataclass discipline, interface integrity, runtime types) | [`python-patterns`](../python-patterns/SKILL.md) |
| `try`/`except` on screen, silent-failure patterns, `except Exception: pass` | Python exception discipline | [`python-exceptions`](../python-exceptions/SKILL.md) |
| `*.sql` or SQL in Python strings | SQL conventions | [`sql`](../sql/SKILL.md) |
| SQL with `ST_*` functions, `geometry` / `geography` columns, PostGIS extension | PostGIS patterns | [`postgis`](../postgis/SKILL.md) |
| Explicit TypeScript / `*.ts`, `*.tsx` | TypeScript rule | [`typescript`](../_typescript-rules.md) |
| React / `*.tsx`, `*.jsx` with React context | React patterns | [`react`](../react/SKILL.md) |
| Explicit Vue / Pinia / `*.vue` | Vue patterns | [`vue`](../vue/SKILL.md) |
| Explicit Rust / `*.rs` | Rust rule | [`rust`](../_rust-rules.md) |
| `*.go` | Go conventions | Go guide (not currently a published skill) |
| `*.py` with pipeline/fetch/job/schedule context, Rundeck YAML, Airflow DAGs | Pipeline job pattern | [`pipeline-jobs`](../pipeline-jobs/SKILL.md) |

A rule is not a skill: TypeScript and Rust have rule-only slugs, Vue has a skill-only slug, and Python, React and DRF each have both. `[`react`](../_react-rules.md)` selects `skills/_react-rules.md`; `[`react`](../react/SKILL.md)` selects `skills/react/SKILL.md`. Typed tokens reject the wrong namespace (for example ``rust` (planned)` or ``_vue-rules.md` (planned)`). `/react` and prose routes use the deterministic default skill. Selections expose `source_path`, and both kinds count separately toward the budget when selected together. Do not infer a QML project from this navigation table.

## Rules

1. **Load only what is needed.** A plain Python route selects coding + python. Do not load Spark, Django, or SQL without matching signals.
2. **Stack when appropriate.** A PySpark file loads both `python/SKILL.md` (general style) and `spark/SKILL.md` (Spark-specific). A Django file loads `python/SKILL.md` + `django/SKILL.md`. SQL embedded in Python loads the relevant Python sub-skill + `sql/SKILL.md`. PostGIS SQL loads `sql/SKILL.md` + `postgis/SKILL.md`. Library-code review loads `python/SKILL.md` + `python-patterns/SKILL.md` + optionally `python-exceptions/SKILL.md`.
3. **Specificity wins.** When a framework sub-skill and the general language sub-skill conflict, the framework sub-skill takes precedence.
4. **Reference files load on demand.** Each sub-skill may have a `reference.md`. Load it only when the sub-skill directs you to consult it for the current task.
5. **Conventions always apply.** Every skill that writes a commit reads `_output-rules.md` first (at skills root).
6. **Tests and docs ship with code.** Regardless of language, every PR that changes code also ships tests for the change and updates user-facing documentation (README, docs tree, CHANGELOG, or module guide) when public behavior changes. No "tests coming later" and no "docs coming later" PRs. See the language-specific sub-skill for format conventions and [`definition-of-done`](../_definition-of-done-rules.md) for the full done criteria.

## Gotchas

- A `.py` file in a Django project is not necessarily Django code. Check imports, not directory structure.
- SQL embedded in Python f-strings should trigger SQL conventions, but the Python file itself still follows Python style.
- PySpark SQL (SparkSQL) follows the sql sub-skill for query structure but the spark sub-skill for DataFrame operations.
- `*.js` files may be plain JavaScript or a framework. Without React/Vue/Angular imports, apply only general conventions.
- TypeScript and JavaScript share many patterns but TypeScript has additional type-system conventions. Don't apply TypeScript rules to `.js` files.
- `python-patterns` and `python-exceptions` are reviewer's lenses, not default style. Load them when doing architectural review or triaging CodeRabbit findings, not for every `.py` file.
