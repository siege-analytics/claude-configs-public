# Self-review — run_comprehensive_test guard (CCP#933)

## Assumptions

Working as: software engineer, tech lead
Goal source: #933
Pre-author-inventory: #933 design note — investigated scan.sh (scan_diff_stdin emit contract, test-only gating precedent in writing-tests:3), scan_ast.py vs scan.sh split, and confirmed skills/_siege-utilities--rules.md is a build artifact whose source is projects/siege-utilities/_rules.md.
Investigate-artifact: #933
Pre-mortem-artifact: #933
Project-contribution: Removes a latent suite-recursion foot-gun from the siege_utilities test surface the hostile-audit effort is expanding — a new error-path test that calls the full-suite runner can no longer wedge the run undetected.

Key assumptions:
- The scanner runs against siege_utilities at commit/push via the shared hook stack. Verified: scan.sh RULE_ID_RE lists siege-utilities.
- The realistic vector is a newly-added call in a test; the diff scanner catches added lines. Pre-existing calls are covered by the SU-4c whole-tree grep invariant (forward-only, matching sibling writing-tests scanner rules).

## Peer review

- **writing-tests:1 (red on revert).** The self-test goes red if the scan.sh block is reverted: the positive scenarios assert exit 1 + the rule tag; removing the block flips them to no-match. Confirmed by running the suite.
- **writing-code:6 (doc-edit symmetry).** The touched behaviour (scanner coverage) is documented; added a matching catalogue bullet in detect-ai-fingerprints/SKILL.md and the SU-4c rule in projects/siege-utilities/_rules.md (the source, not the skills/ build artifact).
- **writing-code:7 (no silent swallow).** The block adds no exception handling; the grep gate yields no-finding (pass) only when the pattern is absent, an observable outcome.
- **writing-code:2 (no history refs in code comments).** The scan.sh comment names behaviour (why the call recurses), not tickets/PRs.
- Gate 1 (syntax): `bash -n scan.sh` -> exit 0; `bash -n test_run_comprehensive_test.sh` -> exit 0.
- Gate 2 (tests): `bash test_run_comprehensive_test.sh` -> 4 passed, 0 failed (positive tests/, negative non-test, negative comment-only, positive nested pkg/tests/). Regression: `test_scan_sh_exit_code.sh` 11 passed, `test_is_test_path.sh` 13 passed, `test_writing_code_7.sh` 13 passed.
- Gate 3 (docs): N/A -- no sphinx sources touched.
- Gate 4 (notebooks): N/A.

## Lead review

- **As tech lead:** the check lives in the scanner's grep idiom (scan_diff_stdin), gated to tests/ test_*.py, with the rule source edited (not the generated artifact). Blast radius MEDIUM-but-contained: the gate excludes all non-test and non-siege code. The Elephant (pre-existing calls not re-flagged by the forward-only diff scanner) is named and covered by the SU-4c review grep.
- **As software engineer:** false-positive surface is bounded — the function definition lives outside tests/, and comments are stripped before matching; both are locked by negative self-test scenarios.
- No AI/assistant attribution in any deliverable.

## Quantified claims

- **4 self-test scenarios, 0 failures.** Evidence: `bash test_run_comprehensive_test.sh` -> "Results: 4 passed, 0 failed".
- **0 regressions in the existing scanner suite.** Evidence: test_scan_sh_exit_code.sh 11 passed, test_is_test_path.sh 13 passed, test_writing_code_7.sh 13 passed.
- **4 files changed** (scan.sh, new self-test, projects/siege-utilities/_rules.md, SKILL.md) + 1 self-review artifact. Evidence: `git diff --cached --name-only`.
- **1 new rule tag** `siege-utilities-SU4-suite-runner-in-test`, emitted only under tests/ test_*.py. Evidence: scenario AC1/AC4 match the tag; AC2/AC3 do not.
