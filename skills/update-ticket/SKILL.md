---
name: update-ticket
description: Add progress comments, link commits, and update fields on an existing ticket (GitHub, GitLab, Jira, Linear).
allowed-tools: Read Grep Glob Bash
---

# Instructions

1. Identify the ticket to update
   1. The user may provide a ticket number, URL, or description
   2. If ambiguous, search recent tickets and confirm with the user
2. Detect the ticketing platform from repo context
   1. If `.git/config` has a `github.com` remote, use `gh` CLI
   2. If `.git/config` has a `gitlab.com` or self-hosted GitLab remote, use `glab` CLI or the GitLab API
   3. If the project uses Jira, Linear, or another system, ask the user which CLI or API to use
   4. Use existing authenticated CLI tools. Never store credentials in plaintext.
3. Read the current state of the ticket before making changes
   1. Review existing comments to avoid duplication
   2. Note current field values so you only change what needs changing
4. Make the update
   1. Add a comment (see Writing comments below)
   2. Update fields as needed (assignee, labels, milestone, status, priority)
   3. Link related commits if applicable (see Linking commits below)

# Linking commits to tickets

When work has been done on a ticket, the comments should reference the relevant commits so reviewers can trace from ticket to code.

## Finding relevant commits

```bash
# Search for commits mentioning the ticket number
git log --oneline --grep="#42"

# Search for commits by a specific author in a date range
git log --oneline --after="2026-03-25" --author="dheeraj"

# Search for commits touching specific files
git log --oneline -- path/to/file.py
```

## Formatting commit references in comments

Reference commits by their short SHA and a one-line description of what changed. Group them logically, not chronologically, when the ticket spans multiple concerns.

### Template

```markdown
## Progress update

Brief narrative of what was accomplished and what remains.

### Commits

| SHA | Description |
|-----|-------------|
| `abc1234` | Refactored silver transform to preserve string types |
| `def5678` | Added round-trip test for committee_id zero-padding |

### Remaining work
- [ ] Item still to do
- [ ] Another item
```

### Platform-specific linking

- **GitHub**: SHAs auto-link when the commit is in the same repo. For cross-repo, use `owner/repo@sha`.
- **GitLab**: SHAs auto-link within the same project. For cross-project, use `group/project@sha`.
- **Jira**: Use smart commits (`PROJ-123 #comment fixed the thing`) or paste the full commit URL.
- **Linear**: Mention the issue ID in the commit message (`FIX-123`) for auto-linking.

# Updating ticket fields

Ticket lifecycle status is proactive, not passive. Apply `[`ticket-lifecycle`](../_ticket-lifecycle-rules.md)` whenever the action changes the ticket's real-world lane. Only update fields that have actually changed.

| Situation | Required status/field update |
|-----------|------------------------------|
| Work has started | status -> In Progress, assignee if unset, comment naming branch/artifact |
| PR opened | status -> In Review, comment with PR URL and branch |
| Testing/UAT/QA handoff | status -> In Testing / Awaiting UAT / QA, comment with owner, environment, evidence, pass/fail criteria |
| Blocked by another ticket/system/person | status -> Blocked, add blocker label if available, comment with Blocked because / Waiting on / Unblocks when |
| Unblocked/resumed | status -> In Progress or In Review, comment with evidence that blocker cleared and next action |
| Merged + verified | status -> Done/Closed only after merge, target branch, deployment/release, and UAT/verification evidence |
| Scope changed | update title if needed, comment explaining the change, adjust size/priority |
| Reassigning | assignee, comment explaining why |
| Partial progress | comment with commits and remaining checklist; status remains the active lane |

If the platform has no mutable status field through the available CLI/API, add a comment with exact prefix `Status: <state>` and include the evidence that would have justified the field update.

# Writing comments

Comments are the narrative thread of a ticket's life. They should be useful to someone reading the ticket months later who needs to understand what happened and why.

## Principles

1. **Lead with the conclusion** -- State what changed or what was decided before explaining how you got there
2. **Be specific** -- "Fixed the bug" is useless. "Cast was dropping leading zeros on committee_id; changed column type from integer to string in silver_transforms.py:48" is useful
3. **Link, don't paste** -- Reference commits, files, docs, and other tickets by link rather than copying content that will go stale
4. **One comment per logical update** -- Don't batch unrelated updates into a single comment. Don't split one update across multiple comments
5. **Include the why** -- Field changes without explanation create confusion. "Moved to P0" is less useful than "Moved to P0 -- this is blocking the Quicksilver join point and Steve's pipeline is waiting on it"
6. **Avoid filler** -- No "Just checking in" or "Quick update" preambles. Start with substance

## Comment types

### Progress update
Report what was done, link commits, note what remains.

```markdown
Preserved leading zeros in committee_id through the silver transform.

**Commits**: `abc1234`, `def5678`
**Remaining**: Integration test against full bronze dataset (running now, ~20 min).
```

### Blocker notification
Explain what is blocked, by what, and what the path forward is.

```markdown
Blocked by #298 -- GeoPopulateAll needs to run on the cluster before we can
verify the geographic crosswalk. Steve is aware; tagged in that issue.

Parking this until the cluster job completes.
```

### Decision record
Capture a decision that affects the ticket's direction, especially if it came from a conversation outside the ticket.

```markdown
Per discussion with Steve: we'll use UUID5 for entity IDs rather than
auto-increment. This aligns with the Quicksilver join point design (see en#357).

Updating the transform to use `uuid5(NAMESPACE_URL, fec_id)`.
```

### Scope change
Explain what changed about the ticket's scope and why.

```markdown
Expanding scope to include all FEC identifier fields, not just committee_id.
The same integer cast issue affects candidate_id and report_id.

Updated title and acceptance criteria. Size bumped from S to M.
```

### Handoff
When reassigning or leaving context for someone else.

```markdown
Reassigning to @steve -- the remaining work is on the Spark Operator side
and needs cluster access I don't have.

**State of things:**
- Silver transform is fixed and tested locally (commits above)
- Integration test written but not yet run on cluster
- The Hive registration step still fails via Spark Connect (see en#349)
```

# Attribution policy

**NEVER** include AI or agent attribution in ticket updates, comments, or field changes. This includes:
- No "Generated with Claude Code", "Made with Cursor", "Built with Codex", or any AI tool mentions
- No `🤖`, `[bot]`, or other markers that signal AI involvement
- No attribution to any AI assistant, code generation tool, or agent framework
- This applies to comments, status updates, and any text written on the ticket

# Checklist

- [ ] Read the ticket's current state and existing comments before updating
- [ ] Comment leads with the conclusion, not the process
- [ ] Commits are linked with SHAs and grouped logically
- [ ] Field changes are accompanied by a comment explaining why
- [ ] No duplicate information from previous comments
- [ ] No AI/agent attribution anywhere in the update (no "Generated with", no "Made with", no tool mentions)
- [ ] Cross-platform sync: if the ticket is dual-tracked (GitHub + GitLab), update both
