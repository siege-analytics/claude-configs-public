# Claude Code Configurations (Public)

Reusable Claude Code skills and project initialization templates.

For use with [`claude_init`](https://github.com/dheerajchand/siege_analytics_zshrc) or standalone.

## Contents

| Directory | Purpose |
|-----------|---------|
| `skills/` | Categorized reusable skills for Claude Code sessions |
| `templates/` | Project templates (CLAUDE.md, settings.local.json) |

## Skills

| Category | Skill | Purpose |
|----------|-------|---------|
| `session/` | **wrap-up** | End-of-session cleanup: commit changes, update README/ROADMAP/CLAUDE.md with lessons learned |
| `planning/` | **im-feeling-lucky** | Analyze ROADMAPs and suggest top 5 items to work on next, weighted by context, age, dependencies |
| `maintenance/` | **consolidate** | Find and consolidate redundant documentation across repositories |

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
