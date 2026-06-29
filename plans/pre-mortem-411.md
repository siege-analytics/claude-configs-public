---
ticket_refs:
  - siege-analytics/claude-configs-public#411
---
# Pre-mortem: #411 — KB and testing-frameworks as blocking gates

## Risks

### Tiger 1 — Native hook detection false positive
**Severity:** Low
**Status:** Mitigated

If COMMAND extraction fails for a reason other than native hook invocation (e.g., malformed JSON), the fallback sets COMMAND="git push". This could trigger self-review/test-guard checks unnecessarily. But the hooks' subsequent TRIGGERS regex check would catch non-push commands, and worst case the agent gets a review check — better than no enforcement.

### Tiger 2 — test-guard false positive in repos without testing: declaration
**Severity:** Low
**Status:** Mitigated

test-guard.sh already checks for `testing:` in PROJECT.md and exits 0 if absent. Adding it to the native pre-push hook doesn't change this behavior.

### Tiger 3 — KB BLOCKED: prefix triggers on advisory-only tags
**Severity:** Low
**Status:** Mitigated

The `BLOCKED:` prefix is only added when `knowledge_base:` is declared AND KB consultation is missing. Projects without knowledge_base: are unaffected.

**Implementation may proceed: YES**
