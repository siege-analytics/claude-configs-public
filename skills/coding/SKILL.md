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
| `*.py` with Django imports (`from django`, `django.`) | Django conventions | [django/SKILL.md](django/SKILL.md) |
| `*.py` with PySpark imports (`from pyspark`, `import pyspark`) | PySpark patterns | [spark/SKILL.md](spark/SKILL.md) |
| `*.py` (general) | Python style | [python/SKILL.md](python/SKILL.md) |
| `*.sql` or SQL in Python strings | SQL conventions | [sql/SKILL.md](sql/SKILL.md) |
| `*.ts`, `*.tsx` | TypeScript style | [typescript/SKILL.md](typescript/SKILL.md) |
| `*.tsx`, `*.jsx` with React imports | React patterns | [react/SKILL.md](react/SKILL.md) |
| `*.go` | Go conventions | [go/SKILL.md](go/SKILL.md) |
| `*.py` with pipeline/fetch/job/schedule context, Rundeck YAML, Airflow DAGs | Pipeline job pattern | [pipeline-jobs/SKILL.md](pipeline-jobs/SKILL.md) |

Not all sub-skills exist yet. If a routing table entry points to a file that doesn't exist, skip it and apply general best practices for that language.

## Rules

1. **Load only what is needed.** A plain Python file loads only `python/SKILL.md`. Do not load spark, django, or sql unless their imports are present.
2. **Stack when appropriate.** A PySpark file loads both `python/SKILL.md` (general style) and `spark/SKILL.md` (Spark-specific). A Django file loads `python/SKILL.md` + `django/SKILL.md`. SQL embedded in Python loads the relevant Python sub-skill + `sql/SKILL.md`.
3. **Specificity wins.** When a framework sub-skill and the general language sub-skill conflict, the framework sub-skill takes precedence.
4. **Reference files load on demand.** Each sub-skill may have a `reference.md`. Load it only when the sub-skill directs you to consult it for the current task.

## Gotchas

- A `.py` file in a Django project is not necessarily Django code. Check imports, not directory structure.
- SQL embedded in Python f-strings should trigger SQL conventions, but the Python file itself still follows Python style.
- PySpark SQL (SparkSQL) follows the sql sub-skill for query structure but the spark sub-skill for DataFrame operations.
- `*.js` files may be plain JavaScript or a framework. Without React/Vue/Angular imports, apply only general conventions.
- TypeScript and JavaScript share many patterns but TypeScript has additional type-system conventions. Don't apply TypeScript rules to `.js` files.
