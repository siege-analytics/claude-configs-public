---
ticket_refs:
  - siege-analytics/claude-configs-public#806
---

# Self-review: PR for #806 R7-F1 + R7-F2 (stem-based name matching)

## Assumptions

Working as: software engineer
Domain: scan_ast.py `_extract_optional_imports` name-matching + single-flag fast path
Goal source: siege-analytics/claude-configs-public#806

R6's `_name_matches_flag` used `r"\b" + name.upper() + r"\b"`. Python regex treats `_` as a word char, so `\bPANDAS\b` never matches `PANDAS_AVAILABLE`. Name-based matching was silently dead; everything fell to positional fallback. Reversed-flag-order fixtures mispaired.

R7-F2: single-flag fast path bypassed the stem check entirely — `import re` + `MRE_AVAILABLE` bound unconditionally with wrong-flag suggestion.

Investigate-artifact: sessions/260907-zesty-meteor/investigate-gate.json
Pre-mortem-artifact: plans/pre-mortem-806.md
Hostile-review-artifact: R7 reviewer's message

## Trivial-against-state declaration

Category: local-only
Cannot produce error: scoped change to name-match helper + 3 fixtures.
Evidence: git diff shows scan_ast.py + test_writing_code_8.sh + this self-review + pre-mortem.
Falsification: NOT trivial if any file outside skills/detect-ai-fingerprints/ + plans/ changed. Verified.

## Trivial-investigation declaration

Category: local-only
Cannot produce error: read-only string manipulation + AST logic.
Evidence: no external contact.
Falsification: NOT trivial if any external resource is contacted. Verified.

## Peer review

Gate 1 (syntax): python3 ast.parse -> ok.
Gate 2 (tests): test_writing_code_8 21/21 (18 prior + 3 R7 lock-ins). Regressions: all 9 other suites unchanged.

Shelf compliance:
- writing-code:5: verified against 5 hand-tested cases (reversed flags, numpy family, PIL from-import, re/MRE mismatch, shapely).
- writing-tests:1: reverting stem match makes fixture (s) mispair, fixture (t) mispair; reverting single-flag stem check makes fixture (u) emit false-positive.
- writing-claims:8: "21 pass" verified.

## Lead review

Stem-strip algorithm:
1. Strip leading `HAS_`, `_HAS_`, or `_` from the flag.
2. Strip trailing `_AVAILABLE`, `_INSTALLED`, `_HAS`, `_HAS_`.
3. Casefold both stem and import name.
4. Match if `stem == imp` OR `stem.replace("_", "") == imp.replace("_", "")` (handles `NUMPY_FINANCIAL` <-> `numpy_financial`).

Single-flag path: applies the same stem match; fails open with `scan-ast-warning` when the sole flag doesn't stem-match any import.

R7-F1 reproduction now correctly pairs pandas -> PANDAS_AVAILABLE and geopandas -> GEOPANDAS_AVAILABLE regardless of flag declaration order. R7-F2 reproduction fails open with a scan-ast-warning instead of binding to the wrong flag.

## Quantified claims

"21/21 pass on writing-code:8" — bash test_writing_code_8.sh returns Results: 21 passed, 0 failed, rc=0.

"5 hand-tested cases behave correctly" — verified inline: reversed-order, numpy+numpy_financial, PIL from-import, re+MRE fail-open, shapely single-import baseline.

"9 other scanner suites unchanged" — verified inline.
