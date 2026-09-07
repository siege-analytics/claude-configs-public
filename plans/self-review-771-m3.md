---
ticket_refs:
  - siege-analytics/claude-configs-public#771
---

# Self-review: PR for #771 m-3 (arg walker recurses into Subscript / Starred)

## Assumptions

Working as: software engineer
Domain: writing-tests:5 arg walker for `pytest.raises(...)` / `assertRaises(...)` positional args
Goal source: siege-analytics/claude-configs-public#771 m-3
Pre-author-inventory: `_iter_call_arg_class_names` handled Name, Attribute, Tuple only. `pytest.raises(Optional[Foo])` returned nothing → tests using typing wrappers false-positive'd writing-tests:5. `pytest.raises(*exc_tuple)` returned nothing → same false-positive.

Investigate-artifact: TRIVIAL
Pre-mortem-artifact: TRIVIAL
Hostile-review-artifact: Round 2 m-3, session 260906-fit-whale.
Project-contribution: extracts arg-walker into `_yield_class_names_from` which recurses into Subscript (unwraps typing wrappers). Starred returns nothing (conservative: cannot statically resolve).

## Trivial-against-state declaration

Category: local-only
Cannot produce error: refactor of arg walker + 3 additive fixtures.
Evidence: `git diff --stat` shows scan_ast.py + test_writing_tests_5.sh + this self-review.
Falsification: NOT trivial if any file outside skills/detect-ai-fingerprints/ + plans/ changed. Verified.

## Trivial-investigation declaration

Category: local-only
Cannot produce error: read-only AST recursion.
Evidence: no external service or DB calls.
Falsification: NOT trivial if any external resource is contacted. Verified.

## Peer review

Gate evidence:
- Gate 1 (syntax): python3 ast.parse -> ok
- Gate 2 (tests): bash test_writing_tests_5.sh -> "20 passed, 0 failed" (17 prior + 3 m-3 lock-ins). Regressions: all other scanner tests unchanged.
- Gate 3 (docs): `_yield_class_names_from` docstring names the shapes it handles (Name, Attribute, Tuple, Subscript, Starred) and cites m-3 by ticket.
- Gate 4 (notebooks): N/A

Shelf compliance:
- writing-code:5: verified against 7 Python-level cases + 3 end-to-end fixtures.
- writing-code:7: no except handlers added.
- writing-tests:1: reverting Subscript recursion makes fixtures (r) and (s) fire → fail.
- writing-claims:8: "20 passed" verified.

## Lead review

- Junior solved the stated goal: yes. Subscript wrappers (Optional/Union/Tuple) unwrap; Starred conservatively yields nothing (documented; the alternative would be false-positive-negative).
- Junior over-scoped: no.
- Junior under-scoped: does not resolve `pytest.raises(GLOBAL_EXC)` where GLOBAL_EXC is a module-level assign of a tuple of exceptions. Author-time decision: requires flow-analysis; if surfaced, extend.
- Standards affirmatively met: writing-code:5, writing-code:7, writing-tests:1, writing-claims:8.

## Quantified claims

Claim: "20/20 pass on writing-tests:5 test (17 prior + 3 m-3 lock-ins)."
Verified-by: bash test_writing_tests_5.sh -> "Results: 20 passed, 0 failed", rc=0.
