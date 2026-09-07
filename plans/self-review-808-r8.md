---
ticket_refs:
  - siege-analytics/claude-configs-public#808
---

# Self-review: PR for #808 R8 (source-module name-match + code consolidation)

## Assumptions

Working as: software engineer
Domain: scan_ast.py `_extract_optional_imports` — algorithm rewrite for import tracking + pairing
Goal source: siege-analytics/claude-configs-public#808 R8-F1..F6

R7's stem-strict single-flag path regressed the two most common Python optional-import idioms because name-match compared flag stem to import BINDING (`np`, `Image`) instead of SOURCE MODULE (`numpy`, `PIL`). R8 reviewer diagnosed structurally: separate the two concerns.

Investigate-artifact: sessions/260907-agile-delta/investigate-gate.json
Pre-mortem-artifact: plans/pre-mortem-808.md
Hostile-review-artifact: R8 reviewer's message + data/probe_impact.py

## Trivial-against-state declaration

Category: local-only
Cannot produce error: rewrite of the multi-import pairing logic + module-scope hoist of stem-strip helpers + 5 additive fixtures.
Evidence: git diff scoped to scan_ast.py + test_writing_code_8.sh + plans/self-review + pre-mortem.
Falsification: NOT trivial if any file outside skills/detect-ai-fingerprints/ + plans/ changed. Verified.

## Trivial-investigation declaration

Category: local-only
Cannot produce error: AST + string logic only. Determinism preserved.
Evidence: no external contact; verified across 5 canonical shapes inline.
Falsification: NOT trivial if any external resource contacted. Verified.

## Peer review

Gate 1 (syntax): python3 ast.parse -> ok.
Gate 2 (tests): test_writing_code_8 26/26 (21 prior + 5 R8 lock-ins). All 9 other suites unchanged.

Shelf compliance:
- writing-code:5: verified against 5 hand-tested shapes + reviewer's 19 probe cases.
- writing-tests:1: reverting the source_module tracking makes fixtures (v)-(y) regress.
- writing-claims:8: "26 pass" verified.

## Lead review

Algorithm:
1. Record each import as `(binding, source_module, lineno)` tuples. `import X` -> `(X, X)`; `import X as Y` -> `(Y, X)`; `from A import B` -> `(B, A)`; `from A import B as C` -> `(C, A)`. Dotted paths use first segment for source.
2. Name-match compares flag stem to source_module (not binding). `NUMPY_AVAILABLE` stem `NUMPY` matches source `numpy`; result binds `np -> NUMPY_AVAILABLE`.
3. Positional fallback pairs remaining imports to remaining flags by lineno when counts match.
4. Special single-remaining-flag rule: bind all remaining imports if AT LEAST ONE source_module stem-matches the sole flag; else fail open. This preserves R7-F2 misdirect protection (`re` bare + `MRE_AVAILABLE`: no source stem-matches MRE, fail open).
5. R8-F5: `_flag_stem` and `_name_matches_flag` hoisted to module scope; single copy for both paths.
6. R8-F6: `_HAS`, `_HAS_` dropped from `_FLAG_STEM_SUFFIX_STRIPS` (dead entries — no flag ending in `_HAS` or `_HAS_` can pass `_is_flag_name`).

R8-F4 (duplicate flag on single import) not addressed here; low severity, uncommon shape.

## Quantified claims

"26/26 pass on writing-code:8" — bash test_writing_code_8.sh -> Results: 26 passed, 0 failed.

"R7-F2 misdirect protection preserved" — verified inline: `import re` + `MRE_AVAILABLE` produces empty map + scan-ast-warning.

"9 other scanner suites unchanged" — verified inline.
