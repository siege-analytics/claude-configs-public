---
description: Always-on Definition of Done. Applied to every behavior change. Five hard criteria — review, edge cases, tests, ticket update, ticket existence. No soft carve-outs.
---

# Definition of Done

Code is not finished until **all five** of the following are true. This is a gate, not a recommendation. PRs that fail any criterion don't merge; sessions that fail any criterion don't end.

## The five criteria

### a. Code-reviewed

Every behavior change goes through code review before merge. CodeRabbit / agent review counts as one pass; a human review is required for non-trivial changes.

**Operationalized by:** [skill:code-review] (slash-invokable as `/code-review`).

### b. Edge cases explored

Every behavior change has been tested mentally — and where appropriate, in tests — against:

- Empty input (`[]`, `""`, `None`, missing key)
- Boundary values (zero, one, max, min, off-by-one neighbors)
- Duplicates
- Out-of-order input
- Very small (1 element) and very large (1M+ elements)
- Mixed types where the contract claims homogeneity
- Partial failure (network timeout mid-batch, write succeeded but ack failed, half the rows valid)
- Null / NaN / NULL in tabular inputs
- Identifier collisions (two different sources, same key)

**Operationalized by:** [skill:code-review] §1 ("Correctness") — explicit edge-case checklist.

### c. Tests written

**Tests are mandatory for all behavior changes.**

- Every new function, method, or behavior change has at least one test.
- Every `raise` path has a negative test.
- Bug fixes ship with a regression test that fails on the previous commit.
- If the project has no test infrastructure yet, **the first contribution adds the infrastructure** (test framework, runner, sample test) before any behavior change. "We don't have tests yet" is not an exception; it's the first ticket.
- PRs without tests must explicitly justify the omission in the PR description, and the justification is subject to review. Acceptance is not assumed.

**Operationalized by:** [skill:python] "Tests and Documentation — non-negotiable" section (Python); [skill:coding] Rule 6 (language-agnostic).

### d. Non-trivial updates → update the ticket

Non-trivial work updates the ticket as it progresses. The ticket reflects the current state of the work, not the state when it was written.

What counts as a ticket update:
- Status transitions (Todo → In Progress → In Review → Done)
- Comments on substantive changes (scope expansion, blocker discovery, design pivots)
- Links to commits and PRs (bidirectional — commit references ticket, ticket links commit)
- Final summary at close (what shipped, what was deferred, validation status)

**Operationalized by:** [skill:update-ticket] (slash-invokable as `/update-ticket`); [skill:close-ticket].

### e. Work has a ticket

Every behavior change starts from a ticket. Tickets exist to:
- Establish *why* the work is being done (problem statement)
- Track scope and acceptance criteria
- Surface dependency relations (what blocks this; what this unblocks)
- Provide an audit trail tying code changes to motivating problems

**Operationalized by:** [skill:pre-work-check] (slash-invokable as `/pre-work-check`) — runs before the first commit; verifies ticket exists, belongs to a project, has no open blockers.

If you find yourself coding without a ticket, stop and write one (or invoke [skill:create-ticket]). The ticket can be a one-liner; what matters is that it exists and is reachable from the commit.

## What "done" means at each transition

| Transition | Done check |
|---|---|
| Pre-commit | Tests added/updated; docstrings on new public APIs; commit message references the ticket |
| Pre-PR | All five criteria; PR description summarizes scope, links the ticket, lists what was tested |
| Pre-merge | CodeRabbit + GitGuardian + (when relevant) human review pass; ticket is In Review status |
| Session-end | All five criteria across all changes in the session; ticket status reflects current state; no orphan commits without ticket links |

## Operationalization map

| Criterion | Skill / file that runs it |
|---|---|
| (a) Code-reviewed | [skill:code-review] |
| (b) Edge cases | [skill:code-review] §1 |
| (c) Tests | [skill:python] "Tests and Documentation" section; [skill:coding] Rule 6 |
| (d) Ticket update | [skill:update-ticket], [skill:close-ticket] |
| (e) Ticket exists | [skill:pre-work-check], [skill:create-ticket] |

The PR-creation gate ([skill:create-pr]) checks all five before opening.

The session-end check ([skill:wrap-up]) verifies all five before declaring the session complete.

## Exceptions

The following are exempt from criteria (a)–(d) but **not** from (e) (ticket existence):

- **Typo fixes** with no functional effect (the same word, spelled correctly)
- **Doc-only changes** that don't reframe API contracts
- **Tooling / CI / build chores** that don't change runtime behavior

If in doubt, apply the full Definition of Done. The cost of unnecessary diligence is low; the cost of skipping diligence on a behavior change that looked trivial is high.

Even exempt changes still need a ticket — the tracking serves the audit trail, not just the work-discipline.

## Why hard enforcement

Soft rules erode. "We should have tests" becomes "we'll add tests later" becomes "we don't have tests for this codebase, sorry." The same drift applies to review, ticket updates, and ticket existence. Each of the five criteria has a documented Siege incident in its origin: missing tests masked a regression that shipped to production; missing reviews let an architectural mistake compound; missing ticket updates left another team blocked on what they thought was unblocked; ticketless work derailed roadmap planning twice in 2025.

The Definition of Done is the documented response to those incidents. Treat it as such.

## Attribution

Defers to [rule:output]. No AI / agent attribution in commits, PRs, or comments.
