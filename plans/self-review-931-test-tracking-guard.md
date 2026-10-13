# Self-review — test-tracking-guard (CCP#931)

## Assumptions

Working as: software engineer, tech lead
Goal source: #931
Pre-author-inventory: #931 design note — sibling survey of the pre-push hook stack (test-guard.sh, pre-push-self-review.sh, no-sensitive-files.sh, branch-guard.sh, pr-base-guard.sh) and `grep -rn "check-ignore|ls-files|error-unmatch" hooks/` confirming no existing tracking guard.
Investigate-artifact: #931
Pre-mortem-artifact: #931
Project-contribution: Protects the siege_utilities test-suite integrity the active hostile-audit effort depends on — a new error-path test that passes locally but is silently git-ignored can no longer reach a green PR, closing the false-green gap that let test-absent commits land ≥3× (ellington #1/#3, 2× this effort).

Key assumptions:
- Real tests live under a `tests/` directory; scratch/backup test files live in working dirs (the reason the user-level global `test_*.py` rule exists). Source: operator memory feedback_global_gitignore_test_files.md.
- The silently-dropped file is invisible to any diff (never committed), so a working-tree scan of `tests/` — not a changed-files scan — is the only detector. Flagged to the Editor; intent of the "no-op on non-test push" ask preserved via tests/-scoping + silent exit 0 in the common case.

## Peer review

Shelf checks and mechanical gate evidence:

- **writing-code:5 (no hypothetical code).** The core relies on `git ls-files --others --ignored --exclude-standard` returning exactly the untracked-and-ignored set. Verified empirically in a scratch repo this session: ignored+untracked `tests/test_a.py` listed; scratch file outside tests/ excluded by the path-component filter; `!tests/test_*.py` negation clears it; a TRACKED file matching the pattern is NOT listed (zero false positives). PROBED.
- **writing-code:15 (blocking I/O timeouts).** N/A — the hook shells only to local `git` plumbing (`ls-files`, `log`, `rev-parse`), no network/subprocess-with-unbounded-wait surface from the writing-code:15 list.
- **writing-code:7 (no silent swallowing).** The scan's git calls use `|| echo ""` to yield an empty result rather than crash the hook; an empty result path is a documented, observable pass (exit 0), not a swallowed error.
- **writing-tests:1 (red on revert).** The harness scenarios go red if the hook logic is reverted: AC1/AC6 assert exit 2 + "silently git-ignored"; AC2 asserts exit 0; removing the block path flips AC1/AC6 to exit 0 → red. Confirmed by running the suite.
- Gate 1 (syntax): `bash -n hooks/git/test-tracking-guard.sh` → exit 0; `bash -n hooks/_test/test_tracking_guard.test.sh` → exit 0.
- Gate 2 (tests): `bash hooks/_test/test_tracking_guard.test.sh` → 8 passed, 0 failed (AC1 block, AC2 pass, AC2b silent, AC3 scratch-pass, AC4a override-pass, AC4b bare-block, AC5 non-trigger-pass, AC6 nested-tests block).
- Gate 2b (config): `python3 -c "import json; json.load(open('hooks/settings-snippet.json'))"` → valid; exactly one test-tracking-guard.sh entry.
- Gate 3 (docs): N/A — no docs/ sphinx sources touched.
- Gate 4 (notebooks): N/A — no .ipynb touched.

## Lead review

- **As tech lead:** the hook mirrors the established PreToolUse git-hook contract verbatim (command extraction via extract-json.py, TRIGGERS regex, cd-yield, effective-CWD, exit 2/0 semantics, evidence-chain `[test-track-skip]` override). It adds no new dependency and is LOW blast radius (new file, 0 callers; one settings-snippet entry; one rule paragraph). The Elephant (hook only runs where wiring is installed) is named and covered by the `_writing-tests-rules.md` backstop for agents without the wiring.
- **As software engineer:** false-positive surface is bounded to `tests/`-path `test_*.py`; tracked files are provably excluded by `ls-files --ignored`. The one divergence from the reviewer's literal request (working-tree scan vs changed-files) is forced by the bug's invisibility and was surfaced with evidence before implementation.
- No AI/assistant attribution in any deliverable (hook, test, rule, commit).

## Quantified claims

- **8 harness scenarios, 0 failures.** Evidence: `bash hooks/_test/test_tracking_guard.test.sh` → "Results: 8 passed, 0 failed".
- **0 false positives on tracked test files.** Evidence: scratch-repo probe — a `git add -f`-tracked `tests/test_a.py` matching `test_*.py` is NOT returned by `git ls-files --others --ignored --exclude-standard` (empty output).
- **4 acceptance criteria from #931 covered** (AC1 block, AC2 silent pass, AC3 scratch-exclusion, AC4 override), plus 2 extra scenarios (AC5 non-trigger, AC6 nested tests/). Evidence: scenario names in the harness output.
- **1 settings-snippet entry added** (not 0, not duplicated). Evidence: `grep -c test-tracking-guard.sh hooks/settings-snippet.json` → 1.
- **5 files changed, 0 silently ignored.** Evidence: `git check-ignore -q` nonzero for all 5 staged paths.
