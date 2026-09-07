---
ticket_refs:
  - siege-analytics/claude-configs-public#771
---

# Self-review: PR for #771 m-2 + writing-code:7 noqa sibling

## Assumptions

Working as: software engineer
Domain: writing-code:7 detector (silent error swallowing)
Goal source: siege-analytics/claude-configs-public#771 m-2 and noqa-sibling
Pre-author-inventory: `check_writing_code_7` detected only body-len ∈ {1, 2} shapes. Body `[log, y=None, return None]` (len 3) escaped despite being silent-swallow with decoy assign. `has_noqa_writing_code_7` accepted bare `# noqa: writing-code-7` without any reason — mirror of M-3 for writing-tests:5.

Investigate-artifact: TRIVIAL
Pre-mortem-artifact: TRIVIAL
Hostile-review-artifact: Round 2 m-2 + writing-code:7 noqa-weak note.
Project-contribution: extends detector to body-len ≥ 3 via `_is_swallow_scaffold` predicate; tightens noqa reason regex to same vowel-lookahead shape as writing-tests:5 M-3 fix.

## Trivial-against-state declaration

Category: local-only
Cannot produce error: two detector edits + additive fixtures.
Evidence: `git diff --stat` shows scan_ast.py + test_writing_code_7.sh + this self-review.
Falsification: NOT trivial if any file outside skills/detect-ai-fingerprints/ + plans/ changed. Verified.

## Trivial-investigation declaration

Category: local-only
Cannot produce error: read-only AST predicate + regex.
Evidence: no external contact.
Falsification: NOT trivial if any external resource is contacted. Verified.

## Peer review

Gate evidence:
- Gate 1 (syntax): python3 ast.parse -> ok
- Gate 2 (tests): bash test_writing_code_7.sh -> "13 passed, 0 failed" (8 prior + 5 lock-ins). Regressions: all 9 other test suites unchanged.
- Gate 3 (docs): `_is_swallow_scaffold` docstring names m-2 by ticket + the scaffold shapes (logging call, constant-value Assign); `has_noqa_writing_code_7` docstring names the sibling of M-3.
- Gate 4 (notebooks): N/A

Shelf compliance:
- writing-code:5: verified against 5 new fixtures.
- writing-code:7: fix is TO the writing-code:7 detector; no new except handlers introduced.
- writing-tests:1: reverting `_is_swallow_scaffold` makes (i) and (m) silent; reverting regex makes (k) and (l) silent.
- writing-claims:8: "13 passed" verified.

## Lead review

- Junior solved the stated goal: yes. m-2 extends detection to any body length where the last statement is a silent terminator AND every earlier statement is scaffold (logging or constant assign). Real cleanup calls break scaffold and keep the handler silent.
- Junior over-scoped: no.
- Junior under-scoped: `_is_swallow_scaffold` treats any `Name = Constant` as scaffold. If someone writes `important_flag = True` inside an except, that's technically a state mutation but the detector will consider it scaffold. Author-time decision: real state-mutating code inside except handlers is rare enough that this false-positive risk is acceptable; a stricter predicate (e.g., only scaffold if the Assign target is not read after the handler) would require flow analysis.
- Standards affirmatively met: writing-code:5, writing-code:7, writing-tests:1, writing-claims:8.

## Quantified claims

Claim: "13/13 pass on writing-code:7 (8 prior + 5 lock-ins)."
Verified-by: bash test_writing_code_7.sh -> "Results: 13 passed, 0 failed", rc=0.
