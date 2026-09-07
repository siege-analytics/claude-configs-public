---
ticket_refs:
  - siege-analytics/claude-configs-public#771
---

# Self-review: PR for #771 m-5 (writing-code:15 rejects timeout=0)

## Assumptions

Working as: software engineer
Domain: writing-code:15 detector — timeout kwarg validation
Goal source: siege-analytics/claude-configs-public#771 m-5
Pre-author-inventory: `check_writing_code_15` accepted any `timeout=<Constant>` as a valid bound; `timeout=0` and `timeout=0.0` semantically raise TimeoutExpired / fail immediately, functionally equivalent to unbounded from the "protect against runaway I/O" perspective. Reviewer flagged as a gap.

Investigate-artifact: TRIVIAL
Pre-mortem-artifact: TRIVIAL
Hostile-review-artifact: Round 2 m-5, session 260906-fit-whale.
Project-contribution: `timeout=0` now fires with a specific `writing-code-15-unbounded-io(timeout-zero)` subshape; `timeout=0.001` (positive fractional) stays silent.

## Trivial-against-state declaration

Category: local-only
Cannot produce error: single-detector logic addition + 3 additive test fixtures.
Evidence: `git diff --stat` shows scan_ast.py + test_writing_code_15.sh + this self-review.
Falsification: NOT trivial if any file outside skills/detect-ai-fingerprints/ + plans/ changed. Verified.

## Trivial-investigation declaration

Category: local-only
Cannot produce error: read-only AST predicate + fixture-based test.
Evidence: no external service or DB calls.
Falsification: NOT trivial if any external resource is contacted. Verified.

## Peer review

Gate evidence:
- Gate 1 (syntax): python3 ast.parse -> ok
- Gate 2 (tests): bash test_writing_code_15.sh -> "12 passed, 0 failed" (9 prior + 3 new m-5 lock-ins). Regressions: writing-code:7 8/8, writing-code:8 12/12, writing-tests:5 17/17, scan_sh_exit_code 10/10, is_test_path 13/13, rule_citations PASS.
- Gate 3 (docs): the new `is_zero` predicate is documented inline with its m-5 provenance + M-1 sibling discipline (`type(val.value) is not bool` rejects the False→0 collision from writing-code:7 M-1).
- Gate 4 (notebooks): N/A

Shelf compliance:
- writing-code:5 (no hypothetical): verified against 3 fixtures.
- writing-code:7 (no silent swallow): no except handlers added.
- writing-tests:1 (tests fail on revert): reverting `is_zero` block makes fixture (j), (k) go silent.
- writing-claims:8 (specific counts): "12 passed" verified inline.

## Lead review

- Junior solved the stated goal: yes. timeout=0 and timeout=0.0 both fire under a new subshape `(timeout-zero)` distinct from `(missing-timeout)` and `(timeout-none-no-audit-comment)`.
- Junior over-scoped: no.
- Junior under-scoped: does not treat negative timeouts (`timeout=-1`) as invalid. Author-time decision: negative timeouts raise ValueError in `subprocess.run` / `requests.get`; the runtime already screams. If a case surfaces, extend `is_zero` to `val.value <= 0`.
- Standards affirmatively met: writing-code:5, writing-code:7, writing-tests:1, writing-claims:8.

## Quantified claims

Claim: "12/12 pass on writing-code:15 test (9 prior + 3 m-5 lock-ins)."
Verified-by: bash test_writing_code_15.sh -> "Results: 12 passed, 0 failed", rc=0.
