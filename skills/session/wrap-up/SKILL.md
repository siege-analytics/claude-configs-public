---
name: wrap-up
description: End-of-session cleanup that commits/deploys changes, updates README.md, ROADMAP.md, and CLAUDE.md with lessons learned. Use when finishing work on a repository.
---

# Wrap-up Skill

## Instructions

When wrapping up a session, complete these steps in order:

### 1. Commit and Deploy
- Check `git status` in all modified repositories
- Commit any uncommitted changes with descriptive messages
- Push to origin
- Trigger builds/deploys if applicable (ArgoCD sync, Tekton pipelines)
- Verify deployments are healthy

### 2. Update README.md
Update the repository's README.md to reflect current state:
- Add/update sections for new features or components
- Update status tables (e.g., interpreter status, service status)
- Document any new configuration or setup steps
- Remove outdated information

### 3. Update ROADMAP.md
Update or create ROADMAP.md with next steps:
- Mark completed items as done
- Add new items discovered during the session
- Prioritize remaining work
- Note any blockers or dependencies

### 4. Update CLAUDE.md
Add a "Lessons Learned" or "Notes" section documenting:
- Mistakes made during the session
- How to do things correctly in future sessions
- Gotchas or non-obvious behaviors discovered
- Useful commands or patterns that worked well

## Example CLAUDE.md Addition

```markdown
## Session Notes (YYYY-MM-DD)

### Mistakes to Avoid
- **Issue**: Git branch mismatch - local `master` vs remote `main`
  **Fix**: Always use `git checkout -B main origin/main` after clone/fetch

### Useful Patterns
- To restart interpreter without pod restart: `curl -X PUT .../api/interpreter/setting/restart/<name>`
```

## Attribution policy

**NEVER** include AI or agent attribution in commits, documentation updates, or any content produced during wrap-up. No "Generated with Claude Code", "Made with Cursor", "Built with Codex", Co-Authored-By lines referencing AI tools, or any other AI/agent markers.

## Checklist

- [ ] No AI/agent attribution in any commits or documentation produced
- [ ] All changes committed
- [ ] All changes pushed to origin
- [ ] Builds/deploys triggered and healthy
- [ ] README.md updated with current state
- [ ] ROADMAP.md updated with next steps
- [ ] CLAUDE.md updated with lessons learned