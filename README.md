# Claude Code Configurations (Public)

Reusable Claude Code skills and project initialization templates.

For use with [`claude_init`](https://github.com/dheerajchand/siege_analytics_zshrc) or standalone.

## Contents

| Path | Purpose |
|---|---|
| [`RESOLVER.md`](RESOLVER.md) | **Skill resolver** — master index mapping task patterns to required skills. Mandatory first read before any non-trivial action. |
| `skills/` | Categorized reusable skills for Claude Code sessions |
| `hooks/` | Shell hooks (PreToolUse, UserPromptSubmit) that enforce the resolver |
| `templates/` | Project templates (CLAUDE.md, settings.local.json) |

## The Skill Resolver

The problem this repo solves: **skills are only useful if they fire before the action they govern.** A catalog of skills the agent *could* consult is worth nothing if the agent doesn't actually read them first.

[`RESOLVER.md`](RESOLVER.md) is a task-pattern → required-skill index. When Claude is about to do something (write Delta data, create a PR, author a ticket), it scans the resolver, finds the matching row, and reads the mapped `SKILL.md` before acting. If no pattern matches, universal pre-action checks (catalog-first, brain-first, test-before-bulk, ticket-required, etc.) still apply.

**Inspired by [GBrain](https://github.com/garrytan/gbrain)'s "thin harness, fat skills" pattern** — intelligence lives in the skills, not the runtime. The resolver is the discovery layer.

### Enforcement

Three enforcement layers keep the resolver active:

1. **Session start** — every project `CLAUDE.md` references `RESOLVER.md` as the first action of any non-trivial task.
2. **Every user turn** — [`hooks/resolver/inject-resolver.sh`](hooks/resolver/inject-resolver.sh) is a `UserPromptSubmit` hook that injects the resolver summary into active context on every prompt. Context doesn't decay by turn 20.
3. **Pre-tool-use** — [`hooks/infrastructure/catalog-guard.sh`](hooks/infrastructure/catalog-guard.sh) is a `PreToolUse` hook on `Bash` that matches dangerous catalog-bypass patterns (`.write.save(s3a://...)`, raw Delta/Parquet writes to catalog-managed buckets, direct S3 copies into `hive-warehouse`/`silver`/`gold`) and blocks them with a STOP-read-skill reminder.

Wire the hooks by merging [`hooks/settings-snippet.json`](hooks/settings-snippet.json) into `~/.claude/settings.json` (or project `.claude/settings.local.json`), replacing `/path/to/claude-configs-public` with the actual absolute path to this repo.

### Why this exists

The pattern was introduced after a live incident: Delta data was written directly to `s3a://hive-warehouse/enterprise_bulk/*` instead of through Unity Catalog. The `pipeline-guard` skill already said "Register in Unity Catalog" — but as a footnote in a checklist the agent didn't re-read before acting. Downstream Consumer queried `SELECT ... FROM enterprise_bulk.<table>` through UC, which resolved to a different physical path — so the "cutover" was invisible, and 99 orphaned objects sat in shared storage. The rule existed; the trigger didn't. The resolver is the trigger.

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
| **coding-standards** | python, sql, spark (+ future: django, react, typescript, go) | `*.py`, `*.sql`, `*.ts`, `*.tsx`, `*.js`, `*.go` |
| **analysis-methods** | spatial (+ future: statistical, graph, entity-resolution, nlp) | Geographic data, modeling, network analysis |

### Reference Skills (Flat)

Auto-applied by Claude when relevant. Not behind a router.

| Category | Skill | Description |
|----------|-------|-------------|
| `documentation/` | **update-docs** | Cascading documentation: inline, files, repo, KMS levels |
| `documentation/` | **update-notion** | Notion knowledge base authoring at 5th-grade reading level |

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
| `planning/` | **create-ticket** | Create tickets in any platform (GitHub, GitLab, Jira, Linear) |
| `planning/` | **close-ticket** | Close with summary comment, linked commits, verification |
| `planning/` | **update-ticket** | Add progress, link commits, update fields |
| `maintenance/` | **consolidate** | Find and consolidate redundant documentation |
| `session/` | **pr-comments** | Triage and respond to PR comments |

### Analytical Skills

User-invoked. Read-only analysis that produces recommendations.

| Category | Skill | Description |
|----------|-------|-------------|
| `coding/` | **code-review** | Systematic review: correctness, security, data integrity, performance |
| `planning/` | **im-feeling-lucky** | Prioritize roadmap items by context, age, dependencies, diversity |
| `thinking/` | **think** | Design-first gate: structured design before any implementation |

### Meta Skills

| Category | Skill | Description |
|----------|-------|-------------|
| `meta/` | **skillbuilder** | Create, audit, and fix skills per Anthropic's guidelines |

## Quick Start

### With `claude_init` (recommended)

If you use the [siege_analytics_zshrc](https://github.com/dheerajchand/siege_analytics_zshrc) config:

```bash
claude_init
```

This clones skills, generates `CLAUDE.md` from the template, and copies `settings.local.json`.

### Manual setup

```bash
mkdir -p .claude

# Add skills as subtree
git subtree add --prefix .claude/skills \
  https://github.com/siege-analytics/claude-configs-public.git main --squash

# Copy and customize CLAUDE.md
curl -o CLAUDE.md \
  https://raw.githubusercontent.com/siege-analytics/claude-configs-public/main/templates/CLAUDE.md.template
# Edit CLAUDE.md and replace {{VARIABLES}}

# Copy settings
curl -o .claude/settings.local.json \
  https://raw.githubusercontent.com/siege-analytics/claude-configs-public/main/templates/settings.local.json
```

### Update skills

```bash
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
| `{{CURRENT_DATE}}` | `2026-03-29` | System date |

## Works well with

- [StrongAI/claude-skills](https://github.com/StrongAI/claude-skills) — `claude_init` merges both repos' skills automatically (org skills take priority)

## License

MIT
