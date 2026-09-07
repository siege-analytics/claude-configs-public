---
ticket_refs:
  - siege-analytics/claude-configs-public#766
---

# Self-review: PR for #766 M-2 (writing-code:15 Popen(...).communicate + test_writing_code_15)

## Assumptions

Working as: software engineer
Domain: Python AST scanner writing-code:15 detector (unbounded blocking I/O)
Goal source: siege-analytics/claude-configs-public#766 finding M-2
Pre-author-inventory: `UNBOUNDED_IO_SURFACES` contains `("Popen", "communicate")` and `("Popen", "wait")` entries; `_matches_unbounded_io` walks Attribute chains via `_attr_chain` which returns None on non-Name terminators (e.g., a `Call()`). So `subprocess.Popen(["x"]).communicate()` bottoms out at the Call and returns None — the (Popen, communicate) entry never matches. Scanner docstring at scan_ast.py:472-473 explicitly claimed this shape was handled — falsified by direct test.

Investigate-artifact: TRIVIAL (see below)
Pre-mortem-artifact: TRIVIAL (see below)
Hostile-review-artifact: Claude Opus 4.7 Round 2 review, session 260906-fit-whale, delivered M-2. Reproduced locally: `subprocess.Popen(["x"]).communicate()` produced 0 writing-code-15 emissions before this fix.
Project-contribution: closes the Popen-chain detection gap and adds `test_writing_code_15.sh` (previously had no dedicated test — chain-coverage gap).

## Trivial-against-state declaration

Category: local-only
Cannot produce error: 20-line special-case addition in `_matches_unbounded_io` + excerpt-surface helper + one new test file. No consumer runtime path touched.
Evidence: `git diff --stat` shows scan_ast.py + test_writing_code_15.sh + this self-review.
Falsification: NOT trivial if any file outside skills/detect-ai-fingerprints/ + plans/ changed. Verified.

## Trivial-investigation declaration

Category: local-only
Cannot produce error: read-only AST logic and shell test in mktemp scratch.
Evidence: diff scope confirmed via `git diff --stat`; no external service or DB calls.
Falsification: NOT trivial if any external resource is contacted. Verified: only mktemp -d.

## Peer review

Gate evidence:
- Gate 1 (syntax): `python3 -c "import ast; ast.parse(open('scan_ast.py').read())"` -> ok; `bash -n test_writing_code_15.sh` -> ok
- Gate 2 (tests): `bash test_writing_code_15.sh` -> "9 passed, 0 failed". Regressions: writing-code:7 8/8 unchanged; writing-code:8 12/12 unchanged; writing-tests:5 12/12 unchanged; scan_sh_exit_code 10/10 unchanged; rule-citations unchanged.
- Gate 3 (docs): `_matches_unbounded_io` docstring extended to name M-2 by ticket, walk the special case (Popen chain), and cite the shape it handles.
- Gate 4 (notebooks): N/A

Shelf compliance:
- writing-code:5 (no hypothetical): the fix is verified against real ast trees for both `subprocess.Popen(...).communicate()` and bare `Popen(...).wait()`.
- writing-code:7 (no silent swallow): no except handlers added in the fix.
- writing-code:15 (unbounded I/O): the fix is TO the writing-code:15 detector; the new test exercises it.
- writing-tests:1 (tests fail on revert): reverting the special-case makes fixture (c) and (d) go silent → fail.
- writing-claims:8 (specific counts): "9 passed, 0 failed" verified inline.

## Lead review

- Junior solved the stated goal: yes. `subprocess.Popen(...).communicate()` and `Popen(...).wait()` chained forms fire; excerpt-surface names the pattern usefully (previously emitted `?(...)`).
- Junior over-scoped: no. M-3 is a separate PR. m-4 (instance-method `p = Popen(); p.wait()`) is deferred as a distinct problem (requires flow analysis, not a special-case shape match).
- Junior under-scoped: m-4 (aliased imports `import subprocess as sp; sp.run(...)`) still misses because `_attr_chain` on `sp.run` returns `('sp', 'run')` which is not in the surface set. Author-time decision: alias handling requires an import-scan pass, out of proportion for a targeted M-2 fix; filed under #766 F1e.
- Standards affirmatively met: writing-code:5, writing-code:7, writing-tests:1, writing-claims:8.

## Quantified claims

Claim: "9/9 pass in the new writing-code:15 test."
Verified-by: `bash test_writing_code_15.sh` -> "Results: 9 passed, 0 failed", rc=0.

Claim: "no regression on existing scanner tests."
Verified-by: writing-code:7 unchanged 8/8; writing-code:8 unchanged 12/12; writing-tests:5 unchanged 12/12; scan_sh_exit_code unchanged 10/10; rule-citations unchanged PASS.

## Post-error revision

Triggered by: Claude Opus 4.7 hostile review Round 2, session 260906-fit-whale, 2026-09-06, finding M-2.
Observed: `subprocess.Popen(["x"]).communicate()` produced 0 writing-code-15 emissions on develop. Scanner docstring at :472-473 claimed the shape was handled.
Falsified assumption: original `_matches_unbounded_io` code assumed the (Popen, communicate) entry would trigger via chain-rightmost-two-segments matching. It doesn't, because `_attr_chain` stops at a non-Attribute (the Popen Call).
Revised model: chain-matching is insufficient for method-invocation chains where the target is a constructor call. Any surface entry whose left-hand side is an instantiable class rather than a module name needs an alternative code path — a "call-then-attribute" pattern rather than "attribute-then-attribute-chain". The M-2 fix adds this pattern for Popen; future similar patterns (context managers, threadpool.executor().submit(), etc.) may need similar treatment.
Implication: audit the UNBOUNDED_IO_SURFACES for entries whose left-hand element is a class (not a module). Preliminary grep: only Popen currently. No further changes needed today, but the general shape is documented and future consumers of `_matches_unbounded_io` know when to reach for the special-case pattern.
