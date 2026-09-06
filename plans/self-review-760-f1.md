---
ticket_refs:
  - siege-analytics/claude-configs-public#760
---

# Self-review: PR for #760 F1 (writing-code:8 test isolation)

## Assumptions

Working as: software engineer
Domain: shell test file for AST scanner
Goal source: siege-analytics/claude-configs-public#760 finding F1 (Codex hostile review, 2026-09-06)
Pre-author-inventory: test_writing_code_8.sh was authored under #57 with `[ "$RC" = "0" ]` checks. Landing #56 (writing-tests:5 detector) then made those RC checks fail because writing-tests-5 now emits on the same fixtures. The test file's coupling to overall scanner rc was the bug; isolation to the writing-code-8 rule token is the fix.
Investigate-artifact: TRIVIAL (single-file test rewrite, same shape as the sibling test_writing_tests_5.sh which uses `fires_wt5()`)
Pre-mortem-artifact: TRIVIAL
Hostile-review-artifact: N/A (Codex hostile review IS what surfaced F1)
Project-contribution: unbreaks the writing-code:8 test suite on develop, closes the false "6/6 pass" claim in self-review-57.

## Trivial-against-state declaration

Category: local-only
Cannot produce error: test file rewrite only; no runtime code change; the new logic is a direct port of the isolation shape already shipped in test_writing_tests_5.sh.
Evidence: `git diff --stat` shows one file changed: skills/detect-ai-fingerprints/test_writing_code_8.sh.
Falsification: NOT trivial if it also changes any file outside skills/detect-ai-fingerprints/. Verified: single file.

## Peer review

Gate evidence:
- Gate 1 (syntax): `bash -n test_writing_code_8.sh` -> ok
- Gate 2 (tests): `bash skills/detect-ai-fingerprints/test_writing_code_8.sh` -> "6 passed, 0 failed", rc=0. Regression: `bash skills/detect-ai-fingerprints/test_writing_tests_5.sh` -> "6 passed, 0 failed", unchanged.
- Gate 3 (docs): N/A
- Gate 4 (notebooks): N/A

Shelf compliance:
- writing-code:5 (no hypothetical): tested against 6 fixtures.
- writing-tests:1 (tests fail on revert): reverting the isolation to `[ "$RC" = "0" ]` reproduces the 4/6 failure Codex found.
- writing-claims:8 (specific counts): "6/6 pass" — verified inline.

## Lead review

- Junior solved the stated goal: yes. Test isolation via `fires_wc8()` helper grepping specifically for the writing-code-8 token.
- Junior over-scoped: no. Did not touch scan_ast.py or fixture bodies.
- Junior under-scoped: F2-F5 (detector-logic soundness bugs in writing-code:8) are NOT fixed here — they're separate tickets under epic #760. This PR only fixes F1 (test-rc coupling).
- Standards affirmatively met: writing-code:5, writing-tests:1, writing-claims:8.

## Quantified claims

Claim: "6/6 test scenarios pass."
Verified-by: `bash skills/detect-ai-fingerprints/test_writing_code_8.sh` returns "Results: 6 passed, 0 failed", rc=0.

Claim: "no regression on test_writing_tests_5.sh."
Verified-by: `bash skills/detect-ai-fingerprints/test_writing_tests_5.sh` returns "Results: 6 passed, 0 failed", unchanged.

## Post-error revision

Triggered by: Codex hostile review, session 260906-ivory-finch, 2026-09-06, finding F1.
Observed: `bash test_writing_code_8.sh` returns rc=1 with 4/6 fixtures failing on develop after PR #754 (writing-tests:5) landed; scan_ast now emits writing-tests-5 on the writing-code:8 fixtures, breaking the `[ "$RC" = "0" ]` check.
Falsified assumption: self-review-57 assumed the test's rc=0 check would remain valid after landing sibling detectors. It did not.
Revised model: scanner test files that use rc-based checks are coupled to global scanner state; the correct isolation is per-rule token grep (`grep -q "writing-code-8"`), matching the pattern already used in test_writing_tests_5.sh.
Implication: apply the same isolation shape to any future scanner test files. self-review-57.md's "6/6 pass" quantified claim (writing-claims:8) is being retracted: at time of PR #752 merge it was true against develop-of-2026-09-05; it became false after PR #754 (writing-tests:5) merged. The self-review artifact is preserved with this Post-error revision as the trigger record.
