---
ticket_refs:
  - siege-analytics/claude-configs-public#572: comment pending
type: pre-mortem
---

# Pre-mortem: Remove CLAUDE_CA_ENFORCE dependency (#572)

## Risk classification

Severity: Low

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Hooks that were silent now block unexpectedly | High (intended) | Low — this IS the desired behavior change | Test suite validates blocking behavior |
| JSON format incompatible with some environment | Very low | Medium | Format is the established pattern, tested in production |

## Tiger / Elephant classification

No Launch-Blocking Tigers. The change is deletion-dominant, removing an env var guard to expose an already-tested code path. No new logic, no new dependencies, no new failure modes.
