---
name: solutions-catalog
description: "Create and maintain entries in the solutions/ catalog. Each solved problem gets a searchable entry with YAML frontmatter (category, tags, severity, ticket) and a structured body (Problem, Root cause, Solution, Prevention). Invoked after successful merges, post-error-revisions, and lessons-learned promotions."
---

# Solutions Catalog

This skill governs creation and maintenance of entries in the
`solutions/` catalog at the root of claude-configs-public. The catalog
makes universal check #2 (brain-first) mechanically enforceable by
giving agents a structured, greppable knowledge base of solved problems.

## When to create an entry

Create a solutions entry when:

1. **Post-merge success compounding** — A PR merges that solved a
   non-trivial problem. The solution, its root cause, and the
   prevention mechanism are worth recording for future agents.

2. **Post-error-revision** — A `## Post-error revision` block
   documents a falsified assumption and its correction. The
   correction is a solved problem.

3. **Distill-lessons promotion** — A `LESSONS.md` entry is promoted
   to a Tier 2 or Tier 3 rule. The promotion creates a catalog entry
   alongside the rule.

4. **Manual** — The operator or agent identifies a solved problem not
   captured by the above paths.

Do NOT create entries for:
- Problems that are still open or only partially solved
- Pure style or formatting fixes
- Ticket-specific context with no reusable lesson

## Entry format

File: `solutions/<slug>.md`

Slug: lowercase, hyphenated, descriptive. Derived from the problem,
not the ticket number. Examples: `verify-before-execute`,
`concurrent-build-race`, `load-verify-published-artifact`.

### YAML frontmatter (required)

```yaml
---
title: Short problem description (matches the slug's intent)
category: <one of the taxonomy below>
tags: [freeform, keywords, for, grep, discovery]
ticket: owner/repo#NNN
date: YYYY-MM-DD
severity: S1 | S2 | S3 | enhancement
source: lessons-learned | post-error-revision | post-merge | manual
---
```

**Required fields:** title, category, date, severity

**Optional fields:** ticket (default N/A), tags (default []),
source (default manual)

### Body (required sections)

```markdown
## Problem
<1-3 sentences: what went wrong or what was needed>

## Root cause
<Why it happened — the structural gap, not the proximate trigger>

## Solution
<What was done — specific PR, commit, config change>

## Prevention
<What prevents recurrence — rule, hook, gate, convention>
```

## Category taxonomy

| Category | Scope |
|---|---|
| `conventions` | Process, workflow, commit, PR conventions |
| `data-integrity` | Data shape, schema, validation, ETL |
| `packaging-truth` | Build, publish, distribution, import |
| `pipeline-operations` | CI/CD, hooks, enforcement, automation |
| `spatial-domain` | Geospatial, CRS, boundaries, geocoding |
| `architecture-patterns` | Design, abstraction, composition |
| `security-issues` | Credentials, injection, access control |
| `performance-issues` | Latency, memory, scaling |

New categories require updating this skill AND `solutions/README.md`
AND the `VALID_CATEGORIES` list in `bin/build.py`. Ad-hoc directory
creation is not allowed — the taxonomy is a controlled vocabulary.

## Build validation

`bin/build.py` validates all `solutions/*.md` files (excluding
README.md) during both build and `--check` mode:

- YAML frontmatter is present and parseable
- Required fields (title, category, date, severity) are non-empty
- Category is in the taxonomy
- Severity is one of: S1, S2, S3, enhancement
- Date matches YYYY-MM-DD format

Validation failures are `BuildError`s that block the build.

## Discovery

The investigate skill Phase 0 requires:

```bash
grep -ri <keywords> solutions/
```

with 2-3 domain terms from the task. If a match is found, the
existing entry's Solution and Prevention sections inform the
investigation — the agent does not re-derive what was already
documented.
