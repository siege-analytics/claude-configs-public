---
ticket_refs:
  - siege-analytics/claude-configs-public#531
---
# Pre-mortem: #531 — entity count drift promotion

## Risks

### Tiger 1 — False positive from format variation
**Severity:** Low
**Status:** Mitigated

The `**` header count in prose may not match `verifiedShapes` array length if formats diverge. But the guard requires both counts > 0 and different — a genuine signal of drift.

**Implementation may proceed: YES**
