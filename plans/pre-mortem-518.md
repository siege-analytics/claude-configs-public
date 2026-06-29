---
ticket_refs:
  - siege-analytics/claude-configs-public#518
---
# Pre-mortem: #518 — Gate 1-4 evidence enforcement

## Risks

### Tiger 1 — Evidence regex too broad
**Severity:** Medium
**Status:** Mitigated

The word "pass" or "clean" could appear in explanatory prose, not as gate evidence output. A Peer review section discussing "this passed review" would match.

**Mitigation:** The regex targets output-format markers unlikely in non-evidence prose: `exit 0` (shell output), the arrow character (command-to-result separator), `N/A` (explicit non-applicability), and `[no-gates]` as explicit declaration. Prose matches for "pass" or "clean" are acceptable false passes — they indicate the reviewer engaged. A false BLOCK (preventing a legitimate push) is much worse than a false pass.

### Paper Tiger 1 — Existing self-reviews break on re-push
**Severity:** Low (Paper Tiger)

Old self-reviews already pushed won't be re-checked. The pre-push hook only examines commits being pushed, not historical ones.

### Tiger 2 — no-gates bypass as escape hatch
**Severity:** Low
**Status:** Mitigated

`[no-gates]` could become a universal bypass if agents insert it routinely.

**Mitigation:** The string is distinctive and grep-able. Monitoring `grep -r 'no-gates' plans/` catches abuse. If detected, a follow-up ticket can restrict the bypass to specific contexts.

**Implementation may proceed: YES**
