---
ticket_refs:
  - siege-analytics/claude-configs-public#771
---

# Self-review: PR for #771 m-6 (_is_test_path segment-anchored)

## Assumptions

Working as: software engineer
Domain: scan_ast.py path classification (_is_test_path used by writing-tests:5 exemption + writing-code:15 --exclude-tests)
Goal source: siege-analytics/claude-configs-public#771 m-6
Pre-author-inventory: `TEST_PATH_PATTERNS = ("/tests/", "/test/", "_test.py", "test_")` with `any(pat in p for pat in ...)` substring match; `test_` matched anywhere in the path, so `tester_lib.py`, `tests_helper.py`, `foo/tester_lib.py` all classified as test paths, causing writing-tests:5 to exempt them and writing-code:15 to skip them when --exclude-tests was passed.

Investigate-artifact: TRIVIAL
Pre-mortem-artifact: TRIVIAL
Hostile-review-artifact: Round 2 hostile review m-6, session 260906-fit-whale.
Project-contribution: closes a false-positive path classifier; adds dedicated test file `test_is_test_path.sh`.

## Trivial-against-state declaration

Category: local-only
Cannot produce error: single-file logic change (segment-anchored match) + one new test file.
Evidence: `git diff --stat` shows scan_ast.py + test_is_test_path.sh + this self-review.
Falsification: NOT trivial if any file outside skills/detect-ai-fingerprints/ + plans/ changed. Verified.

## Trivial-investigation declaration

Category: local-only
Cannot produce error: read-only path-classifier logic + shell test.
Evidence: diff scope confirmed via git diff --stat.
Falsification: NOT trivial if any external resource is contacted. Verified: only Path() operations on string paths.

## Peer review

Gate evidence:
- Gate 1 (syntax): python3 ast.parse -> ok; bash -n test_is_test_path.sh -> ok
- Gate 2 (tests): bash test_is_test_path.sh -> "13 passed, 0 failed". Regressions: writing-code:7 8/8, writing-code:8 12/12, writing-code:15 9/9, writing-tests:5 17/17, scan_sh_exit_code 10/10, rule-citations PASS.
- Gate 3 (docs): TEST_PATH_DIR_SEGMENTS and TEST_PATH_SUFFIXES named after their semantics; `_is_test_path` docstring names the boundary rule and the m-6 anti-pattern set. `TEST_PATH_PATTERNS` retained as a back-compat alias so any external consumer that greps for it still finds it.
- Gate 4 (notebooks): N/A

Shelf compliance:
- writing-code:5 (no hypothetical): 13 fixtures cover the boundary shapes.
- writing-code:7 (no silent swallow): no except handlers added.
- writing-tests:1 (tests fail on revert): reverting to substring match causes fixtures (g)-(l) to flip.
- writing-claims:8 (specific counts): "13 passed, 0 failed" verified inline.

## Lead review

- Junior solved the stated goal: yes. Anchored path-segment match rejects mid-name occurrences of `test_`; still accepts basename-prefixed `test_` and `_test.py` suffix and `/tests/` / `/test/` directory segments.
- Junior over-scoped: no.
- Junior under-scoped: does not handle Windows-style backslashes. Author-time decision: this scanner runs on Linux/macOS pathlib.Path outputs; if a Windows consumer surfaces, extend `TEST_PATH_DIR_SEGMENTS` to include `\\tests\\` and `\\test\\`. Deferred.
- Standards affirmatively met: writing-code:5, writing-code:7, writing-tests:1, writing-claims:8.

## Quantified claims

Claim: "13/13 pass on the new boundary test."
Verified-by: bash test_is_test_path.sh -> "Results: 13 passed, 0 failed", rc=0.

Claim: "no regression on the five other scanner test scripts."
Verified-by: all five pass unchanged (writing-code:7 8/8, writing-code:8 12/12, writing-code:15 9/9, writing-tests:5 17/17, scan_sh_exit_code 10/10, rule-citations PASS).
