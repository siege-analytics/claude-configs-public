---
ticket_refs:
  - siege-analytics/claude-configs-public#787
---

# Self-review: PR for #787 R3-F7 (adverb case) + R3-F8 (noqa vocabulary)

## Assumptions

Working as: software engineer
Domain: scan.sh prose adverb regex + scan_ast.py noqa carve-out regexes for writing-tests:5 and writing-code:7
Goal source: siege-analytics/claude-configs-public#787 R3-F7 and R3-F8

R3-F7: `ADVERBS_RE` matched via `grep -oE`; missed capitalized `Crucially` at the start of a sentence.

R3-F8: previous noqa regex accepted any 4+ letter English-shape word with a vowel. `# noqa: writing-tests-5 pass throughthrough` slipped through because "through" is a real 7-letter English word. Loose heuristic; reviewer suggested controlled vocabulary.

Investigate-artifact: TRIVIAL
Pre-mortem-artifact: TRIVIAL

## Trivial-against-state declaration

Category: local-only
Cannot produce error: 2 regex changes + additive fixtures.
Evidence: `git diff --stat`.
Falsification: NOT trivial if any file outside skills/detect-ai-fingerprints/ + plans/ changed. Verified.

## Trivial-investigation declaration

Category: local-only
Cannot produce error: regex change only; behavior verified against fixture-per-shape.
Evidence: no external contact.
Falsification: NOT trivial if any external resource is contacted. Verified.

## Peer review

Gate 1 (syntax): python3 ast.parse -> ok; bash -n scan.sh -> ok.
Gate 2 (tests): test_writing_tests_5 25/25 (22 prior + 3 R3-F8 lock-ins). Regressions: all 9 other suites unchanged (test_writing_code_7 stays 13/13 because its existing carve-out fixtures already contain category keywords like "best-effort" and "cleanup").

Shelf compliance:
- writing-code:5: fixtures verified.
- writing-tests:1 (tests fail on revert): reverting to `grep -oE` on adverbs makes "Crucially" fixture silent; reverting to vowel-lookahead noqa makes (w) "through" fixture silent.
- writing-claims:8: "25 passed" verified for wt5.

## Lead review

Standards met: writing-code:5, writing-tests:1, writing-claims:8.

Controlled vocabulary is the right shape for noqa reasons: (a) it forces the author to name WHICH carve-out category applies, (b) it maps directly to the rule text's two documented carve-out families (`finally`/`cleanup`/`finalizer` and `signal`/`handler`), (c) placeholder abuse (`xxx`, `tbd`, `through`, `pass`) is mechanically defeated.

R3-F8 keyword sets:
- writing-tests:5: cleanup, finally, finalizer, destructor, shutdown, signal, handler, atexit, bootstrap, vendored, library, best-effort, unsafe, cannot-induce, not-induceable.
- writing-code:7: cleanup, best-effort, unsafe, signal, atexit, handler, shutdown, finalizer, destructor, bootstrap, vendored, library, reraise-later, delayed-signal.

## Quantified claims

"25/25 pass on writing-tests:5" — bash test_writing_tests_5.sh returns Results: 25 passed, 0 failed, rc=0.

"13/13 pass on writing-code:7 preserved" — bash test_writing_code_7.sh returns Results: 13 passed, 0 failed, rc=0.

"scan.sh --message-file with 'Crucially this matters' now emits" — verified inline.
