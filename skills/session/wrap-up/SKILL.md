---
name: wrap-up
description: End-of-session cleanup that commits changes, updates README/ROADMAP/CLAUDE.md with lessons learned. Use when finishing work.
disable-model-invocation: true
allowed-tools: Read Grep Glob Bash Edit Write
---

# Wrap-up Skill

## Instructions

When wrapping up a session, complete these steps in order:

### 0. Definition of Done verification

Before any commit/cleanup, verify all five criteria from [`_definition-of-done-rules.md`](../../_definition-of-done-rules.md) for the session's work:

- [ ] **(a) Code-reviewed** — every behavior change reviewed (CodeRabbit on PR; self-review of diffs; human review where required)
- [ ] **(b) Edge cases explored** — checklist applied to every behavior change
- [ ] **(c) Tests written** — every behavior change has tests
- [ ] **(d) Ticket updated** — status, comments, links current
- [ ] **(e) Work has a ticket** — no orphan commits

This step does not block — it surfaces what's incomplete. If any criterion fails, log the gap explicitly in the wrap-up notes (Step 6 below) so the next session has a starting point. Don't quietly close the session over an incomplete change; the wrap-up note is the audit trail.

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

### 5. Update Notion Knowledge Base (if architecture changed)

If this session changed architecture, data models, pipeline structure, or system capabilities:
- Run affected Notion sync jobs: `python -m sync.run roadmap dashboard automated_skills`
- Create an "Architecture Update — YYYY-MM-DD" page under Telemetry describing what changed and why, at 5th-grade reading level
- Update the Project Roadmap if project status or dependencies changed
- Update the Automated Skills page if new skills or automation were added

**Provenance tagging:** Every Notion page must declare how it is maintained:
- **Sync pages** (rebuilt by cron jobs) already have footers via `notion.provenance_footer("sync")`
- **Agent-created pages** (like Architecture Updates) must append `notion.provenance_footer("agent")` as the last blocks
- **Manual pages** are tagged by the Content Registry
- After creating an agent page, add it to `CONTENT_REGISTRY` in `sync/config/__init__.py` with `"type": "agent"`
- If the page needs human follow-up (e.g., creating a form, configuring a DB), add an entry to `PENDING_HUMAN_ACTIONS` in `content_registry.py`

**Trigger:** Ask yourself — "Would Leena or a new team member need to know about this?" If yes, it belongs in Notion.

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
- [ ] Notion updated if architecture, models, or capabilities changed
- [ ] Architecture Update page created if significant changes were made