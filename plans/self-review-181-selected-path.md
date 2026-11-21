# Self-review: #181 selected commit-msg path

Ticket: siege-analytics/claude-configs-public#181
Review tier: C (native commit-message enforcement)
Base: develop 5eb1619844c393ca3065edf16201906f2f5a810f

## Assumptions

Goal source: operator directive and #181 policy intent: ban every Co-Authored-By trailer and continue authorized work when a candidate needs repair.

## Acceptance criteria

No commit execution path accepts a `Co-Authored-By` trailer, regardless of attribution target. The native hook checks the final message file directly, and a large message with an early matching trailer cannot evade rejection through a broken pipe.

## Changes

- Move final-message trailer detection into a shared helper and run it before the selected-registration branch delegates to `native_git.py`.
- Read the message file directly with `grep` and input redirection. This removes the `printf | grep -q` pipeline that could produce SIGPIPE with `pipefail`.
- Add regressions for the selected path and a 2 MB message whose co-author trailer appears before the payload.

## Test plan

- `bash hooks/_test/review_risk_policy.test.sh`: 16 passed, 0 failed.
- `uv run --with-requirements requirements-validation.txt python3 bin/_test/selected_registration_test.py`: 14 passed.
- `bash -n .githooks/commit-msg` and `git diff --check`: passed.
- Hosted CI is required on the final PR head before promotion.

## Findings

The selected branch invokes the registered native adapter before the repository compatibility policy. Checking the message file before that delegation closes the path without changing the adapter's ticket policy. The compatibility path now searches the original file, so message size and pipe behavior cannot change whether a trailer is found. The tests confirm rejection on both paths and retain the surrounding tier-policy cases.

## Independent review

CodeRabbit on PR #1480 identified the selected-path bypass and SIGPIPE risk. Both findings are fixed, with regressions for a selected message file and a 2 MB message. Details and review URL are recorded in `plans/hostile-review-181-selected-path.md`.
