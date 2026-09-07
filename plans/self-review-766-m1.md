---
ticket_refs:
  - siege-analytics/claude-configs-public#766
---

# Self-review: PR for #766 M-1 (writing-code:7 identity check + test_writing_code_7)

## Assumptions

Working as: software engineer
Domain: Python AST scanner writing-code:7 detector (silent-swallow)
Goal source: siege-analytics/claude-configs-public#766 finding M-1
Pre-author-inventory: `is_silent_terminator` at scan_ast.py:263 used `stmt.value.value in (None, False)`, which uses `==` and matches `0`, `0.0`, `0j`, `False` (all `== False` in Python). writing-code:7 rule text names four terminator shapes: Pass, Return None, Return False, Continue. `return 0` is a legitimate typed sentinel (count = 0), NOT silent-swallow.

Investigate-artifact: TRIVIAL (see below)
Pre-mortem-artifact: TRIVIAL (see below)
Hostile-review-artifact: Claude Opus 4.7 Round 2 review, session 260906-fit-whale, delivered M-1. Reproduced locally: `except ValueError: return 0` produced a writing-code-7 emission before this fix.
Project-contribution: closes the false-positive so writing-code:7 stops flagging typed sentinels as silent-swallow, and adds `test_writing_code_7.sh` (previously the rule had no dedicated test — a Round 2 chain-coverage gap).

## Trivial-against-state declaration

Category: local-only
Cannot produce error: 2-line identity check swap in scan_ast.py + one new test file. No consumer runtime path touched.
Evidence: `git diff --stat` shows scan_ast.py + test_writing_code_7.sh + this self-review.
Falsification: NOT trivial if any file outside skills/detect-ai-fingerprints/ + plans/ changed. Verified.

## Trivial-investigation declaration

Category: local-only
Cannot produce error: read-only AST logic + shell test in mktemp scratch.
Evidence: diff scope confirmed via `git diff --stat`; grep for external service or DB calls returns nothing.
Falsification: NOT trivial if any external resource is contacted. Verified: only mktemp -d.

## Peer review

Gate evidence:
- Gate 1 (syntax): `python3 -c "import ast; ast.parse(open('scan_ast.py').read())"` -> ok; `bash -n test_writing_code_7.sh` -> ok
- Gate 2 (tests): `bash test_writing_code_7.sh` -> "8 passed, 0 failed". Regressions: writing-code:8 12/12 unchanged; writing-tests:5 12/12 unchanged; scan_sh_exit_code 10/10 unchanged.
- Gate 3 (docs): `is_silent_terminator` docstring extended to name the M-1 concern by ticket.
- Gate 4 (notebooks): N/A

Shelf compliance:
- writing-code:5 (no hypothetical): identity-vs-equality behavior verified against Python: `0 == False -> True`, `0 is False -> False`.
- writing-code:7 (no silent swallow): the fix is TO the writing-code:7 detector; no new except handlers added.
- writing-tests:1 (tests fail on revert): reverting the identity check causes (d) and (e) to fire → fail.
- writing-claims:8 (specific counts): "8 passed, 0 failed" verified inline.

## Lead review

- Junior solved the stated goal: yes. `is` identity check replaces `in (None, False)` equality; typed zeros are no longer misclassified.
- Junior over-scoped: no. M-2, M-3 are separate PRs.
- Junior under-scoped: minor m-2 (writing-code:7 only detects body-len ∈ {1, 2}) is not addressed here. That's a distinct rule-scope decision (should longer swallow chains fire? Rule text is silent) and belongs in an m-1/m-2/m-3-through-m-6 followup ticket per the epic plan.
- Standards affirmatively met: writing-code:5, writing-code:7 (via test), writing-tests:1, writing-claims:8.

## Quantified claims

Claim: "8/8 pass in the new writing-code:7 test."
Verified-by: `bash skills/detect-ai-fingerprints/test_writing_code_7.sh` -> "Results: 8 passed, 0 failed", rc=0.

Claim: "no regression on existing scanner tests."
Verified-by: test_writing_code_8 unchanged 12/12; test_writing_tests_5 unchanged 12/12; test_scan_sh_exit_code unchanged 10/10; test_rule_citations unchanged PASS.

## Post-error revision

Triggered by: Claude Opus 4.7 hostile review Round 2, session 260906-fit-whale, 2026-09-06, finding M-1.
Observed: `except ValueError: return 0` produced `writing-code-7-silent-swallow(Return)` on develop before this fix. The handler is not silent-swallow; it's returning a documented typed sentinel.
Falsified assumption: the original writing-code:7 detector code assumed `in (None, False)` was semantically equivalent to `is None or is False` for AST literal values. It is not, because Python's Constant nodes hold actual Python objects and `0 == False`.
Revised model: any Python-level equality check on `Constant.value` that is testing for singleton sentinels (None, True, False) must use `is`, not `in` or `==`. Same for `Ellipsis`, `NotImplemented`. This is a general Python discipline; the scanner is the reason it surfaced here.
Implication: audit other places in scan_ast.py where `Constant.value` is tested against a set of singletons. Preliminary grep shows `_iter_call_arg_class_names` and the DeprecationWarning message check are safe (they compare against strings via `.value == '...'`), but a more thorough sweep is filed under #766 F1e.
