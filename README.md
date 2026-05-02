# Claude Code Configurations (Public)

Reusable Claude Code skills and project initialization templates.

For use with [`claude_init`](https://github.com/dheerajchand/siege_analytics_zshrc) or standalone. Pin to a release tag — see [Quick Start](#quick-start).

[![Latest release](https://img.shields.io/github/v/release/siege-analytics/claude-configs-public?label=latest)](https://github.com/siege-analytics/claude-configs-public/releases) [![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## Contents

| Path | Purpose |
|---|---|
| [`RESOLVER.md`](RESOLVER.md) | **Skill resolver** — master index mapping task patterns to required skills. Mandatory first read before any non-trivial action. |
| [`CHANGELOG.md`](CHANGELOG.md) | Release notes by version. |
| `skills/` | Categorized reusable skills for Claude Code sessions. |
| `skills/_*-rules.md` | **Always-on conventions** — applied across every skill that touches code, data, or output. See [Conventions](#always-on-conventions). |
| `skills/shelves/` | **DBrain book-skill library** — book-derived skills (Clean Code, DDIA, Effective Python, etc.) organized into 11 topic shelves. See [DBrain](#dbrain--book-skill-library). |
| `hooks/` | Shell hooks (PreToolUse, UserPromptSubmit) that enforce the resolver. |
| `templates/` | Project templates (CLAUDE.md, settings.local.json). |

## The Skill Resolver

The problem this repo solves: **skills are only useful if they fire before the action they govern.** A catalog of skills the agent *could* consult is worth nothing if the agent doesn't actually read them first.

[`RESOLVER.md`](RESOLVER.md) is a task-pattern → required-skill index. When Claude is about to do something (write Delta data, create a PR, author a ticket, run a spatial join), it scans the resolver, finds the matching row, and reads the mapped `SKILL.md` before acting. If no pattern matches, universal pre-action checks (catalog-first, brain-first, test-before-bulk, ticket-required, etc.) still apply.

**The first gate is [`think`](skills/thinking/think/SKILL.md).** Every catalog-bypass, every premature cutover, every half-designed pipeline the resolver exists to prevent traces back to acting before thinking. The `think` skill is not one pattern among many — it is the mandatory first step before any feature, refactor, architecture change, cutover, or >30-minute task. The rest of the resolver assumes `think` has already fired.

**Inspired by [GBrain](https://github.com/garrytan/gbrain)'s "thin harness, fat skills" pattern** — intelligence lives in the skills, not the runtime. The resolver is the discovery layer; `think` is the gate.

### Enforcement

Three enforcement layers keep the resolver active:

1. **Session start** — every project `CLAUDE.md` references `RESOLVER.md` as the first action of any non-trivial task.
2. **Every user turn** — [`hooks/resolver/inject-resolver.sh`](hooks/resolver/inject-resolver.sh) is a `UserPromptSubmit` hook that injects the resolver summary into active context on every prompt. Context doesn't decay by turn 20.
3. **Pre-tool-use** — [`hooks/infrastructure/catalog-guard.sh`](hooks/infrastructure/catalog-guard.sh) is a `PreToolUse` hook on `Bash` that matches dangerous catalog-bypass patterns and blocks them with a STOP-read-skill reminder.

Wire the hooks by merging [`hooks/settings-snippet.json`](hooks/settings-snippet.json) into `~/.claude/settings.json` (or project `.claude/settings.local.json`), replacing `/path/to/claude-configs-public` with the actual absolute path to this repo.

## Always-on conventions

Files at the root of `skills/` named `_*-rules.md` are loaded by the resolver Conventions table and apply to every relevant skill. They're the always-on policy layer:

| File | Scope | Use when |
|---|---|---|
| [`_output-rules.md`](skills/_output-rules.md) | Commit trailers, attribution policy, docstring minimums, markdown style | Any skill that writes anything |
| [`_data-trust-rules.md`](skills/_data-trust-rules.md) | Default assumption: tabular data lies. Validate at boundaries | Before any spatial / identifier / external-data work |
| [`_principles-rules.md`](skills/_principles-rules.md) | Clean Code maxims (naming, function size, error handling) | Always-on for any code task |
| [`_python-rules.md`](skills/_python-rules.md) | Effective Python idioms | Touching `*.py` |
| [`_jvm-rules.md`](skills/_jvm-rules.md) | Effective Java + Effective Kotlin (merged) | Touching JVM languages, including Scala on Spark |
| [`_typescript-rules.md`](skills/_typescript-rules.md) | Effective TypeScript idioms | Touching `*.ts` / `*.tsx` |
| [`_rust-rules.md`](skills/_rust-rules.md) | Rust idioms | Touching `*.rs` |
| [`_siege-utilities-rules.md`](skills/_siege-utilities-rules.md) | Prefer [`siege_utilities`](https://github.com/siege-analytics/siege_utilities) for utility-shaped problems before writing a new helper. Consider PRs upstream when the gap is generic. | Writing Python utilities |

## Skills

Skills are classified by how they're invoked:

- **Reference** — Knowledge Claude applies automatically when relevant. Not a slash command.
- **Action** — Workflows with side effects. User invokes via `/skill-name`.
- **Analytical** — Analysis that produces findings. User invokes via `/skill-name`.
- **Router** — Dispatches to sub-skills based on context. Saves description budget at scale.

### Router Skills

Routers cover an entire category with one description slot. Sub-skills are loaded on demand based on file type, imports, or problem signals.

| Router | Sub-Skills | Triggers On |
|--------|-----------|-------------|
| **coding-standards** | python, python-patterns, python-exceptions, sql, postgis, spark, scala-on-spark, geopandas, sedona, duckdb-spatial, django, pipeline-jobs, code-review, qml-component-review | `*.py`, `*.sql`, `*.scala`, file imports, framework signals |
| **analysis-methods** | spatial (router itself; dispatches to per-engine spatial skills) | Geographic data, spatial queries; future: statistical, graph, entity-resolution, NLP |
| **shelves** (DBrain) | 11 topic shelves with 53 book skills | Engineering practice / language idioms / business / design questions — see [DBrain](#dbrain--book-skill-library) |

### Spatial skills

`skills/analysis/spatial/` is itself a router that dispatches to four per-engine skills based on data scale × GDAL availability × workload pattern:

| Engine | Skill | Use when |
|---|---|---|
| **PostGIS** | [`coding/postgis/`](skills/coding/postgis/SKILL.md) | Persistent multi-user; ACID; rich indexes (GIST/SP-GIST/BRIN). Includes a *Mastering PostGIS* distillation. |
| **GeoPandas** | [`coding/geopandas/`](skills/coding/geopandas/SKILL.md) | Single-node Python, Pandas idiom. Folds raw Shapely. Has explicit no-GDAL fallbacks. |
| **Apache Sedona** | [`coding/sedona/`](skills/coding/sedona/SKILL.md) | Distributed spatial joins on Spark. Same skill for PySpark and Scala scaffolding. Includes raster. |
| **DuckDB-spatial** | [`coding/duckdb-spatial/`](skills/coding/duckdb-spatial/SKILL.md) | SQL on Parquet without server; bundles GEOS/GDAL/PROJ — the strongest single tool for GDAL-less environments. |

Always start spatial work with `siege_utilities.geo.capabilities.geo_capabilities()` to detect the environment tier, then route from [`analysis/spatial/SKILL.md`](skills/analysis/spatial/SKILL.md).

### Action Skills

User-invoked. These change state (git, APIs, tickets, files).

| Category | Skill | Description |
|----------|-------|-------------|
| `git-workflow/` | **commit** | Structured commits with ticket references |
| `git-workflow/` | **branch** | Branch naming convention (type/descriptive_string) |
| `git-workflow/` | **create-pr** | Pull requests with bidirectional ticket linking |
| `git-workflow/` | **merge** | Develop-first merge workflow |
| `git-workflow/` | **develop-guard** | Ensure develop branch exists |
| `session/` | **wrap-up** | End-of-session commit and documentation cleanup |
| `session/` | **pr-comments** | Triage and respond to PR comments |
| `session/` | **coderabbit-response** | Triage and respond to CodeRabbit reviews |
| `planning/` | **create-ticket** | Create tickets in any platform (GitHub, GitLab, Jira, Linear) |
| `planning/` | **close-ticket** | Close with summary comment, linked commits, verification |
| `planning/` | **update-ticket** | Add progress, link commits, update fields |
| `planning/` | **pre-work-check** | Claim ticket → mark in-progress → branch → start (the pre-flight) |
| `maintenance/` | **consolidate** | Find and consolidate redundant documentation |

### Analytical Skills

User-invoked. Read-only analysis that produces recommendations.

| Category | Skill | Description |
|----------|-------|-------------|
| `coding/` | **code-review** | Systematic review: correctness, security, data integrity, performance |
| `coding/` | **qml-component-review** | QML component decomposition; properties-in / signals-out discipline |
| `planning/` | **im-feeling-lucky** | Prioritize roadmap items by context, age, dependencies, diversity |
| `thinking/` | **think** | Design-first gate: structured design before any implementation |
| `meta/` | **check-resolvable** | Audit that every skill is reachable from RESOLVER |

### Reference Skills

Auto-applied by Claude when relevant. Not behind a router.

| Category | Skill | Description |
|----------|-------|-------------|
| `documentation/` | **cascading-documentation** | Cascading documentation: inline, files, repo, KMS levels |
| `documentation/` | **notion-knowledge-base** | Notion knowledge base authoring at 5th-grade reading level |
| `infrastructure/` | **databricks** | Databricks workspace, jobs, DLT, Delta, Unity Catalog, Photon |
| `infrastructure/` | **unity-catalog** | Unity Catalog permissioning specifics |
| `infrastructure/` | **ops** | Shared-infra guardrails (cyberpower UPS, K8s pod limits, Rundeck concurrency) |
| `maintenance/` | **library-api-evolution** | Renaming public functions, changing defaults, dropping columns safely |

### Meta Skills

| Category | Skill | Description |
|----------|-------|-------------|
| `meta/` | **skillbuilder** | Create, audit, and fix skills per Anthropic's guidelines |

## Quick Start

### Pin to a release tag (recommended)

Pin to a tagged release for stability. Latest is **[`v0.1.0`](https://github.com/siege-analytics/claude-configs-public/releases)** — see [`CHANGELOG.md`](CHANGELOG.md) for what's in each release.

```bash
git subtree add --prefix .claude/skills \
  https://github.com/siege-analytics/claude-configs-public.git v0.1.0 --squash
```

To upgrade later:

```bash
git subtree pull --prefix .claude/skills \
  https://github.com/siege-analytics/claude-configs-public.git v0.2.0 --squash
```

### With `claude_init`

If you use the [siege_analytics_zshrc](https://github.com/dheerajchand/siege_analytics_zshrc) config:

```bash
claude_init
```

This clones skills, generates `CLAUDE.md` from the template, and copies `settings.local.json`.

### Manual setup (tracking `main`, no pin)

```bash
mkdir -p .claude

git subtree add --prefix .claude/skills \
  https://github.com/siege-analytics/claude-configs-public.git main --squash

curl -o CLAUDE.md \
  https://raw.githubusercontent.com/siege-analytics/claude-configs-public/main/templates/CLAUDE.md.template
# Edit CLAUDE.md and replace {{VARIABLES}}

curl -o .claude/settings.local.json \
  https://raw.githubusercontent.com/siege-analytics/claude-configs-public/main/templates/settings.local.json
```

### Update skills

```bash
# Pinned: change tag and re-pull
git subtree pull --prefix .claude/skills \
  https://github.com/siege-analytics/claude-configs-public.git v0.2.0 --squash

# Tracking main: just pull
git subtree pull --prefix .claude/skills \
  https://github.com/siege-analytics/claude-configs-public.git main --squash
```

## Template Variables

The `CLAUDE.md` template supports:

| Variable | Example | Source |
|----------|---------|--------|
| `{{PROJECT_NAME}}` | `my-project` | Directory name or git remote |
| `{{ORG_NAME}}` | `siege-analytics` | Git remote organization |
| `{{GIT_ROOT}}` | `~/git/siege-analytics` | Parent directory |
| `{{CURRENT_DATE}}` | `2026-05-02` | System date |

## DBrain — book-skill library

`skills/shelves/` is a separate, larger library of book-derived skills — *DBrain*, in the spirit of [GBrain](https://github.com/garrytan/gbrain). It uses the same "thin harness, fat skills" pattern and is gated by the same resolver, but lives under its own meta-router so its description budget cost is one slot per shelf, not one per book.

| Shelf | Topic |
|---|---|
| `engineering-principles/` | Clean Code, Clean Architecture, Design Patterns, DDD, Refactoring, Pragmatic Programmer, Ousterhout |
| `systems-architecture/` | Designing Data-Intensive Applications, System Design, Microservices Patterns, Release It!, HPBN, system-design interview |
| `languages/` | Effective Python/Java/Kotlin/TypeScript, Kotlin in Action, Spring Boot, Programming Rust, Rust in Action, asyncio, web scraping |
| `data-and-pipelines/` | Pipeline design and scheduling patterns |
| `product/` | JTBD, Continuous Discovery, Design Sprint, Lean Startup, Lean UX, Inspired, Mom Test, retention |
| `marketing/` | CRO, StoryBrand, Contagious, Made to Stick, Scorecard / One-Page Marketing, Hooked |
| `sales/` | Predictable Revenue, Negotiation, Influence, $100M Offers |
| `strategy/` | Blue Ocean, Crossing the Chasm, Traction (EOS), Obviously Awesome |
| `design/` | Refactoring UI, iOS HIG, UX heuristics, web typography, Top, Don't Make Me Think, Microinteractions |
| `team/` | Drive, the 37signals way |
| `storytelling/` | Storytelling with Data, Animation at Work |

See [`skills/shelves/SKILL.md`](skills/shelves/SKILL.md) (the meta-router) and the per-shelf routers for what each shelf dispatches to.

## siege_utilities

Many skills explicitly delegate to [`siege_utilities`](https://github.com/siege-analytics/siege_utilities) when it covers the task. The [`_siege-utilities-rules.md`](skills/_siege-utilities-rules.md) always-on rule formalizes this preference: **before writing a Python utility, helper, or one-off function, check whether `siege_utilities` already provides it.** If it almost solves the problem but doesn't, file an upstream PR before adding a local helper.

The spatial skills in particular (per-engine `siege-utilities-<engine>.md` references) document what SU obviates and what's still bring-your-own.

## Works well with

- [StrongAI/claude-skills](https://github.com/StrongAI/claude-skills) — `claude_init` merges both repos' skills automatically (org skills take priority)

## Releases & versioning

Versions follow [SemVer](https://semver.org/). Major version bumps for incompatible resolver/router/skill-shape changes; minor for additive skills or shelves; patch for fixes inside existing skills.

See [`CHANGELOG.md`](CHANGELOG.md) for the per-version diff.

Pin downstream consumers to a tag (`v0.1.0`, `v0.2.0`, …). `main` is the rolling integration branch and may include in-flight changes.

## Credits

The DBrain shelves under `skills/shelves/` are integrated and adapted from two MIT-licensed upstream skill libraries:

- **[ZLStas/skills](https://github.com/ZLStas/skills)** — Clean-Code reviewer agents, Effective-* language rules, and skills for Effective Python/Java/Kotlin/TypeScript, Kotlin in Action, Spring Boot, Programming Rust, Rust in Action, asyncio, web scraping, data-pipeline patterns, system-design interview, storytelling, and animation.
- **[wondelai/skills](https://github.com/wondelai/skills)** — Deep `references/`-rich skills covering Clean Code, Clean Architecture, DDD, Refactoring, Pragmatic Programmer, Ousterhout, DDIA, system design, Release It!, HPBN, and the full product / marketing / sales / strategy / design / team shelves.

Inspiration for the shelves model: [GBrain](https://github.com/garrytan/gbrain).

The PostGIS skill draws on *Mastering PostGIS* (Witkowski, Chojnacki, Mackiewicz, 2017), Paul Ramsey's blog, *PostGIS in Action* 3rd ed. (Obe & Hsu, 2021), and Crunchy Data's geospatial materials. See per-skill citations.

See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) for full attribution, commit pins, and per-book source mapping.

## License

MIT — see [`LICENSE`](LICENSE).
