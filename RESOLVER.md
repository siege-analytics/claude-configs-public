# Skill Resolver

**You MUST consult this resolver as the first step of any non-trivial task.** When a task pattern below matches what you're about to do, READ the mapped skill(s) before proceeding. Not after. Not "I know what it says." Read.

This is the enforcement layer for every skill in this collection and the electinfo collection. Skills are only useful if they fire before action.

---

## Trivial vs. Non-Trivial

**Trivial** — no skill consultation required:
- Read-only: search, grep, read, list, explain
- Single-file, single-line reversible edits (undone by `git restore`)
- Exploratory questions / analysis with no file writes
- Draft content not yet committed

**Non-trivial** — resolver must be consulted, appropriate skill invoked:
- Any `git commit`, `git push`, branch create/delete, merge, rebase, reset
- Any write to data files, schemas, Hydra configs, Pydantic models, Parquet/Delta
- Code file writes touching public APIs, imports, or library interfaces
- Ticket creation, PR creation, issue updates, any external API write
- Infrastructure changes: K8s, Airflow DAGs, Rundeck YAML, Spark CRDs
- Documentation writes spanning multiple repos
- Session wrap-up / end-of-session actions

**Rule:** if it cannot be undone with `git restore` or `rm`, it is non-trivial. All commits are
non-trivial — diff size does not matter.

---

## THE FIRST GATE: `think`

> **The most important skill in this entire chain is `think`.** Every catalog-bypass, every premature cutover, every half-designed pipeline this resolver exists to prevent traces back to acting before thinking.

Before ANY of the following, you MUST read `skills/thinking/think/SKILL.md` and produce a written design note:

- Implementing a new feature
- Refactoring existing code
- Changing architecture (new layer, new catalog, new data path, new integration)
- Making a cutover (moving Consumer / production traffic to a new source)
- Proposing a schema change
- Building a new skill, hook, or enforcement mechanism (yes, including this resolver itself)
- Any task estimated > 30 minutes

**Explicit exemptions** (from `think` skill): trivial fixes, following step-by-step instructions from the user, research/read-only work, non-code tasks.

The `think` gate is not a pattern-match entry below — it is the **first gate**. Every other pattern in this resolver assumes `think` has already fired.

---

## How to use

1. **`think` first** if the task has architectural or blast-radius implications (see above).
2. Scan the task patterns below.
3. If any pattern matches, `cat` the mapped SKILL.md and read it in full.
4. If multiple patterns match, read all of them.
5. Only then take the action.
6. If no pattern matches but the action has non-trivial blast radius (data writes, mutations to shared systems, infra changes), consult the **universal checks** at the bottom.

---

## electinfo Workspace Overrides

These rules take precedence over anything in individual skill files:

1. **Git remotes:** Always use HTTPS with `${GITHUB_PERSONAL_ACCESS_TOKEN}`. Never SSH. See `[skill:git]`.
2. **Ticket creation:** Use `[skill:qaticket]` — defaults to adam@elect.info assignee, Engineering team, QA label. The generic `planning/create-ticket` skill is a fallback only for non-Linear/non-GitHub platforms.
3. **No AI attribution:** No `Co-Authored-By`, no bot markers, no tool credits anywhere in commits, tickets, or docs.

### electinfo-specific routing

| Trigger | Skill |
|---|---|
| Editing `rundeck/jobs/fec-enterprise/*.yaml` | `enterprise-spark-jobs/SKILL.md` + `git-workflow/commit/SKILL.md` |
| Spark executor OOM, exit code 52, memory tuning | `enterprise-spark-jobs/SKILL.md` |
| Debugging or retrieving a Rundeck execution log | `rundeck-logs/SKILL.md` |
| Posting comments to Linear or GitHub issues | `adammode/SKILL.md` (prepends `From adam@elect.info:`) |
| Creating a ticket in Linear or GitHub | `qaticket/SKILL.md` |
| Any Delta/Parquet write to S3 bronze/silver/gold | `infrastructure/unity-catalog/SKILL.md` |
| PostGIS queries, spatial joins, ST_* functions | `coding/postgis/SKILL.md` + `analysis/spatial/SKILL.md` |
| Session end, committing work | `session/wrap-up/SKILL.md` + `git-workflow/commit/SKILL.md` |

---

## Task patterns → required skills

### Data, catalogs, storage

| About to… | Read first |
|---|---|
| Write Delta/Parquet/Iceberg to any path | `skills/infrastructure/unity-catalog/SKILL.md` |
| Use `.write.save(...)`, `.write.parquet(...)`, or any raw-path write | `skills/infrastructure/unity-catalog/SKILL.md` |
| Use `saveAsTable(...)` | `skills/infrastructure/unity-catalog/SKILL.md` |
| Register a table in Hive Metastore or Unity Catalog | `skills/infrastructure/unity-catalog/SKILL.md` |
| Touch `s3a://hive-warehouse/*`, `s3://silver/*`, `s3://gold/*`, or any shared bucket | `skills/infrastructure/unity-catalog/SKILL.md` |
| Run a batch data processing job | `electinfo_claude_skills/skills/pipeline-guard/SKILL.md` |
| Schedule a recurring pipeline job | `skills/coding/pipeline-jobs/SKILL.md` + `electinfo_claude_skills/skills/rundeck-job/SKILL.md` |

### Writing code

| About to… | Read first |
|---|---|
| Write Python | `skills/coding/SKILL.md` → `skills/coding/python/SKILL.md` |
| Write SQL (Postgres/PostGIS/SparkSQL) | `skills/coding/SKILL.md` → `skills/coding/sql/SKILL.md` |
| Write PySpark / use DataFrame API / write to Delta | `skills/coding/SKILL.md` → `skills/coding/spark/SKILL.md` + `skills/infrastructure/unity-catalog/SKILL.md` |
| Write a pipeline / ETL / scheduled data job | `skills/coding/pipeline-jobs/SKILL.md` |
| Write a Rundeck job YAML | `electinfo_claude_skills/skills/rundeck-job/SKILL.md` |
| Review existing code (yours or others') | `skills/coding/code-review/SKILL.md` |
| Write Scala on Databricks notebooks, `.scala` files, `Dataset[T]` Spark code | `skills/coding/scala-on-spark/SKILL.md` (delegates to `shelves/languages/effective-java/`, `effective-kotlin/`, and `coding/spark/`) |
| Design a service / module boundary | `skills/thinking/think/SKILL.md` (gate) → `skills/shelves/engineering-principles/clean-architecture/SKILL.md` |
| Pick a storage engine, replication scheme, or partitioning strategy | `skills/thinking/think/SKILL.md` (gate) → `skills/shelves/systems-architecture/data-intensive/SKILL.md` |

### Design & planning

| About to… | Read first |
|---|---|
| Implement a new feature, refactor, or architecture change | `skills/thinking/think/SKILL.md` (MANDATORY before any code) |
| Do spatial / geographic analysis | `skills/analysis/SKILL.md` → `skills/analysis/spatial/SKILL.md` |
| Do statistical / graph / entity-resolution / text analysis | `skills/analysis/SKILL.md` |

### Git & tickets

| About to… | Read first |
|---|---|
| Create a git branch | `skills/git-workflow/branch/SKILL.md` + `skills/git-workflow/develop-guard/SKILL.md` |
| Create a commit | `skills/git-workflow/commit/SKILL.md` |
| Merge a branch | `skills/git-workflow/merge/SKILL.md` |
| Open a pull request | `skills/git-workflow/create-pr/SKILL.md` |
| Triage / respond to PR comments | `skills/session/pr-comments/SKILL.md` |
| Create a ticket | `skills/planning/create-ticket/SKILL.md` |
| Update a ticket (progress comment, field change) | `skills/planning/update-ticket/SKILL.md` |
| Close a ticket | `skills/planning/close-ticket/SKILL.md` |
| Start work on a ticket (first commit, mark In Progress, assign to self) | `skills/planning/pre-work-check/SKILL.md` |

### Documentation

| About to… | Read first |
|---|---|
| Write or update docs in any repo | `skills/documentation/cascading-documentation/SKILL.md` |
| Author a Notion page | `skills/documentation/notion-knowledge-base/SKILL.md` |
| Administer the elect-info Notion workspace | `electinfo_claude_skills/skills/notion-sync-admin/SKILL.md` |
| Consolidate / deduplicate documentation | `skills/maintenance/consolidate/SKILL.md` |

### Session & operations

| About to… | Read first |
|---|---|
| End a session / hand off work | `skills/session/wrap-up/SKILL.md` |
| Recover from a magnum / enterprise-runner outage | `electinfo_claude_skills/skills/monitor-magnum/SKILL.md` |
| Create a new skill | `skills/meta/skillbuilder/SKILL.md` |

---

## Universal pre-action checks (always apply)

These fire for every non-trivial action, regardless of whether a pattern above matched:

0. **THINK FIRST** (the non-negotiable gate): for anything beyond a trivial mechanical change, read `skills/thinking/think/SKILL.md` and write a design note. If you can't state what you're about to do, why, what could go wrong, and what the rollback looks like — you are not ready to act. Every serious failure in this session traces back to skipping this.

1. **Catalog-first**: if the action touches data that lives under a catalog (Unity Catalog, Hive Metastore), go through the catalog. Never write raw paths to bucket locations the catalog manages. Confirm the table's registered location BEFORE writing.

2. **Brain-first** (borrowed from GBrain): before calling any external API or running any mutation, check if we have the answer / target already. Re-use before recreating.

3. **Test-before-bulk**: any batch operation (≥20 items) runs on 3–5 items first, verifies, then scales.

4. **Ticket-required + Epic-in-project + Dependency-clear**: Any work that creates a change in state or behavior of the software that will impact the product requires a ticket. Typographical corrections with no functional effect are exempt. That ticket must belong to a project or epic — unprojected tickets are not worked. All blocking upstream tickets must be Done before you start. Include the ticket reference in every commit. Read `skills/planning/pre-work-check/SKILL.md` before starting any such work.

5. **Branch-correct**: you are on a feature branch, not main / master / develop, for any write.

6. **Dual-mirror check** (for dual-tracked repos electinfo↔gitlab): after acting on one side, mirror to the other.

7. **No-attribution**: never add Claude/AI attribution to commits, PRs, or public-facing content.

8. **Measure twice, cut once**: for destructive or irreversible actions (drops, deletes, force-push, hard-reset), confirm scope first.

---

## What if nothing matches?

If you're doing something truly novel that no skill covers, default to:

1. **Read `skills/thinking/think/SKILL.md`** and write a brief design note.
2. **Confirm with the user** before acting if blast radius is non-trivial.
3. **File a skill-creation task** if this turns out to be a recurring pattern — see `skills/meta/skillbuilder/SKILL.md`.

---

## Enforcement

This resolver is surfaced into every session via:

- **Session start**: referenced from every project's CLAUDE.md.
- **Every user turn**: injected via `UserPromptSubmit` hook (`hooks/resolver/inject-resolver.sh`) so it stays in active context.
- **Pre-tool-use**: `PreToolUse` hooks on `Bash` match dangerous catalog/data-write patterns and block with a STOP-read-skill reminder (`hooks/infrastructure/catalog-guard.sh`).

Skills collection paths (all relative to their repo roots):

- **Siege (this repo)**: `~/git/electinfo/claude-configs-public/skills/`
- **Electinfo**: `~/git/electinfo/electinfo_claude_skills/skills/` (includes a subtree of siege skills under `skills/siege/` plus electinfo-specific skills at the top level)

---

## Disambiguation rules

1. **Prefer the most specific skill.** `coderabbit-response` beats `code-review` when a bot posted the review.
2. **Skills chain explicitly.** `create-pr` → `commit` → `branch` in reverse.
3. **Conventions always apply.** Every skill that writes a commit reads `_output-rules.md` first.
4. **Router sub-skills load only when triggered.** A `.py` file without `pyspark` imports doesn't load `coding/spark/`.
5. **When in doubt, ask the user.**
