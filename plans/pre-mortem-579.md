---
ticket_refs:
  - siege-analytics/claude-configs-public#579: comment pending
  - siege-analytics/claude-configs-public#580: comment pending
type: pre-mortem
---

# Pre-mortem: Evidence-chain overrides for test-guard and ticket-required (#579, #580)

## Risk classification

Severity: Low

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Agents that used bare [run-skip] or [no-ticket] are now blocked | High (intended) | Low — this IS the desired change | Agents must learn the evidence-chain format |
| Regex for structured override is too strict (false rejects) | Low | Medium | Regex matches the gold standard pattern exactly |
| Regex for bare override detection misses edge cases | Low | Medium | Pattern covers bare marker and empty-content marker |

## Tiger / Elephant classification

No Launch-Blocking Tigers. The evidence-chain regex is identical to the production-tested pattern in post-error-revision-required.sh.
