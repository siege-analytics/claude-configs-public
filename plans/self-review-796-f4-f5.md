---
ticket_refs:
  - siege-analytics/claude-configs-public#796
---

# Self-review: PR for #796 R4-F4 + R4-F5 (dead-code sweep)

## Assumptions

Working as: software engineer
Domain: skills/detect-ai-fingerprints/scan_ast.py hygiene
Goal source: siege-analytics/claude-configs-public#796 R4-F4 and R4-F5

R4-F4: `collect_referenced`, `TEST_PATH_PATTERNS`, and `_NOQA_WITH_REASON_RE` alias were R3 back-compat shims with zero external callers.

R4-F5: `_is_flag_name` had a dead `isinstance(FLAG_PATTERNS, str)` branch on a module-level tuple constant.

Investigate-artifact: TRIVIAL
Pre-mortem-artifact: TRIVIAL

## Trivial-against-state declaration

Category: local-only
Cannot produce error: dropping unreferenced symbols and simplifying a predicate to its already-fired path.
Evidence: git diff scoped to scan_ast.py + this self-review.
Falsification: NOT trivial if any external caller broke. Verified by grep across the repo before removal: `collect_referenced` and `TEST_PATH_PATTERNS` had zero non-definition references; `_NOQA_WITH_REASON_RE` had 2 self-file callers rewired to `_NOQA_WT5_REASON_KEYWORDS_RE`.

## Trivial-investigation declaration

Category: local-only
Cannot produce error: static code cleanup with grep-verified zero external callers.
Evidence: no external contact.
Falsification: NOT trivial if any resource beyond the scanner file changed. Verified.

## Peer review

Gate 1 (syntax): python3 ast.parse -> ok.
Gate 2 (tests): all 10 scanner test suites unchanged.

Shelf compliance:
- writing-code:3 (no speculative abstractions): dead-code removal aligns.
- writing-tests:1 (tests fail on revert): reverting the alias-rewire in `_is_carveout_handler` restores a reference to a symbol that no longer exists, breaking module load; verified.
- writing-claims:8: "10 suites unchanged" verified inline.

## Lead review

Standards met: writing-code:3, writing-tests:1, writing-claims:8. Codebase is ~15 lines shorter and no less capable.

## Quantified claims

"10 scanner test suites unchanged at their post-R3-F9 baseline (10, 13, 12, 12, 28, 25, 8, 10, 13, PASS)" — verified by running each script inline.

"3 dead symbols removed: `collect_referenced`, `TEST_PATH_PATTERNS`, `_NOQA_WITH_REASON_RE` alias" — verified by grep on scan_ast.py returning zero hits for each after this PR.

"`_is_flag_name` simplified from 3 lines to 1" — verified by diff.
