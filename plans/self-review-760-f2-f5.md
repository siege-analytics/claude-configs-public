---
ticket_refs:
  - siege-analytics/claude-configs-public#760
---

# Self-review: PR for #760 F2-F5 (writing-code:8 detector soundness)

## Assumptions

Working as: software engineer
Domain: Python AST scanner (skills/detect-ai-fingerprints/scan_ast.py) — writing-code:8 detector
Goal source: siege-analytics/claude-configs-public#760 findings F2-F5 (Codex hostile review, session 260906-ivory-finch, 2026-09-06)
Pre-author-inventory: `check_writing_code_8` and its helpers (~180 lines) landed in PR #752 with four unsoundness bugs. All four verified locally against Codex's reproductions before this fix.

Investigate-artifact: TRIVIAL (see below)
Pre-mortem-artifact: TRIVIAL (see below)
Hostile-review-artifact: Codex session 260906-ivory-finch delivered the findings this PR fixes. Reproductions rerun locally.
Project-contribution: makes the writing-code:8 detector actually enforce the rule as documented. Before this PR, four accepted-guard shapes were false-positives (the code was unsafe but the scanner said silent).

## Trivial-against-state declaration

Category: local-only
Cannot produce error: single-file Python change to the AST scanner + additive test cases; no runtime code path in production consumers touched here.
Evidence: `git diff --stat` shows scan_ast.py + test_writing_code_8.sh + this self-review.
Falsification: NOT trivial if any file outside skills/detect-ai-fingerprints/ + plans/ changed. Verified.

## Trivial-investigation declaration

Category: local-only
Cannot produce error: no external state (data shape, config, cluster topology, plan complexity, version resolution) contacted. The detector runs read-only ast walks; the test fixtures are mktemp'd + torn down.
Evidence: `git diff --stat` shows only the two source files + one plan file; grep for `subprocess|open(|requests|urllib` in the diff returns nothing.
Falsification: NOT trivial if any external resource is read or written. Verified: only mktemp -d writes.

## Peer review

Gate evidence:
- Gate 1 (syntax): `python3 -c "import ast; ast.parse(open('skills/detect-ai-fingerprints/scan_ast.py').read())"` -> ok
- Gate 2 (tests): `bash skills/detect-ai-fingerprints/test_writing_code_8.sh` -> "12 passed, 0 failed" (original 6 + 6 new Codex lock-ins). Regressions: `bash test_writing_tests_5.sh` -> unchanged 6/6, `bash test_rule_citations.sh` -> unchanged PASS.
- Gate 3 (docs): detector-body comments updated to reference F2-F5 by ticket. Function docstrings restated to name the invariant each check enforces.
- Gate 4 (notebooks): N/A

Shelf compliance:
- writing-code:5 (no hypothetical): each fix has a concrete Codex reproduction that surfaces the bug; the new fixtures (g), (h), (i), (j), (k), (l) lock them in.
- writing-code:7 (no silent swallow): no except blocks added in this diff.
- writing-tests:1 (tests fail on revert): reverting the F2 fix causes fixture (g) to go silent → fail; reverting F3 causes (h) to go silent → fail; reverting F4 causes (i) → fail; reverting F5 causes (j) → fail. Each new fixture is bound to its own fix.
- writing-claims:8 (specific counts): "12 passed, 0 failed" — verified inline; 6 old + 6 new = 12.

## Lead review

- Junior solved the stated goal: yes, four bugs, four fixes, six lock-in fixtures. F5's counterpart fixture (k) verifies the "caller-contract phrase" path still admits legitimate private helpers. F2's counterpart (l) verifies the else-branch of `if not FLAG:` IS still recognized as guarded.
- Junior over-scoped: no. F6-F8 (writing-tests:5 detector) are a separate PR under this epic. F11 (baseline/ratchet) is separately filed.
- Junior under-scoped: known limitations — canonical polarity check only recognizes `FLAG` and `not FLAG`; comparison forms (`FLAG == True`, `FLAG is None`) and truthy checks via `bool(FLAG)` are not recognized. Author-time decision: comparison forms are lint-flaggable at a different layer; the primary shape the rule text calls out is `if [not] FLAG:`. If a downstream consumer writes `if FLAG == True: use()`, the scanner will flag it (unrecognized guard shape). That's a stricter-not-looser outcome, which is safe.
- Standards affirmatively met: writing-code:5, writing-code:7, writing-tests:1, writing-claims:8.

## Quantified claims

Claim: "12/12 test scenarios pass, 6 original + 6 new Codex lock-in."
Verified-by: `bash skills/detect-ai-fingerprints/test_writing_code_8.sh` returns "Results: 12 passed, 0 failed", rc=0.

Claim: "no regression on test_writing_tests_5.sh or test_rule_citations.sh."
Verified-by: both scripts run to their existing PASS outputs unchanged.

## Post-error revision

Triggered by: Codex hostile review, session 260906-ivory-finch, 2026-09-06, findings F2-F5.
Observed: four reproductions Codex ran silently succeeded when scanner should have fired. Each traced to a specific detector helper:
- F2: `_guarded_by_flag` was branch-blind (used ast.walk to find flag name anywhere in the test).
- F3: `_if_establishes_flag` treated `if FLAG: return` as establishing FLAG truthy on fallthrough (it establishes falsy).
- F4: same function accepted `if FLAG and other:` as canonical, when compound tests can't prove polarity.
- F5: `_private_helper_documents_flag` accepted any docstring containing the flag name.

Falsified assumption: self-review-57 asserted the detector recognized "the canonical `if not FLAG: raise` and `if FLAG: ...; else: raise` shapes." The recognition logic accepted more than that (F3, F4) and less than that with polarity (F2), and the private-helper doc contract was under-specified (F5). Author-time inventory did not enumerate the full test matrix; that's the primary discipline miss.

Revised model:
- Guard-detection is branch-aware polarity analysis: only `if FLAG:` body OR `if not FLAG:` else establishes flag-truthy.
- Establish-flag on fallthrough requires canonical polarity + terminator in the opposite branch: `if not FLAG: terminate` OR `if FLAG: ...; else: terminate`.
- Private-helper docstring must both name the flag AND carry a caller-contract phrase from a controlled vocabulary (`caller must check`, `caller has checked`, `caller ensures`, `assumes the caller`, etc.).
- The invariant established after an if-statement applies to statements FOLLOWING the if, not to the if-body itself (F2 fix: reorder in `_visit_block` — visit stmt first, then push the established guard).

Implication: any future detector authored for the same "flag-guarded callsite" family must specify (a) which if-test shapes are canonical, (b) which branch of each shape implies the invariant, (c) where in the visit order the invariant becomes active. Adopting these three as design axes for future detectors is the follow-on discipline.
