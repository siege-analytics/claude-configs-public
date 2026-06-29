---
ticket_refs:
  - siege-analytics/claude-configs-public#450
---
# Pre-mortem: #450 — advisory hooks to JSON-blocking

## Risks

### Tiger 1 — Double-blocking on branch check
**Severity:** Low
**Status:** Mitigated

Both pre-action-guard.sh and branch-state-guard.sh detect protected branches. If both emit `{"continue": false}`, the agent sees two blocks on the same turn. This is harmless — the first block stops the prompt.

### Tiger 2 — SCOPE MISMATCH false positive on multi-ticket branches
**Severity:** Low
**Status:** Mitigated

Branch names with multiple ticket numbers may not match think-gate.json ticket. The existing think-gate-guard already extracts ALL ticket numbers from branch name. Adding SCOPE MISMATCH to BLOCK_PATTERNS just makes existing detection blocking.

### Tiger 3 — Bootstrapping: branch checkout blocked by mutation gate
**Severity:** Medium
**Status:** Mitigated

`git checkout -b` requires think-gate + artifacts. But you need a feature branch before writing repo artifacts. Mitigation: write artifacts to workspace paths which bypass branch-guard write hook.

**Implementation may proceed: YES**
