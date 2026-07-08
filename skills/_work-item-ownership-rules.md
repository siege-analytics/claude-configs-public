---
description: Always-on. Two rules for multi-session work organized around a work tracker (issues / tickets / cards) and a coordinator (a hub or governance session that assigns and follows work). Rule 1 -- stamp the item you own with a machine-readable owner marker so an out-of-band reader can route back to you deterministically. Rule 2 -- report material state changes to your coordinator as you act. Complements _session-coordination-rules (agent-to-agent message cadence); this is the work-session <-> coordinator loop. No override flag.
---

# Work-item ownership & coordinator reporting

These two rules make the loop between a work session and its **coordinator** -- a hub or governance session that assigns and follows work across a **work tracker** (issues, tickets, or cards) -- observable and deterministic. They are the sibling of `_session-coordination-rules` (which covers agent-to-agent message *cadence*); these cover a session's relationship to its coordinator and to the item it owns.

## The two rules

**work-item-ownership:1. Stamp the work item you own with a machine-readable owner marker.** Early in your run -- as one of your first writes on the item -- record which session owns it: e.g. a comment or custom field containing `maintained-by: <your-session-id>`. A coordinator or periodic status tracker that later needs to route a change back to the owning session then reads the marker instead of inferring from session name or labels, which is ambiguous the moment more than one session has touched the same item. Without a marker, an out-of-band reader can only guess (fragile) or route every ambiguous case through the coordinator for a manual call. The stamp is one cheap write and is the only deterministic owner signal an out-of-band reader has.

No override flag: the marker is always cheap and always the correct signal.

**work-item-ownership:2. Report material state changes to your coordinator as you act.** When you are a work session under a coordinator, send the coordinator one concise message on each MATERIAL change of state -- work started, review opened, blocked or unblocked, handed off for verification, completed -- so the coordinator (and any periodic tracker) has a live picture without polling. Report material changes only, never every tool call: over-reporting is noise that trains the coordinator to ignore you. This is the reciprocal of the coordinator/tracker notifying the owning session (via the rule-1 marker) when the item changes from the other side.

**Carve-out (operator override):** if the operator is driving the session directly and interactively, coordinator reporting is redundant -- report to the operator, not to a hub. These rules apply to spawned / background work sessions coordinated by a hub.

## Cross-references

- `_session-coordination-rules` -- agent-to-agent message *cadence* (declare at-rest, stop pinging past at-rest, distinguish slow-from-stuck, hand off the baton, spawn discipline). The work-item rules here are the *content* side: what a work session owes its coordinator, keyed on the item it owns.
- The rule-1 marker is what makes a tracker's "notify the owning session on change" routing deterministic; rule-2 is the session-side half of the same loop.

## Originating evidence

A periodic board-derived status tracker needed to notify the session working a ticket when that ticket changed (e.g. a reviewer answered a question). It had to infer the owning session from session name/label, which failed when several stale sessions all referenced the same ticket -- so it fell back to routing every ambiguous case through the coordinator hub for a manual call. Stamping each work session's id onto its item at spawn made the routing deterministic; pairing it with session-side reporting of material changes closed the loop, so the coordinator no longer had to poll and no owning session went unnotified.

## Tooling status

Judgment-enforced. Mechanical-detection candidates: a spawn-time guard that a work session's spawn prompt includes the stamp instruction; an outbound-message parser that flags a completed material action (PR opened/merged, status transition) with no corresponding coordinator report.

## Attribution

Defers to `_output-rules`. No AI / agent attribution in owner markers, coordinator messages, rule files, or commit / PR bodies.
