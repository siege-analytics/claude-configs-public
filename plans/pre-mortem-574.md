---
ticket_refs:
  - siege-analytics/claude-configs-public#574: comment pending
type: pre-mortem
---

# Pre-mortem: Tighten universal-mutation-gate designing/reviewing bypass (#574)

## Risk classification

Severity: Medium

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Agents in designing status can no longer run `git commit` or `git push` | High (intended) | Low — this IS the desired change | Agent must move to implementing status first |
| `python3 bin/build.py --deploy` blocked during designing | Medium | Medium — needed for deploy stamp | Not in MUTATION_INDICATORS; passes during designing |
| Commands between safelist and mutation-indicators are under-scrutinized | Low | Low | Gap is small: non-safelist, non-mutation commands are investigation-like |
| Agents stuck in designing after tightening — no clear path to implementing | Low | High | BLOCK message describes the exact steps: produce artifacts, change status |

## Tiger / Elephant classification

No Launch-Blocking Tigers. The change is a pure restriction (designing/reviewing gets less access, not more). Existing implementing path is unchanged. The only way an agent gets stuck is if it doesn't read the BLOCK message, which has explicit instructions.
