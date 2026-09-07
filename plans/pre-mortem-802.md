---
ticket_refs:
  - siege-analytics/claude-configs-public#802
---

# Pre-mortem: PR for #802 (Round 5 R5-F1 + R5-F2)

## Status: Cleared

Implementation may proceed: YES.

## Context

Round 5 hostile review (GPT-5.5) returned NOT GREEN with three findings. R5-F1 is a MEDIUM correctness bug in `_extract_optional_imports`: non-deterministic multi-import-to-flag mapping in try blocks that declare 2+ imports and 2+ availability flags. R5-F2 is a LOW-severity stale docs tail after R4-F1/F2/F3 rewrite. R5-F3 is a ticket-body wording issue on issue #801 (handled via GH issue edit, not this PR).

## Risk classification

**Severity: Elephant 1** — regression in the single-import case.
Description: `_extract_optional_imports` is the entry point for the writing-code:8 detector. Changing its per-import pairing algorithm risks breaking the 12 existing fixtures that all use single-import shapes.
Mitigation: Keep the single-import behavior identical. Pairing logic only activates when there are ≥2 imported names in a try block. Verify all 12 existing test_writing_code_8 fixtures still pass.

**Severity: Paper Tiger 2** — the "nearest following flag" pairing heuristic misclassifies a legitimate try block.
Description: If someone writes `import X; FLAG_X = True; import Y; FLAG_X = True` (two imports one flag), the pairing algorithm binds both to FLAG_X. That is correct behavior. But `import X; import Y; FLAG_X = True; FLAG_Y = True` (imports first, flags after) would need order-independent matching.
Mitigation: use lineno-order within the try body. Assign each import to the flag set on the smallest line number strictly greater than the import's line number. Fixture-tested with both orderings.

**Severity: Paper Tiger 3** — R5-F2 docs rewrite introduces a new stale item.
Description: SKILL.md was previously touched in R3-F6 and R4-F1/F2/F3 and each pass missed items. Odds of a fifth pass leaving a stale tail non-zero.
Mitigation: Grep verify each targeted change before commit; reviewer noted the specific line numbers.

## Rollback

`git revert` of the merged PR restores the pre-R5 state. writing-code:8 detector remains functional (with the R5-F1 non-determinism).
