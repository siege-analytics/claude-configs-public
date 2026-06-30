---
ticket_refs:
  - siege-analytics/claude-configs-public#581: comment pending
type: pre-mortem
---

# Pre-mortem: Evidence-chain override for workaround-tally (#581)

## Risk classification

Severity: Low

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Agents that used bare [workaround-acknowledged: #N] are now blocked | High (intended) | Low — this IS the desired change | Agents must add Reason/Evidence/Falsification |
| Regex for structured override is too strict (false rejects) | Low | Medium | Regex matches the gold standard and the already-merged #579/#580 patterns |
| Override check order causes structured overrides to hit bare-rejection first | None | High | Structured check runs first, bare check only fires on non-match |

## Tiger / Elephant classification

No Launch-Blocking Tigers. The evidence-chain regex is identical to the production-tested patterns merged in #579/#580 and the gold standard in post-error-revision-required.sh.
