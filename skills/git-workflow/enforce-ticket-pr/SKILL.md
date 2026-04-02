---
name: enforce-ticket-pr
description: Enforce that every pull request references tickets and that ticket comments link back to the PR. PRs and tickets must be bidirectionally linked.
---

# Instructions

This skill is a guardrail that modifies the behaviour of the create-pr skill by adding two hard requirements:

1. **Every PR must reference at least one ticket** in its description
2. **Every referenced ticket must be updated with a comment linking back to the PR**

# Before creating a PR

1. Check that all commits on the branch reference tickets
   1. Run `git log develop..HEAD --oneline` to see all commits
   2. Scan each commit for ticket references (Fixes, Refs, Part-of, etc.)
   3. If any commits lack ticket references, flag them to the user
2. Collect the set of unique tickets referenced by commits on this branch
3. Verify these tickets exist and are in the correct state (In Progress or similar)

# PR → Ticket link

The PR description must contain a `## Tickets` section listing every ticket this PR addresses:

```markdown
## Tickets

- Fixes #42
- Refs #38
- Part-of electinfo/enterprise#357
```

### Rules

- Use `Fixes` / `Closes` when the PR fully resolves the ticket
- Use `Refs` when the PR is related but does not resolve the ticket
- Use `Part-of` when the PR is one of several that address the ticket
- **At least one ticket must be listed.** If the PR has no ticket, stop and create one first (if the work is PR-able, it is ticketable)

# Ticket → PR link

After creating the PR, update each referenced ticket with a comment linking back to the PR:

```markdown
PR opened: owner/repo#123
Branch: feature/geographic_enrichment_phase1
Status: Ready for review

### Changes in this PR
- Brief summary of what this PR does relative to this ticket
```

### Platform-specific linking

| Platform | How to link |
|----------|-------------|
| GitHub | PR URLs auto-link in issue comments. Use `gh issue comment` to add the reference |
| GitLab | MR URLs auto-link. Use `glab issue note` to add the reference |
| Jira | Add the PR URL in a comment or use smart commits |
| Linear | Linear auto-links GitHub PRs if integration is configured. Add a manual comment if not |

# Bidirectional verification

After creating the PR and updating tickets, verify both directions:

1. **PR → Tickets**: Read the PR description and confirm all ticket references are present and correctly formatted
2. **Tickets → PR**: Read each referenced ticket and confirm the PR link comment was added

```bash
# Verify PR has ticket references
gh pr view 123 --json body | jq -r '.body' | grep -E '(Fixes|Closes|Refs|Part-of)'

# Verify ticket has PR link
gh issue view 42 --json comments | jq -r '.comments[].body' | grep "PR opened"
```

# When tickets don't exist

If the branch was created without a ticket (which the branch skill should have caught, but sometimes doesn't):

1. **Create the ticket now** -- Use the create-ticket skill
2. **Go back and amend the PR description** to reference the new ticket
3. **Add the ticket reference to the most recent commit** if possible (amend if not pushed, new commit if pushed)

The goal is that by the time the PR is merged, the bidirectional link exists. It's better to create the ticket late than to merge without one.

# PR merge and ticket update

When a PR is merged:

1. **Update referenced tickets** with a merge comment:
   ```markdown
   PR #123 merged into develop.
   Commits: abc1234, def5678
   ```
2. **Move tickets to In Review** (or equivalent) if not already there
3. **Close tickets** only if the PR merge fully resolves them AND the user has approved (per project workflow)

# Override

If the user explicitly says to skip the ticket requirement for a PR:

```
User: "Create the PR without a ticket, I'll add one later"
```

Add a note in the PR description:

```markdown
## Tickets

_No ticket linked -- to be created. See [no-ticket] commits._
```

This should be rare and temporary. Follow up to ensure the ticket is created.

# Attribution policy

**NEVER** include AI or agent attribution in PRs, tickets, or related comments.

# Checklist

- [ ] PR description contains a `## Tickets` section with at least one ticket reference
- [ ] Each ticket reference uses the correct keyword (Fixes, Refs, Part-of)
- [ ] Each referenced ticket has been updated with a comment linking back to the PR
- [ ] All commits on the branch reference tickets (flagged any that don't)
- [ ] Bidirectional links verified: PR → tickets and tickets → PR
- [ ] If no ticket existed, one was created before or immediately after PR creation
- [ ] No AI/agent attribution in the PR or ticket comments
