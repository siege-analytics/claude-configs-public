# Self-review — wire test-tracking-guard into .claude/settings.json (CCP#946)

## Assumptions

Working as: software engineer, tech lead
Goal source: #946
Pre-author-inventory: #946 — reproduced the drift on skills-upstream/develop: `grep -c test-tracking-guard.sh hooks/settings-snippet.json` = 1, `.claude/settings.json` = 0. #932 wired the guard into the snippet (documentation) but not the live `.claude/settings.json` (what validate-hooks.py check #6 validates), so develop CI has failed since 0dbd1d8 and the guard was inert at runtime.
Investigate-artifact: #946
Pre-mortem-artifact: #946
Project-contribution: Restores a passing develop CI (red since #932) and actually activates the test-tracking-guard at runtime, and unblocks PR #939 whose CI inherited the develop-level failure.

Key assumptions:
- `.claude/settings.json` is the CI-validated live wiring; the snippet is documentation. Verified by reproducing validate-hooks.py check #6 under Python 3.11.
- The triple uses the relative `hooks/git/test-tracking-guard.sh` path form, matching sibling git hooks in `.claude/settings.json`. Verified by reading the file.

## Peer review

- **writing-tests:8 (integration check for a hook).** This fix IS the integration-check instance: #932's hook scenario tests passed, but the hook was not wired into `.claude/settings.json` and validate-hooks.py was not run. Adding a hook is not finished until that gate passes. The fix runs it.
- **Change is minimal + matches convention.** One PreToolUse/Bash entry inserted after survey-context.sh (its snippet position), relative-path form like its siblings, timeout 10.
- Gate 1 (syntax): `python3 -c "import json; json.load(open('.claude/settings.json'))"` -> valid.
- Gate 2 (integration): `~/.pyenv/versions/default_31111/bin/python bin/validate-hooks.py` -> "All hooks valid", exit 0; no settings-drift line for test-tracking-guard. (Local default python3 is <3.10 and cannot run validate-hooks.py's `Path | None` annotation; the SZSH pyenv 3.11 reproduces CI.)
- Gate 2b (the CI tripwire I missed first pass): CI run 37562444110 showed `bin/_test/settings_drift_test.py` still FAILing -- "[PASS] live settings and snippet agree" (my wiring fix worked) but "[FAIL] snippet has 39 triples over 30 distinct hooks; got 40 triples over 31 hooks". That test hardcodes the snippet's triple/hook count as a tripwire; #932 added test-tracking-guard to the snippet (-> 40/31) but never bumped it. Fixed the expected count to (40, 31). After: `settings_drift_test.py` -> "All settings-drift fixtures passed", exit 0 (pyenv 3.11). So the drift fix needed TWO edits, not one; CI caught the second, not local validate-hooks.py alone.
- Gate 3 (counts): snippet count 1 == settings count 1.
- Gate 4 (docs/notebooks): N/A.

## Lead review

- **As tech lead:** this is the fix for a regression I introduced in #932 (snippet-only wiring). Root cause: the hook-authoring path exercised the hook's own tests but not the integration gate (validate-hooks.py). Minimal blast radius: one JSON entry; no hook/skill/rule logic changes.
- **As software engineer:** verified the exact drift and that the fix clears it under the same Python version CI uses (3.11), not just by grep. The 13 validate-hooks.py warnings are pre-existing unreferenced-hook noise, unrelated, and do not fail the run.
- Meta captured for the ticket: fold "a new hook is not done until validate-hooks.py passes AND it is wired in .claude/settings.json" into writing-tests:8 or a hook-authoring corollary (follow-up).
- No AI/assistant attribution anywhere.

## Quantified claims

- **1 PreToolUse/Bash triple added** to `.claude/settings.json` (test-tracking-guard.sh). Evidence: grep count 0 -> 1.
- **validate-hooks.py exit 0** ("All hooks valid"), no drift line for test-tracking-guard. Evidence: command output under pyenv 3.11.
- **snippet == settings** (both 1). Evidence: the two grep counts.
- **settings_drift_test.py tripwire bumped** 39/30 -> 40/31 to match the legitimately-added guard; test exit 0 after. Evidence: pyenv-3.11 run output.
- **2 files changed** (.claude/settings.json wiring + bin/_test/settings_drift_test.py count) + this artifact. Evidence: `git status -s`.
