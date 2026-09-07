---
ticket_refs:
  - siege-analytics/claude-configs-public#810
---

# Self-review: PR for #810 R9-F1 + R9-F2 + R9-F3

## Assumptions

Working as: software engineer
Domain: scan_ast.py `_extract_optional_imports`
Goal source: siege-analytics/claude-configs-public#810

Three defects in R8's algorithm surfaced by Round 9:
- R9-F1 dotted source truncation: `from foo.bar import baz` + `FOO_BAR_AVAILABLE` failed to pair.
- R9-F2 flag consumed by first same-source binding: `import numpy; import numpy as np` only bound one.
- R9-F3 positional fallback manufactured wrong-flag suggestions when no stems matched.

Investigate-artifact: sessions/260907-wide-horse/investigate-gate.json
Pre-mortem-artifact: plans/pre-mortem-810.md

## Trivial-against-state declaration

Category: local-only
Cannot produce error: pairing algorithm rewrite + source_module recording change + 3 fixtures.
Evidence: git diff.
Falsification: NOT trivial if any file outside skills/detect-ai-fingerprints/ + plans/ changed. Verified.

## Trivial-investigation declaration

Category: local-only
Cannot produce error: AST + string logic.
Evidence: no external contact.
Falsification: NOT trivial if any external resource contacted. Verified.

## Peer review

Gate 1 (syntax): python3 ast.parse -> ok.
Gate 2 (tests): test_writing_code_8 29/29 (26 prior + 3 R9 lock-ins). Regressions: 9 other suites unchanged.

Shelf compliance:
- writing-code:5: 6 hand-tested cases + fixture-per-finding.
- writing-tests:1: reverting each of the 3 fixes makes the corresponding new fixture regress.
- writing-claims:8: "29 pass" verified.

## Lead review

R9-F1: store `alias.name` (full dotted path) as source. `_name_matches_flag` normalizes `.` and `_` equivalently when the direct case-folded compare fails.

R9-F2: phase-1 groups imports by source_module first. Each source group finds its single stem-matching flag and binds ALL bindings in that group to it. `import numpy; import numpy as np` — both share source `numpy`, both bind to `NUMPY_AVAILABLE`.

R9-F3: multi-flag positional fallback now gated on `phase1_matched_any`. If no phase-1 name-match happened, positional pairing is unreliable — fail open with warning. Sole-flag path unchanged (still checks stem-match per R7-F2 protection).

R7-F2 preservation verified: `import re` + `MRE_AVAILABLE` still fails open (`re` source no stem-match; sole-flag any_match=False).

R8 shapes still work: `import numpy as np` + `NUMPY_AVAILABLE`, `from PIL import Image` + `PIL_AVAILABLE` both bind correctly.

## Quantified claims

"29/29 pass on writing-code:8" — verified inline.
"9 other scanner suites unchanged" — verified inline.
"R7-F2 misdirect protection preserved" — verified inline: `re` + `MRE_AVAILABLE` empty map + scan-ast-warning.
