---
name: coding-standards
description: "Coding conventions. TRIGGER: writing Python, SQL, PySpark, Django, pipeline jobs, Rundeck YAML, or Go. Routes to the language-specific guide."
user-invocable: false
paths: "**/*.py,**/*.sql,**/*.ts,**/*.tsx,**/*.js,**/*.jsx,**/*.go"
---

# Coding Standards Router

Select and apply the appropriate coding guide based on file type and framework.

## Routing Table

| Signal | Sub-Skill | Path |
|--------|-----------|------|
| `*.py` with Django imports (`from django`, `django.`) | Django conventions | [skill:django] |
| `*.py` with PySpark imports (`from pyspark`, `import pyspark`) | PySpark patterns | [skill:spark] |
| `*.py` (general) | Python style | [skill:python] |
| `*.py` library code, especially on re-review / CR feedback touching architecture | Python engineering patterns (DRY, dataclass discipline, interface integrity, runtime types) | [skill:python-patterns] |
| `try`/`except` on screen, silent-failure patterns, `except Exception: pass` | Python exception discipline | [skill:python-exceptions] |
| `*.sql` or SQL in Python strings | SQL conventions | [skill:sql] |
| SQL with `ST_*` functions, `geometry` / `geography` columns, PostGIS extension | PostGIS patterns | [skill:postgis] |
| `*.ts`, `*.tsx` | TypeScript style | [skill:typescript] |
| `*.tsx`, `*.jsx` with React imports | React patterns | [skill:react] |
| `*.go` | Go conventions | [skill:go] |
| `*.py` with pipeline/fetch/job/schedule context, Rundeck YAML, Airflow DAGs | Pipeline job pattern | [skill:pipeline-jobs] |

Not all sub-skills exist yet. If a routing table entry points to a file that doesn't exist, skip it and apply general best practices for that language.

## Rules

1. **Load only what is needed.** A plain Python file loads only `python/SKILL.md`. Do not load spark, django, or sql unless their imports are present.
2. **Stack when appropriate.** A PySpark file loads both `python/SKILL.md` (general style) and `spark/SKILL.md` (Spark-specific). A Django file loads `python/SKILL.md` + `django/SKILL.md`. SQL embedded in Python loads the relevant Python sub-skill + `sql/SKILL.md`. PostGIS SQL loads `sql/SKILL.md` + `postgis/SKILL.md`. Library-code review loads `python/SKILL.md` + `python-patterns/SKILL.md` + optionally `python-exceptions/SKILL.md`.
3. **Specificity wins.** When a framework sub-skill and the general language sub-skill conflict, the framework sub-skill takes precedence.
4. **Reference files load on demand.** Each sub-skill may have a `reference.md`. Load it only when the sub-skill directs you to consult it for the current task.
5. **Conventions always apply.** Every skill that writes a commit reads `_output-rules.md` first (at skills root).
6. **Tests and docs ship with code.** Regardless of language, every PR that changes code also ships tests for the change and updates user-facing documentation (README, docs tree, CHANGELOG, or module guide) when public behavior changes. No "tests coming later" and no "docs coming later" PRs. See the language-specific sub-skill for format conventions and [rule:definition-of-done] for the full done criteria.

## Gotchas

- A `.py` file in a Django project is not necessarily Django code. Check imports, not directory structure.
- SQL embedded in Python f-strings should trigger SQL conventions, but the Python file itself still follows Python style.
- PySpark SQL (SparkSQL) follows the sql sub-skill for query structure but the spark sub-skill for DataFrame operations.
- `*.js` files may be plain JavaScript or a framework. Without React/Vue/Angular imports, apply only general conventions.
- TypeScript and JavaScript share many patterns but TypeScript has additional type-system conventions. Don't apply TypeScript rules to `.js` files.
- `python-patterns` and `python-exceptions` are reviewer's lenses, not default style. Load them when doing architectural review or triaging CodeRabbit findings, not for every `.py` file.
