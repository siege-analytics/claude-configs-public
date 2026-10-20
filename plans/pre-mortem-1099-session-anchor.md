---
ticket_refs:
  - siege-analytics/claude-configs-public#1099: session resolution trusts a mis-tagged CRAFT_SESSION_DIR over the payload's session
---

## Pre-Mortem
Task: verify `CRAFT_SESSION_DIR` against the payload's session UUID, using the session's turn-anchor file, before anything keys on it.
Ticket: siege-analytics/claude-configs-public#1099

### Tigers

#### Tiger 1: correctly tagged sessions lose their gates (Severity: high)

Mitigation:
- The directory is replaced only when its anchor names a UUID and that UUID differs from the payload's. A missing anchor, a missing UUID, or a payload id that is not a UUID all leave it alone.
- Fixture controls pin both the correctly tagged and the no-anchor cases.
- task_keyed_gates (50), hub_concurrency_gate (26) and session_signal_resolution (18) stay green.

#### Tiger 2: the anchor file is not what Craft writes (Severity: medium)

electinfo has relied on `meta/claude-turn-anchors.json` holding the turn's UUID since enterprise#2960. If a future Craft stops writing it, the check degrades to today's behaviour; it never blocks for lack of an anchor.

#### Tiger 3: a mis-tag with no matching sibling (Severity: medium)

The result is `<sessions>/<payload uuid>`, a session that exists in name only, so no gate is visible and mutations fail closed rather than falling back to a shared workspace-root gate.

### Launch-Blocking Assessment

None identified, provided the suites stay green.
