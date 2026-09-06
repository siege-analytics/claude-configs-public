---
ticket_refs:
  - siege-analytics/claude-configs-public#766
---

# Self-review: PR for #766 M-3 (writing-tests:5 noqa reason must be a real word)

## Assumptions

Working as: software engineer
Domain: Python AST scanner writing-tests:5 detector — noqa carve-out regex
Goal source: siege-analytics/claude-configs-public#766 finding M-3
Pre-author-inventory: F8 (#760) required `noqa: writing-tests-5` to be followed by ≥3 chars of non-whitespace. That trivially accepted `xxx`, `tbd`, `...`, defeating the "reason must justify the carve-out" intent (writing-rules:4). Round 2 (Claude Opus, session 260906-fit-whale) named M-3 as the gap.

Investigate-artifact: TRIVIAL (see below)
Pre-mortem-artifact: TRIVIAL (see below)
Hostile-review-artifact: Claude Opus 4.7 Round 2, session 260906-fit-whale. Reproduced locally: `# noqa: writing-tests-5 xxx` silenced the rule before this fix.
Project-contribution: closes the placeholder-reason carve-out so writing-tests:5 stays strict; adds 5 M-3 lock-in fixtures.

## Trivial-against-state declaration

Category: local-only
Cannot produce error: single regex change + 5 additive test fixtures.
Evidence: `git diff --stat` shows scan_ast.py + test_writing_tests_5.sh + this self-review.
Falsification: NOT trivial if any file outside skills/detect-ai-fingerprints/ + plans/ changed. Verified.

## Trivial-investigation declaration

Category: local-only
Cannot produce error: read-only regex + shell test in mktemp scratch.
Evidence: diff scope confirmed; no external service or DB calls.
Falsification: NOT trivial if any external resource is contacted. Verified: only mktemp -d.

## Peer review

Gate evidence:
- Gate 1 (syntax): `python3 -c "import ast; ast.parse(...)"` -> ok
- Gate 2 (tests): `bash test_writing_tests_5.sh` -> "17 passed, 0 failed" (12 prior + 5 new M-3 lock-ins). Regressions: writing-code:7 8/8, writing-code:8 12/12, writing-code:15 9/9, scan_sh_exit_code 10/10, rule-citations PASS.
- Gate 3 (docs): regex `_NOQA_WITH_REASON_RE` docstring extended to name M-3 by ticket and cite the vowel+length shape.
- Gate 4 (notebooks): N/A

Shelf compliance:
- writing-code:5 (no hypothetical): behavior verified against 14 Python-level regex cases; 12 fixture-driven cases.
- writing-code:7 (no silent swallow): no new except handlers added.
- writing-tests:1 (tests fail on revert): reverting the vowel-lookahead makes fixtures (m-p) go silent → fail.
- writing-claims:8 (specific counts): "17 passed, 0 failed" verified inline.

## Lead review

- Junior solved the stated goal: yes. Placeholder tokens (xxx, tbd, ...) no longer defeat the carve-out; real words (cleanup, finally, best-effort, unsafe, signal) still pass.
- Junior over-scoped: no. Minors m-1 to m-6 (excluding m-7) filed under #766 F1e.
- Junior under-scoped: the vowel-lookahead is a heuristic; a determined adversary could type `# noqa: writing-tests-5 aaaa` and pass. Author-time decision: the goal is to force the author to think of at least one real word ("what's my reason") — any English speaker's real reason will contain a real English word. Anti-goal is Codex's placeholder-reason attack (`xxx`, `tbd`), which is exactly what M-3 fixes. If a stronger check is needed later, an enumerated-category vocabulary (same shape as `CALLER_CONTRACT_PHRASES` for writing-code:8) can be layered on top.
- Standards affirmatively met: writing-code:5, writing-code:7, writing-tests:1, writing-claims:8.

## Quantified claims

Claim: "17/17 pass on writing-tests:5 test (12 prior + 5 M-3 lock-ins)."
Verified-by: `bash test_writing_tests_5.sh` -> "Results: 17 passed, 0 failed", rc=0.

Claim: "no regression on the four other scanner test scripts."
Verified-by: writing-code:7 unchanged 8/8; writing-code:8 unchanged 12/12; writing-code:15 unchanged 9/9; scan_sh_exit_code unchanged 10/10; rule-citations unchanged PASS.

## Post-error revision

Triggered by: Claude Opus 4.7 hostile review Round 2, session 260906-fit-whale, 2026-09-06, finding M-3.
Observed: `# noqa: writing-tests-5 xxx` was accepted as a valid carve-out on develop before this fix. The F8 regex required only `\S{3,}` — any 3+ non-whitespace chars.
Falsified assumption: F8's implementer (this same agent, self-review-760-f6-f8.md) assumed "≥3 non-whitespace chars after the noqa" was equivalent to "a reason token". Placeholder tokens defeat that equivalence.
Revised model: any regex intended to enforce "author must state a reason" must reject tokens that a lazy author would type as placeholder (xxx, tbd, ..., zzz). The empirical anti-pattern set is small but well-defined; the vowel-lookahead + 4-char-minimum handles it without needing an enumerated allowlist.
Implication: audit other noqa/opt-out regexes in the scanner (writing-code:7's `noqa: writing-code-7` handler) for the same weakness. Preliminary grep at scan_ast.py:304 shows `has_noqa_writing_code_7` checks for the substring `"noqa: writing-code-7"` with no reason requirement at all — even the F8 (weak) discipline is not applied there. Follow-up filed under #766 F1e.
