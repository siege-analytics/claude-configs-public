---
ticket_refs:
  - siege-analytics/claude-configs-public#804
---

# Pre-mortem: PR for #804 (R6-F1 name-based pairing)

## Status: Cleared. Implementation may proceed: YES.

## Context

R5 shipped nearest-following-line pairing to fix multi-import non-determinism. Round 6 verified it works for interleaved import/flag order but breaks on the grouped shape (all imports, then all flags). Rewriting to name-based pairing with positional fallback.

## Risks

**Severity: Elephant 1** — single-import regression. 14 existing writing-code:8 fixtures use single-import shapes. The name-based algorithm must handle the single-flag case identically.
Mitigation: Preserve the single-flag fast path. Run all 14 fixtures before commit.

**Severity: Paper Tiger 2** — false negatives from fail-open. If name-match AND positional fallback both fail, dropping the try block from tracking means writing-code:8 won't fire anywhere in that file for those imports.
Mitigation: Emit `scan-ast-warning` on stderr so the operator sees the fail-open. Rare shape (only fires on 3+ imports with 3+ flags where names don't match and count parity fails).

**Severity: Paper Tiger 3** — name-match heuristic misclassifies. `import re` looking for `RE_AVAILABLE` matches, but `import mre` looking for `MRE_AVAILABLE` would also match `RE_AVAILABLE` by substring. Solution: require the import name to appear as a WHOLE word in the flag (uppercased), delimited by non-word chars.
Mitigation: Use `re.search(r"\b" + name.upper() + r"\b", flag)` for name matching.

## Rollback

`git revert` restores R5's pairing. writing-code:8 grouped-shape false-positive returns but no new regression.
