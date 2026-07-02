---
description: Always-on ticket lifecycle status discipline. Ticket state must move at the point of action: work start, PR open, test/UAT handoff, blocker, unblock/resume, merge/verified close. Platform-agnostic; requires a comment when a platform lacks a mutable Status field.
---

# Ticket Lifecycle Status

Ticket comments are not the work and ticket fields are not optional bookkeeping. A reader must be able to tell whether a ticket is not started, in progress, in review, in testing/UAT, blocked, or done from the ticket itself.

## Lifecycle rules

### ticket-lifecycle:1. Work start moves the ticket to In Progress

When you begin non-trivial work on a ticket, update the ticket at the same time:

- Status/state: `In Progress` or the platform equivalent.
- Assignee: set to the current operator/agent owner if the platform supports it and it is unset.
- Comment: one sentence naming the branch or investigation artifact you are starting from.

If the platform has no mutable status field, add a comment beginning `Status: In Progress` with the branch/artifact evidence.

### ticket-lifecycle:2. PR creation moves the ticket to In Review

The same action that opens a PR must update each referenced ticket:

- Status/state: `In Review` or platform equivalent.
- Comment: PR URL, branch, and whether the PR fixes or only references the ticket.

A PR comment without a status transition is incomplete unless the platform lacks a status field; in that case the comment must include `Status: In Review`.

### ticket-lifecycle:3. Test/UAT handoff moves the ticket to In Testing or Awaiting UAT

When work leaves author/reviewer hands and enters testing, QA, user acceptance, rollout validation, or production UAT:

- Status/state: `In Testing`, `Awaiting UAT`, `QA`, or platform equivalent.
- Comment: test/UAT owner, environment, evidence to be collected, and pass/fail criteria.

Do not mark the ticket done while testing/UAT evidence is pending.

### ticket-lifecycle:4. Blockers are status, not just labels

When work is blocked by a dependency, external answer, failed gate, missing credential, or unmerged upstream:

- Status/state: `Blocked` or platform equivalent.
- Label: add a blocker/dependency label if available.
- Comment: `Blocked because: <reason>; Waiting on: <ticket/person/system>; Unblocks when: <falsifiable condition>`.

A blocked ticket without a failure reason is misleading and violates coordinator status discipline.

### ticket-lifecycle:5. Unblocked/resumed tickets move back to the active lane

When the blocking condition clears, update the ticket in the same action:

- Status/state: `In Progress` if author work remains.
- Status/state: `In Review` if the next action is review.
- Comment: evidence that the blocker cleared and the next owner/action.

### ticket-lifecycle:6. Done requires merge plus verification evidence

Closing or marking Done requires all applicable evidence:

- merged commit/PR evidence,
- target branch evidence,
- deployment/release evidence or N/A with reason,
- test/UAT/production validation evidence or N/A with reason.

If any evidence is missing, the ticket remains in the appropriate active state (`In Review`, `In Testing`, or `Blocked`).

## Platform fallback

Different trackers name statuses differently. Use the closest platform equivalent. If no status field is available through the authenticated CLI/API, write the status as a ticket comment with the exact prefix `Status: <state>` and include the evidence that would have justified a field update.

## Cross-references

- `[skill:update-ticket]` is the platform action surface for comments and fields.
- `[skill:create-pr]` owns the In Review transition.
- `[skill:close-ticket]` owns the Done/Closed transition.
- `[rule:definition-of-done]` requires the ticket to reflect the current state before PR and close.
- `[rule:session-coordination]` covers agent-to-agent baton and status clarity.
