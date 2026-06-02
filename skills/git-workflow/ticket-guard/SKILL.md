---
name: ticket-guard
description: "Pre-work gate: ensures a ticket destination is configured before non-trivial work begins. Like develop-guard enforces branching, this enforces that strategic decisions and work-tracking have a durable, human-visible destination. Fires before any non-trivial action."
disable-model-invocation: true
allowed-tools: Bash Read
---

# Ticket Guard

Enforce that every workspace has a configured, reachable ticket destination before non-trivial work begins. Decisions and work-tracking that land only in workspace-local `plans/` or `memory/` are invisible to humans and ephemeral across sessions. This guard closes that gap.

## Core invariant

> **Every non-trivial piece of work and every strategic decision must have a durable, human-visible destination.** `plans/` and `memory/` are agent-local scratch. Tickets, issues, and tracked documents are the durable record.

The destination does not have to be GitHub Issues. It must be:

1. **Durable** -- survives session end, agent restart, workspace deletion
2. **Human-visible** -- a human can find it without running the agent
3. **Addressable** -- each item has a stable reference (URL, file path + row, ticket ID)

## Acceptable destinations

| Destination | Addressable as | Notes |
|---|---|---|
| GitHub Issues | `owner/repo#123` | Default for repos with a GitHub remote |
| GitLab Issues | `group/project#123` | Default for repos with a GitLab remote |
| Linear | `TEAM-123` | When workspace has a Linear source configured |
| Jira | `PROJ-123` | When workspace has Jira integration |
| Local file (CSV, Excel, JSON, Markdown) | `file:<path>#<row-or-heading>` | For projects without a ticket system |
| Notion database | `<page-url>` | When workspace has Notion integration |

## NOT acceptable destinations

- `plans/*.md` -- agent-local, not human-visible without the agent
- `memory/*.md` -- agent-local, same problem
- "I'll file a ticket later" -- not a destination; it's a deferral
- Conversation context -- ephemeral, lost on session end

## Instructions

This skill fires as a pre-work check. It runs once per session (memoized after first check).

### Step 1: Detect ticket destination

Check, in order:

1. **Workspace config** -- does `~/.craft-agent/workspaces/<workspace>/config.json` (or equivalent) have a `ticketDestination` field?
2. **Git remote** -- does the working directory have a GitHub or GitLab remote? If so, the remote's issue tracker is the default destination.
3. **Source integrations** -- does the workspace have an active Linear, Jira, or similar source?

If any of the above resolves, store the result and proceed.

### Step 2: If no destination found -- STOP

Present the user with options:

> This workspace has no ticket destination configured. Strategic decisions and work-tracking need a durable, human-visible home. Where should tickets go?
>
> 1. **GitHub Issues** on `<detected-remote>` (if a remote exists)
> 2. **Linear** (if source is configured but inactive)
> 3. **Local tracking file** -- I'll create a `TICKETS.md` or `tickets.csv` in the project root
> 4. **Other** -- tell me the system and I'll configure it
>
> This is a one-time setup per workspace. I won't ask again once configured.

Do NOT proceed with non-trivial work until the user answers. Do NOT default silently. The develop-guard asks before creating a branch; this guard asks before starting work.

### Step 3: Validate the destination is reachable

- **GitHub/GitLab**: verify the remote exists and you can list issues (`gh issue list --limit 1` or equivalent)
- **Linear/Jira**: verify the source is active and authenticated
- **Local file**: verify the file exists or can be created at the specified path
- **Notion**: verify the database is accessible

If validation fails, report the error and ask the user to fix it before proceeding.

### Step 4: Record the destination

Store the validated destination so subsequent skill invocations (especially `decision-to-ticket`) know where to file.

For agent-local persistence (within session):
- Set a session-scoped variable or note in the conversation context

For cross-session persistence:
- Write to a workspace-level config or memory entry of type `reference`

## When this skill fires

This skill is a **universal pre-action check** -- it fires before any non-trivial work, in the same category as develop-guard (check #6) and ticket-required (check #5).

**Specifically, it fires when:**
- The agent is about to start implementation work
- The agent is about to make a strategic decision (as defined by `decision-to-ticket`)
- The agent is about to create a branch for feature work
- The `decision-to-ticket` skill needs a destination and none is configured

**It does NOT fire for:**
- Read-only exploration
- Trivial single-line fixes
- Research questions
- Session setup / configuration

## Interaction with existing checks

- **Check #5 (Ticket-required)** says "work requires a ticket." Ticket-guard says "and here's where tickets live." They're complementary.
- **Check #6 (Branch-correct / develop-guard)** says "be on the right branch." Ticket-guard says "have a place to file." Same structural pattern.
- **`decision-to-ticket` skill** consumes the destination this guard configures. If ticket-guard hasn't run, decision-to-ticket triggers it.

## Edge cases

### Multiple repos in one workspace
A workspace may have multiple projects with different ticket destinations (e.g., `siege-utilities` uses GitHub Issues, `electinfo` uses Linear). The destination is scoped to the working directory's remote, not the workspace globally.

### Offline / air-gapped work
If the ticket destination is unreachable (no network, API down), the guard should:
1. Note the unreachable destination
2. Allow work to proceed with a local tracking file as fallback
3. Queue the ticket creation for when connectivity returns

### User explicitly opts out
If the user says "I don't want ticket tracking for this project," that IS a valid answer. Record it as the destination: `none (user opted out on <date>)`. The guard won't ask again, but `decision-to-ticket` will still flag strategic decisions -- it just won't auto-file them.
