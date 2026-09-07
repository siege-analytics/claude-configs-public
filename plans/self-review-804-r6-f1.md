---
ticket_refs:
  - siege-analytics/claude-configs-public#804
---

# Self-review: PR for #804 R6-F1 (name-based pairing + positional fallback)

## Assumptions

Working as: software engineer
Domain: scan_ast.py `_extract_optional_imports` multi-flag pairing
Goal source: siege-analytics/claude-configs-public#804 R6-F1

R5's nearest-following-line pairing handled interleaved import/flag order but broke on grouped shape (all imports, then all flags). Round 6 reviewer's V2 fixture (pandas + geopandas top of try, flags below) demonstrated three failure modes on the R5 code:
- False positive: correctly-guarded geopandas fires wc-8.
- False negative: geopandas guarded by PANDAS_AVAILABLE silently accepted.
- Wrong-flag suggestion: emission text names the wrong flag.

Investigate-artifact: plans/pre-mortem-804.md (structural)
Pre-mortem-artifact: plans/pre-mortem-804.md
Hostile-review-artifact: R6 reviewer's message (archived in session 260525-long-swan history)

## Trivial-against-state declaration

Category: local-only
Cannot produce error: change scoped to `_extract_optional_imports` multi-flag branch plus 4 additive fixtures.
Evidence: git diff shows scan_ast.py + test_writing_code_8.sh + plans/self-review-804 + plans/pre-mortem-804.
Falsification: NOT trivial if any file outside skills/detect-ai-fingerprints/ + plans/ changed. Verified.

## Trivial-investigation declaration

Category: local-only
Cannot produce error: AST + regex logic only. Determinism preserved (sorted lineno; deterministic name match).
Evidence: no external contact.
Falsification: NOT trivial if any external resource is contacted. Verified.

## Peer review

Gate 1 (syntax): python3 ast.parse -> ok.
Gate 2 (tests): test_writing_code_8 18/18 (14 prior + 4 R6-F1 lock-ins). All 9 other suites unchanged.

Shelf compliance:
- writing-code:5 (no hypothetical): verified against 4 fixtures + reviewer's original V2 fixture.
- writing-tests:1 (tests fail on revert): reverting name-match makes fixture (o) fire wrong-flag; reverting positional fallback makes fixture (r) emit scan-ast-warning + no mapping.
- writing-claims:8: "18 pass" verified.

## Lead review

Algorithm rewrite:
1. **Name-match phase**: for each import, look for a flag whose stem contains the import name uppercased as a whole word (`\b<NAME>\b`). Word-boundary prevents substring false-matches like `re` inside `MRE_AVAILABLE`. If exactly one name-match, bind and remove that flag from the pool. Multiple matches or zero matches leave the import "pending".
2. **Positional fallback**: if the remaining pending imports count equals the remaining unmatched flags count, pair by lineno order. Handles the aliased case (`import pandas as pd; import geopandas as gpd; PANDAS_AVAILABLE = ...; GEOPANDAS_AVAILABLE = ...`) where name-match fails but positional works.
3. **Fail-open**: if imports still pending after both phases, emit `scan-ast-warning` on stderr and drop tracking for those imports. False negatives are safer than false positives with wrong-flag suggestions.

Single-flag fast path preserved for all existing single-import fixtures.

R6-F1 fix demonstrated on:
- V2 grouped correctly-guarded → silent
- V2 grouped wrong-flag → fires on truly-unguarded name with correct suggested flag
- 3+3 grouped fixture → silent
- Aliased imports positional fallback → silent

## Quantified claims

"18/18 pass on writing-code:8" — bash test_writing_code_8.sh returns Results: 18 passed, 0 failed, rc=0.

"V2 fixture map correct: pandas → PANDAS_AVAILABLE, geopandas → GEOPANDAS_AVAILABLE" — verified inline; before fix, both mapped to PANDAS_AVAILABLE.

"9 other scanner suites unchanged" — verified inline.
