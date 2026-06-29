---
ticket_refs:
  - siege-analytics/claude-configs-public#524
  - siege-analytics/claude-configs-public#525
---
# Pre-mortem: #524 + #525 — WARNING-to-BLOCK promotions

## Risks

### Tiger 1 — Promote commits break without exemption (#524)
**Severity:** Medium
**Status:** Mitigated

Promote commits use `Self-Review: promote merge` + `[no-review]` but no `Design-Note-Source:`. Without exemption, all promote pushes would be blocked.

**Mitigation:** Added `[no-review]` exemption check wrapping the Design-Note-Source block. Promote commits include `[no-review]` and are exempt.

### Tiger 2 — Severity regex breaks other formats (#525)
**Severity:** Low
**Status:** Mitigated

The fixed regex `\*?\*?severity:\*?\*?` adds optional markdown bold markers. This matches both `Severity:` (plain) and `**Severity:**` (bold). Tested against both formats — both match.

### Paper Tiger 1 — Old pre-mortems fail retroactively
**Severity:** Low (Paper Tiger)

Pre-push hook only checks pre-mortems referenced by the CURRENT commit. Old pre-mortems are not rechecked.

**Implementation may proceed: YES**
