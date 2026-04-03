# Claude Code Configurations (Public)

Reusable Claude Code skills and project initialization templates.

For use with [`claude_init`](https://github.com/dheerajchand/siege_analytics_zshrc) or standalone.

## Contents

| Directory | Purpose |
|-----------|---------|
| `skills/` | Categorized reusable skills for Claude Code sessions |
| `templates/` | Project templates (CLAUDE.md, settings.local.json) |

## Skills

Skills are classified by how they're invoked:

- **Reference** — Knowledge Claude applies automatically when relevant. Not a slash command.
- **Action** — Workflows with side effects. User invokes via `/skill-name`.
- **Analytical** — Analysis that produces findings. User invokes via `/skill-name`.

### Reference Skills

Auto-applied by Claude when it detects relevant work (e.g., writing Python, reviewing SQL).

| Category | Skill | Description |
|----------|-------|-------------|
| `coding/` | **python** | Python style, naming, error handling, type hints, 3.11+ idioms |
| `coding/` | **sql** | PostgreSQL, PostGIS, SparkSQL conventions and performance |
| `coding/` | **spark** | PySpark job patterns, Delta Lake, medallion architecture |
| `analysis/` | **spatial** | Decision framework: spatial vs string vs graph, algorithm selection |
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
