---
ticket_refs:
  - siege-analytics/claude-configs-public#787
---

# Self-review: PR for #787 R3-F2 (writing-code:15 rejects invalid timeout literals)

## Assumptions

Working as: software engineer
Domain: writing-code:15 detector — timeout kwarg validation
Goal source: siege-analytics/claude-configs-public#787 R3-F2
Pre-author-inventory: detector had 3 subshapes — missing-timeout, timeout-none-no-audit-comment, timeout-zero. `timeout=False` (bool that isn't None) and `timeout=()` (empty tuple) both passed silently despite being functionally unbounded.

Investigate-artifact: TRIVIAL
Pre-mortem-artifact: TRIVIAL

## Trivial-against-state declaration

Category: local-only
Cannot produce error: 2 new subshape branches + 5 lock-in fixtures.
Evidence: `git diff --stat`.
Falsification: NOT trivial if any file outside skills/detect-ai-fingerprints/ + plans/ changed. Verified.

## Trivial-investigation declaration

Category: local-only
Cannot produce error: read-only AST predicate additions.
Evidence: no external contact.
Falsification: NOT trivial if any external resource is contacted. Verified.

## Peer review

Gate 1 (syntax): python3 ast.parse -> ok.
Gate 2 (tests): test_writing_code_15 23/23 (18 prior + 5 R3-F2 lock-ins). Regressions: all 9 other suites unchanged.

Shelf compliance:
- writing-code:5 (no hypothetical): verified against 5 fixtures.
- writing-tests:1 (tests fail on revert): reverting the R3-F2 branches makes (s), (t), (v), (w) silent.
- writing-claims:8 (specific counts): "23 passed" verified inline.

## Lead review

Standards met: writing-code:5, writing-tests:1, writing-claims:8. Two new emission subshapes documented in the code + surface names use `ast.unparse` to name the invalid literal precisely.

## Quantified claims

"23/23 pass" — bash test_writing_code_15.sh returns Results: 23 passed, 0 failed, rc=0.
