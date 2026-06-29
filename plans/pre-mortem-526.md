---
ticket_refs:
  - siege-analytics/claude-configs-public#526
---
# Pre-mortem: #526 — review-gate re-review enforcement

## Risks

### Tiger 1 — Branch mismatch blocks wrong context
**Severity:** Medium
**Status:** Mitigated

A review-gate.json for branch A could block mutations on branch B if the branch field isn't checked.

**Mitigation:** The reader checks `data.get('branch', '')` against current git branch. Mismatch → skip (no block).

### Tiger 2 — Git commands fail in non-repo context
**Severity:** Low
**Status:** Mitigated

The mutation gate's inline Python might run outside a git repo.

**Mitigation:** All git subprocess calls wrapped in try/except. Failure → pass (no block).

### Paper Tiger 1 — No review-gate.json exists
**Severity:** Low (Paper Tiger)

Most tasks don't have a review-gate.json. No file → no check → no block. Only tasks that have been reviewed (hostile review, cross-review) create this file.

**Implementation may proceed: YES**
