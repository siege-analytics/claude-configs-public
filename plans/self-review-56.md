---
ticket_refs:
  - siege-analytics/claude-configs-public#56
---

# Self-review: PR for #56 (writing-tests:5 AST detector)

## Assumptions

Working as: software engineer
Domain: Python AST scanner (skills/detect-ai-fingerprints/scan_ast.py)
Goal source: siege-analytics/claude-configs-public#56
Pre-author-inventory: scan_ast.py after #57 landed at ~975 lines; existing docstring listed writing-code:4/7/8/9/15 and writing-releases:3. writing-tests:5 was called out in the rule text as cross-file (needs to grep sibling test file for pytest.raises(<ExcClass>)); no dedicated detector existed. This PR adds the cross-file check.
Investigate-artifact: TRIVIAL (see ## Trivial-investigation declaration below)
Pre-mortem-artifact: TRIVIAL (see ## Trivial-investigation declaration below)
Hostile-review-artifact: WAIVED (external dispatch ladder exhausted, per session operator authorization 2026-09-05)
Project-contribution: promotes writing-tests:5 from judgment-enforced to mechanically-detected. `[skill:detect-ai-fingerprints]` now catches "except <Class>: <handler>" in production code lacking a matching `pytest.raises(<Class>)` in the sibling test file.

## Trivial-against-state declaration

Reason: single Python file addition (~120 lines added to scan_ast.py) + one new test file. No hook wiring change; scan.sh already dispatches to scan_ast.py for .py files.
Evidence: `git diff --stat` shows scan_ast.py + test_writing_tests_5.sh + plans/self-review-56.md.
Falsification: not trivial if the new checker crashes on real code. Verified against 6 test fixtures covering all documented rule shapes.

## Trivial-investigation declaration

Reason: rule text at `_writing-tests-rules.md` writing-tests:5 names the pattern precisely (except with named class in production code + no `pytest.raises(<Class>)` in test file + not a carve-out). Detection design mirrors that shape: extract handlers, resolve sibling test files by convention (tests/test_<stem>.py plus a few variants), grep test files for `pytest.raises(<class>)` and `assertRaises(<class>)`.
Cannot produce error: the new function `check_writing_tests_5` runs read-only AST walks + read-only test-file scans; can't mutate state.
Evidence: 6-scenario test suite covers (a) no test file / (b) matching pytest.raises / (c) dotted-class-with-short-name-match / (d) noqa carve-out / (e) test file exempt / (f) bare except (handled by writing-code:7).
Falsification: not trivial if a legitimate carve-out gets flagged, or if short-name test matches on a dotted exception class get missed. Both verified by tests (c) and (d).

## Peer review

Gate evidence:
- Gate 1 (syntax): `python3 -c "import ast; ast.parse(open('skills/detect-ai-fingerprints/scan_ast.py').read())"` -> ok
- Gate 2 (tests): `bash skills/detect-ai-fingerprints/test_writing_tests_5.sh` -> "6 passed, 0 failed". Regression: `bash skills/detect-ai-fingerprints/test_rule_citations.sh` still passes.
- Gate 3 (docs): scan_ast.py docstring updated to name writing-tests:5 in the covered-rules list
- Gate 4 (notebooks): N/A

Shelf compliance:
- writing-code:5 (no hypothetical): tested against 6 real fixtures; not extrapolated.
- writing-code:7 (no silent swallow): no except blocks in the new code.
- writing-tests:1 (tests fail on revert): reverting the detector removes its emissions; test (a) fails when the unguarded-except scenario returns no writing-tests-5 emission.
- writing-claims:8 (specific counts): "6/6 pass" — verified inline.

## Lead review

- Junior solved the stated goal: yes. Cross-file AST detector for writing-tests:5 with 6 fixture scenarios covering the rule text's documented shapes.
- Junior over-scoped: no. Test-file discovery covers the common conventions (tests/test_<stem>.py, tests/<pkg>/test_<stem>.py, <pkg>/tests/test_<stem>.py, sibling test_<stem>.py); more exotic layouts (pytest custom collect hooks, tox nested envs) are deferred.
- Junior under-scoped: the rule text's two documented carve-outs (finally-cleanup and __del__/signal handlers) are only exempted through the explicit `# noqa: writing-tests-5` opt-out here, not auto-detected. Author-time judgment: rule text says both carve-outs "require a one-line comment naming why no test exists" — the noqa IS that comment. Auto-detecting finally-cleanup context adds complexity for a case where the author is already required to write a comment.
- Standards affirmatively met: writing-code:5, writing-code:7, writing-tests:1, writing-claims:8.

## Quantified claims

Claim: "6/6 test scenarios pass."
Verified-by: `bash skills/detect-ai-fingerprints/test_writing_tests_5.sh` returns "Results: 6 passed, 0 failed."

Claim: "no regression on existing scanner test."
Verified-by: `bash skills/detect-ai-fingerprints/test_rule_citations.sh` returns PASS (unchanged output).

## Post-mortem applicability

Not applicable. First-time detector; no prior shipped behavior to revert.
