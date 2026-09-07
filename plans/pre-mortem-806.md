---
ticket_refs:
  - siege-analytics/claude-configs-public#806
---

# Pre-mortem: PR for #806 (R7-F1 + R7-F2 stem-based name matching)

## Status: Cleared. Implementation may proceed: YES.

## Context

R6 introduced name-based pairing with a `\b<NAME>\b` regex. R7 diagnosed that `\b` treats `_` as a word char in Python regex, so the regex never matches conventional flag names like `PANDAS_AVAILABLE`. Every multi-flag block was falling through to positional fallback, hiding the name-match feature entirely. When flag order differs from import order, mispairing produces false positives with wrong-flag suggestions.

## Risks

**Severity: Elephant 1** — Regression on the 18 existing writing-code:8 fixtures.
Description: The name-match algorithm rewrite touches the core pairing logic. All 18 lock-ins must still pass.
Mitigation: Run test_writing_code_8.sh after the change.

**Severity: Paper Tiger 2** — Stem-strip loses information.
Description: Stripping `_AVAILABLE`, `HAS_`, `_HAS_`, `_INSTALLED` from a flag before comparison could produce empty or ambiguous stems. `HAS__AVAILABLE` (unlikely but possible) strips to nothing.
Mitigation: If stem is empty after strip, treat as name-mismatch and fall through.

**Severity: Paper Tiger 3** — Import name is a case-sensitive Python identifier; flag is UPPERCASE convention.
Description: Comparing case-insensitively is correct, but `Import` (capitalized module) is rare. Non-ASCII identifiers (unicode module names) exist in Python 3 and would break case-folding.
Mitigation: Case-fold via `.casefold()` which handles unicode; check ASCII assumption is preserved in `_is_flag_name`.

## Rollback

`git revert` restores R6's broken `\b` regex + positional fallback. False negatives via positional fallback on reversed-order files still exist but no NEW regression.
