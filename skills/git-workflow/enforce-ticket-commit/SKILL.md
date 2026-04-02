---
name: enforce-ticket-commit
description: Enforce that every commit references a ticket. If work is committable, it is ticketable. Refuse to commit without a ticket reference unless explicitly overridden.
---

# Instructions

This skill is a guardrail, not an action. It modifies the behaviour of the commit skill by adding a hard requirement: every commit must reference a ticket.

1. Before creating any commit, check for a ticket reference
   1. Scan the commit message for ticket patterns (see Ticket patterns below)
   2. If no ticket reference is found, **stop and ask**
2. If no ticket exists for this work
   1. Inform the user: "This work doesn't have a ticket. If it's committable, it's ticketable."
   2. Offer to create a ticket first (use the create-ticket skill)
   3. Only proceed with the commit after a ticket exists or the user explicitly overrides
3. If the user explicitly overrides
   1. Accept the override but add a `[no-ticket]` marker in the commit body (not the subject line) so it's searchable later
   2. This should be rare -- the goal is to make ticketless commits uncomfortable, not impossible

# Ticket patterns

The commit footer should contain one of these patterns:

```
Fixes: #42
Closes: #42
Refs: #42
Part-of: #42
```

Cross-repo references are also valid:

```
Fixes: electinfo/enterprise#42
Refs: siege-analytics/siege_utilities#335
```

Platform-specific patterns that auto-link are also acceptable:

| Platform | Patterns |
|----------|----------|
| GitHub | `#42`, `owner/repo#42`, `GH-42` |
| GitLab | `#42`, `group/project#42` |
| Jira | `PROJ-42`, `ELE-42` |
| Linear | `ELE-42`, `SU-42` |

# Why this matters

Commits without ticket references create invisible work. When someone reads the git log in six months, they can't trace a commit back to the decision that motivated it. When a PM reviews velocity, unticketed work doesn't exist. When a teammate reviews a PR, they can't read the context.

**If you're making a change worth committing, you're making a change worth tracking.**

Exceptions exist (emergency hotfixes, trivial typos, CI configuration), but they should be the exception, not the norm. The `[no-ticket]` marker makes exceptions visible and auditable.

# Decision tree

```
Commit ready?
├── Has ticket reference in footer? → Proceed with commit
├── No ticket reference?
│   ├── Ticket exists but not referenced? → Add reference, then commit
│   ├── No ticket exists?
│   │   ├── User wants to create ticket? → Create ticket (create-ticket skill), then commit
│   │   └── User explicitly overrides? → Commit with [no-ticket] in body
│   └── Trivial change (typo, formatting)? → Ask user if override is appropriate
└── Ambiguous? → Ask user
```

# Integration with commit skill

This skill wraps the existing commit skill. The commit workflow becomes:

1. Stage changes (per commit skill)
2. **Check for ticket reference** (this skill)
3. Write commit message (per commit skill)
4. **Verify ticket reference is in the footer** (this skill)
5. Create the commit
6. Verify (per commit skill)

# Override syntax

When the user explicitly says to skip the ticket requirement:

```
User: "Just commit it, no ticket needed"
User: "Override the ticket check"
User: "This is too trivial for a ticket"
```

In these cases, add to the commit body:

```
[no-ticket] Trivial formatting change, per operator override.
```

# Attribution policy

**NEVER** include AI or agent attribution in commits, tickets, or related content.

# Checklist

- [ ] Commit message footer contains a ticket reference (Fixes, Closes, Refs, or Part-of)
- [ ] Ticket reference points to a real, existing ticket
- [ ] If no ticket existed, one was created before committing (or user explicitly overrode)
- [ ] Override is marked with `[no-ticket]` in the commit body
- [ ] The referenced ticket is updated with the commit SHA (per update-ticket skill)
