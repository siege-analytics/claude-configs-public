---
name: wrap-up
description: End-of-session cleanup that commits changes, sweeps for LESSONS.md ledger entries, and updates README/ROADMAP/CLAUDE.md. Use when finishing work.
allowed-tools: Read Grep Glob Bash Edit Write
---

# Wrap-up Skill

## Instructions

When wrapping up a session, complete these steps in order:

### 0. Definition of Done verification

Before any commit/cleanup, verify all five criteria from [`definition-of-done`](../_definition-of-done-rules.md) for the session's work:

- [ ] **(a) Code-reviewed** -- every behavior change reviewed (CodeRabbit on PR; self-review of diffs; human review where required)
- [ ] **(b) Edge cases explored** -- checklist applied to every behavior change
- [ ] **(c) Tests written** -- every behavior change has tests
- [ ] **(d) Ticket updated** -- status, comments, links current
- [ ] **(e) Work has a ticket** -- no orphan commits

This step does not block -- it surfaces what's incomplete. If any criterion fails, log the gap explicitly in the wrap-up notes (Step 6 below) so the next session has a starting point. Don't quietly close the session over an incomplete change; the wrap-up note is the audit trail.

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

### 3.5. Check rules-audit cadence

Read the `**Last audit:**` line in `<repo>/LESSONS.md`. If the date is more than **60 days** ago (or the file is missing the line entirely), print a single-line nudge:

> Heads up: rules-audit hasn't run in N days. Consider `/rules-audit` before the next session.

This is **not a blocker** -- the user decides whether to run [`rules-audit`](../rules-audit/SKILL.md). The nudge just ensures the question gets asked.

### 4. Sweep for lessons-learned entries

Before updating CLAUDE.md, sweep the session for findings worth logging in the project's `LESSONS.md` ledger (Tier 1 of the rules pipeline). Ask:

- Did any code-review finding repeat from a prior session?
- Did any CodeRabbit thread map to a recurring pattern?
- Did any human reviewer comment flag "we keep getting this"?
- Did any production incident or near-miss happen during the session?

For each pattern that qualifies, invoke [`lessons-learned`](../lessons-learned/SKILL.md) to append or bump the entry. Threshold guidance:

- Critical (security, data loss): log at recurrence 1
- Production incident: log at recurrence 1
- Recurring style/correctness pattern: log at recurrence 2+
- One-off bug with no pattern: skip -- the commit + ticket are sufficient

### 5. Update CLAUDE.md
Use CLAUDE.md for **session-scoped** notes that don't belong in the durable Tier-1 ledger:
- Workflow gotchas specific to this session's environment
- Useful one-liners or commands discovered
- Context for the next session ("currently blocked on X", "left in state Y")

Durable, recurring patterns belong in `LESSONS.md` (step 4 above), not CLAUDE.md.

### 6. Update project knowledge base (if applicable)

If the project has a knowledge base (Notion, Confluence, internal wiki, etc.) that is intentionally written for non-engineering readers, and this session changed architecture, data models, pipeline structure, or system capabilities, update it.

The mechanics are project-specific (which pages exist, how sync jobs are run, whether agent-authored pages need a provenance tag, where the content registry lives). Project-specific wrap-up overlays should extend this skill with the concrete commands, page taxonomy, and provenance conventions for their knowledge base. The generic rule is just: if architecture changed AND the audience for the knowledge base includes the people who would need to know, update it as part of wrap-up.

**Trigger:** ask "would a non-engineering reader (PM, ops, sales, future hire) need to know about this?" If yes and a knowledge base exists for that audience, update it.

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
- [ ] Checked rules-audit cadence -- nudged user if last audit >60 days ago
- [ ] LESSONS.md ledger updated for any recurring patterns surfaced this session (via [`lessons-learned`](../lessons-learned/SKILL.md))
- [ ] CLAUDE.md updated with session-scoped notes (durable patterns went to LESSONS.md, not here)
- [ ] Project knowledge base updated if architecture, models, or capabilities changed (per project-specific wrap-up overlay if one exists)
