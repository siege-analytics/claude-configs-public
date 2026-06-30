---
ticket_refs:
  - siege-analytics/claude-configs-public#582: comment pending
type: pre-mortem
---

# Pre-mortem: Promote destructive-guard v2-deferred tiers (#582)

## Risk classification

Severity: Medium

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `gh issue comment` blocked during artifact posting | High (intended) | Medium — evidence-chain override provides escape | Agents must include [destructive-ok: ...] in command text |
| Circular dependency with mutation-gate (#574) | Medium | High | Evidence-chain override in command text; allow-list as fallback |
| Existing tests for destructive-guard break | Low | Medium | Tests cover prod-destructive patterns; v2 tiers are additive |
| curl POST blocked during legitimate API calls | Medium (intended) | Medium | Allow-list file provides per-project exceptions |

## Tiger / Elephant classification

Potential Tiger: the mutation-gate requires `gh issue comment` to satisfy its artifact-posted gate, but the destructive-guard now blocks `gh issue comment`. Both hooks fire on the same PreToolUse event. The evidence-chain override provides a mechanical escape, but if an agent doesn't know to include it, the pipeline deadlocks.

Mitigation: this is the same class of circular dependency as #574. The evidence-chain override is the designed escape. The BLOCKED message includes the override format. Worst case, the agent adds the override and retries.
