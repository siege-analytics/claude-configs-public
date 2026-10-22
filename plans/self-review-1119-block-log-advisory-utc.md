---
ticket_refs:
  - siege-analytics/claude-configs-public#1119: enforcement-blocks.jsonl counts prompt-time advisories as blocks, in local time
---

# Self-review: #1119 block log advisories and UTC timestamps

## Assumptions

Pre-author-inventory: on dheeraj-electinfo, 345 of 391 block-log lines since the v3.5.74 deploy were `pre-action-guard` advisories (three per prompt), and timestamps were naive local time. The new test fails 7 of 9 checks on develop.
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1119
Pre-mortem-artifact: plans/pre-mortem-1119-block-log-advisory-utc.md
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1119#issuecomment-6329805067
Project-contribution: the block log can be counted directly. Advisories are labelled, every timestamp has an offset, and block-classifier-guard asks only about real blocks.

1. `log-block.sh` writes `datetime.now(timezone.utc).isoformat()` and sets `"advisory": true` when the invariant ends with `(advisory)`. The would-have-blocked audit record from #873 is kept; it is only labelled.
2. `block-classifier-guard.sh` skips `advisory is True` lines and legacy lines whose invariant ends with `(advisory)`. It compares aware datetimes, reading naive lines as local time. A malformed line (non-object, overflow date, null field) is skipped by itself and does not hide later lines.
3. No caller changes: only `pre-action-guard` and `branch-state-guard` use the suffix, and both exit 0.

## Peer review

- **writing-tests:** `block_log_advisory_utc.test.sh`, 10 checks:
  - the writer's UTC offset and advisory flag;
  - the classifier on a mixed log of new and legacy, real and advisory, recent and old lines;
  - malformed lines;
  - classification matching.
- **Hostile review:** no blocker. Addressed:
  - the rollback hazard, now in the pre-mortem (reverting needs the new-format log lines rewritten);
  - the `AttributeError` and `OverflowError` per-line catch;
  - the strict `is True` check.
  Left as is: a null `command` field skips that one line. Writers never emit null, and it used to crash the whole scan.

## Not done

- `block-classifier-guard.sh` is not registered in any deployed settings found (dheeraj-electinfo, the pod-level settings). The fix keeps it correct for when it is wired.
- Existing log lines are not rewritten. Legacy advisories are skipped by suffix, and legacy naive timestamps are read as local.

## Test plan

- `block_log_advisory_utc` 10/0 here. Develop's lib and guard fail 7 of the first 9.
- `branch_state_advisory` 8/0.
- `review_risk_test`; the skill-inventory, generated-source-authority and review-risk-metrics `--check`s.
- The full local validate job, with hook suites run on stdin closed.

## Follow-up: time-zone-independent malformed-line fixture (CodeRabbit on #1124)

The malformed-line fixture used naive `9999-12-31T23:59:59`. It overflows only east of UTC. On a UTC host it parses as a future, recent block, so the counts came out 3 and 2 instead of 2 and 1. Reproduced: the old fixture under `TZ=UTC` gives 8 passed and 2 failed.

The fixture now uses an unparseable timestamp (`ValueError`) and naive `0001-01-01T00:00:00`. Year one either overflows or falls outside the 4h window, so in every zone it neither counts nor hides later lines. Passes 10/0 under UTC, Asia/Tokyo, America/Chicago and Pacific/Kiritimati (+14). The classifier code is unchanged.
