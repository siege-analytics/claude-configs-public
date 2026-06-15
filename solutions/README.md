# Solutions Catalog

Searchable catalog of solved problems. Each entry documents a problem,
its root cause, the solution, and the prevention mechanism. Future
sessions discover prior solutions via `grep -r <keyword> solutions/`.

This catalog enforces universal check #2 (brain-first): check if we
have the answer already before re-deriving it. The investigate skill
Phase 0 requires grepping this directory before starting fresh
investigation.

## Entry schema

Each `.md` file (excluding this README) has YAML frontmatter:

```yaml
---
title: Short problem description
category: one-of-taxonomy
tags: [freeform, keywords, for, grep]
ticket: owner/repo#NNN
date: YYYY-MM-DD
severity: S1 | S2 | S3 | enhancement
source: lessons-learned | post-error-revision | post-merge | manual
---
```

**Required fields:** title, category, date, severity

**Optional fields:** ticket (default: N/A), tags (default: []),
source (default: manual)

## Body format

```markdown
## Problem
<1-3 sentences describing what went wrong or what was needed>

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

New categories require a skill update (not ad-hoc creation). The
`bin/build.py` validator enforces the taxonomy.

## When entries are created

- **Post-merge success compounding** (#422) — after a successful
  PR merge, the agent creates an entry if the work solved a
  non-trivial problem
- **Post-error-revision** — when a post-error-revision block
  documents a falsified assumption and its correction
- **Distill-lessons promotion** — when a LESSONS.md entry is
  promoted to Tier 2/3, the catalog entry is created alongside
- **Manual** — operator or agent creates an entry for a solved
  problem not captured by the above paths
