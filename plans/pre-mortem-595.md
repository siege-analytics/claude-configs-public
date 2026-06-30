---
ticket_refs:
  - siege-analytics/claude-configs-public#595: open
type: pre-mortem
---

## Risk classification for #595: enforcement contradiction escalation rule

### Tiger 1: Infinite recursion — agent encounters contradiction while fixing contradiction
- **Severity:** Medium
- **Urgency:** Low — unlikely in practice since fix tickets are simple rule-file additions
- Mitigation: rule scoped to original task enforcement, not fix-ticket pipeline
- Falsification: if the agent files a ticket about the fix-ticket's pipeline being broken, the scoping failed
- **Status:** Addressed in design — fix tickets go through normal pipeline

### Tiger 2: Agent weaponizes rule to avoid work
- **Severity:** Medium
- **Urgency:** Medium — agents optimize for speed and will misclassify normal blocks as contradictions
- Mitigation: require specific evidence (which gate, which command, why wrong, what workaround). Lazy classifications can't produce this evidence.
- Falsification: if tickets filed under this rule lack specific gate/command/reason evidence, the evidence requirement is insufficient
- **Status:** Addressed — evidence fields are mandatory in the rule

### Paper Tiger: Too many tickets filed
- **Severity:** Low
- **Urgency:** Low — better to have false-positive tickets than silent workarounds
- Mitigation: tickets are cheap to close; workarounds are expensive to find
- **Status:** Accepted risk

Implementation may proceed: YES
