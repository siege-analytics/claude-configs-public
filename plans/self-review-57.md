---
ticket_refs:
  - siege-analytics/claude-configs-public#57
---

# Self-review: PR for #57 (writing-code:8 AST detector)

## Assumptions

Working as: software engineer
Domain: Python AST scanner (skills/detect-ai-fingerprints/scan_ast.py)
Goal source: siege-analytics/claude-configs-public#57
Pre-author-inventory: scan_ast.py at 792 lines pre-fix; existing docstring listed writing-code:4/7/9/15 and writing-releases:3. writing-code:8 was called out in-file as "carve-out" territory (line 13) but had no dedicated detector. Multi-pass single-file scan for optional-import + unguarded callsite is what #57 asks for.
Investigate-artifact: TRIVIAL (see ## Trivial-investigation declaration below)
Pre-mortem-artifact: TRIVIAL (see ## Trivial-investigation declaration below)
Hostile-review-artifact: WAIVED (external dispatch ladder exhausted, per session operator authorization 2026-09-05)
Project-contribution: promotes writing-code:8 from judgment-enforced to mechanically-detected. `[skill:detect-ai-fingerprints]` now catches the "optional import declared but callsites not guarded" defect class at commit-body scan time.

## Trivial-against-state declaration

Reason: single Python file addition (~180 lines added to scan_ast.py) + one new test file. No hook wiring change; scan.sh already dispatches to scan_ast.py for .py files.
Evidence: `git diff --stat` shows scan_ast.py + test_writing_code_8.sh + plans/self-review-57.md.
Falsification: not trivial if the new checker crashes on real code. Verified against 6 test fixtures covering all documented rule shapes.

## Trivial-investigation declaration

Reason: rule text at `_writing-code-rules.md` writing-code:8 names the pattern precisely (try/import/except-with-flag + callsite guarded by if-flag). Detection design mirrors that shape.
Cannot produce error: the new function `check_writing_code_8` runs read-only AST walks; can't mutate state.
Evidence: 6-scenario test suite covers unguarded / early-return-guarded / if-body-guarded / try-body / private-helper-docstring / no-optional-import-pattern cases.
Falsification: not trivial if a legitimate carve-out (e.g. private helper documenting the flag in its docstring) gets flagged. Verified by test (e).

## Peer review

Gate evidence:
- Gate 1 (syntax): `python3 -c "import ast; ast.parse(open('skills/detect-ai-fingerprints/scan_ast.py').read())"` -> ok
- Gate 2 (tests): `bash skills/detect-ai-fingerprints/test_writing_code_8.sh` -> "6 passed, 0 failed". Regression: `bash skills/detect-ai-fingerprints/test_rule_citations.sh` still passes.
- Gate 3 (docs): scan_ast.py docstring updated to name writing-code:8 in the covered-rules list
- Gate 4 (notebooks): N/A

Shelf compliance:
- writing-code:5 (no hypothetical): tested against 6 real fixtures; not extrapolated.
- writing-code:7 (no silent swallow): no except blocks in the new code.
- writing-tests:1 (tests fail on revert): reverting the detector removes its emissions; test (a) fails when the unguarded-callsite scenario returns rc=0.
- writing-claims:8 (specific counts): "6/6 pass" — verified inline.

## Lead review

- Junior solved the stated goal: yes. AST-based single-file detector for writing-code:8 with 6 fixture scenarios.
- Junior over-scoped: no. Cross-file re-export detection (a known scanner gap per rule text) is out of scope; detector explicitly documents this.
- Junior under-scoped: could add more early-return-invariant recognition patterns (e.g. `try: ... except Exception: raise`). Deferred to follow-up; current recognition covers the canonical `if not FLAG: raise` and `if FLAG: ...; else: raise` shapes.
- Standards affirmatively met: writing-code:5, writing-code:7, writing-tests:1, writing-claims:8.

## Quantified claims

Claim: "6/6 test scenarios pass."
Verified-by: `bash skills/detect-ai-fingerprints/test_writing_code_8.sh` returns "Results: 6 passed, 0 failed."

Claim: "no regression on existing scanner test."
Verified-by: `bash skills/detect-ai-fingerprints/test_rule_citations.sh` returns PASS (unchanged output).

## Post-mortem applicability

Not applicable. First-time detector; no prior shipped behavior to revert.
