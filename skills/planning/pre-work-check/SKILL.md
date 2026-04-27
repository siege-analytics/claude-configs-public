---
name: pre-work-check
description: "MANDATORY gate before starting any work that changes the state or behavior of the software. Verifies the ticket has a project/epic, all blockers are Done, and the dependency graph is clear."
allowed-tools: Read Bash
---

# Pre-Work Check

**When this applies:** Any work that creates a change in state or behavior of the software that will impact the product. Typographical corrections with no functional effect are the only exempt class.

Before you mark a ticket In Progress, assign it to yourself, or write the first commit — run this checklist in full. Do not start until every item passes.

## Why

Work done outside a project drifts from the roadmap and is never deprioritized correctly. Work that starts with open blockers produces rework when the blocker resolves and changes requirements. The dependency graph exists precisely to show the order things must happen in — ignoring it builds on an unstable foundation.

## Checklist

### 1. Ticket is well-formed
- [ ] Title, description, and acceptance criteria are present
- [ ] Type (bugfix / feature / task) is set
- [ ] Priority and size are set

### 2. Ticket belongs to a project (epic)
- [ ] The ticket is assigned to a project or epic in the ticketing system
- [ ] **If not: STOP.** Add it to the correct project, or create one if none fits. Unprojected tickets are not worked.

### 3. All upstream blockers are Done
- [ ] Check the ticket's blocking relations
- [ ] Every ticket listed as a blocker must be in Done state
- [ ] **If any blocker is not Done: STOP.** Report the blocker. Ask the user whether to resolve the blocker first or deprioritize this ticket.

### 4. Dependency graph check
- [ ] Identify what this ticket unblocks when Done
- [ ] If this ticket sits on the critical path, it takes priority over non-critical work
- [ ] If this ticket's project has many blocked dependents, escalate accordingly

### 5. Branch hygiene
- [ ] A feature branch has been created (see `skills/git-workflow/branch/SKILL.md`)
- [ ] You are NOT on main, master, or develop

## Hard Rules

**No project = no work.** Every ticket must belong to a project before work begins.

**Open blockers = no work.** If any upstream ticket is not Done, stop and communicate before proceeding.

**Dependency order is not optional.** The dependency graph defines what gets built in what order.
