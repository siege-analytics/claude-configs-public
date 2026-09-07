---
ticket_refs:
  - siege-analytics/claude-configs-public#810
---

# Pre-mortem: PR for #810 (R9-F1/F2/F3 three-fix pass)

## Status: Cleared. Implementation may proceed: YES.

## Context

R8's source-module refactor fixed the aliased-import regression but Round 9 verified three more shapes still fail. F1 dotted-source truncation; F2 flag consumed by first same-source binding; F3 positional fallback manufactures wrong-flag suggestions.

## Risks

**Severity: Elephant 1** — Regression on 26 existing writing-code:8 fixtures.
Mitigation: Run test after each change. Positional fallback still fires for cases where at-least-one stem-match happens (that's the aliased-imports-with-alias case that motivated positional fallback originally).

**Severity: Paper Tiger 2** — R9-F3 fix makes multi-flag positional fallback narrower. Could regress a shape that R6/R7 fixtures depended on.
Mitigation: Trace each existing multi-flag fixture. Fixture (i) numpy+pandas grouped — both have name-match on NUMPY / PANDAS stems, so positional fallback isn't needed. Fixture (r) aliased pd+gpd — name-match won't hit (source is `pandas` matching `PANDAS_AVAILABLE` stem — actually match!). Verify inline.

**Severity: Paper Tiger 3** — R9-F1 fix (normalize `.` and `_` in stem comparison) could accidentally match unrelated flags. E.g., `import a.b` + `A_B_C_AVAILABLE`? Stem `A_B_C` (5 chars minus underscores = ABC); source `a.b` (dots stripped = ab). Not equal. Good.
Mitigation: verify inline.

## Rollback

`git revert` restores R8's behavior; R9-F1/F2/F3 regressions return but no new bug.
