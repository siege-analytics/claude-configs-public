# Hostile review: compact safety kernel

## Scope

Independent review of kernel semantics, precedence, build integration, source authority, budget/structure validator, fixtures, and the explicit no-runtime-cutover boundary.

## Round 1

Found contradictory project/user precedence, generated artifacts not semantically bound to the validated source, source symlink acceptance after resolution, permissive invariant headings, and literal-only shelf guards.

Resolution: matching overlays precede user execution preferences in declared scope; conflicts ask. Artifacts are checked against generated-source authority. Source chains are checked before resolution. All K-number headings must exactly equal K1 through K10. Shelf-globalization prose receives explicit negative guards, documented as heuristic until resolver enforcement.

## Round 2

Found that the budget command trusted the authority catalog without independently proving it fresh, so coordinated artifact/catalog edits could pass the budget command in isolation.

Resolution: every budget write/check first runs `generated-source-authority.py --check`, which validates inventory, performs a fresh isolated build, and compares the authority catalog. A negative fixture proves failure propagates closed.

## Round 3

Final focused review found no remaining S1/S2 issues.

## Final disposition

The candidate kernel contains exactly ten invariants, is 6,944 characters / 1,736 estimated tokens, remains below both hard budgets, preserves project-overlay authority beneath the narrow safety boundary, and explicitly states that progressive-loading runtime cutover has not occurred.
