# Self review: #819/#820 self-review hook repairs

## Assumptions

Goal source: #819 and #820
Working as: software engineer and tech lead
Pre-author-inventory: inspected `hooks/git/self-review.sh` transformation-content scan, `Pre-author-inventory:` field check, and existing hook test coverage.
Investigate-artifact: plans/design-note-819-820-self-review-hook.md
Pre-mortem-artifact: plans/design-note-819-820-self-review-hook.md
Hostile-review-artifact: plans/hostile-review-819-820-self-review-hook.md
Project-contribution: reduces false-positive governance blocks while preserving strict evidence gates for current work.

## Peer review

- writing-code:5 PASS - #819 patch skips only the exact self-review hook path during transformation content scanning; real transformation files remain checked.
- writing-code:5 PASS - #820 patch grandfathers only clean tracked artifacts older than the enforcement-introduction commit; dirty, untracked, and current missing fields still block.
- writing-tests:1 PASS - `hooks/_test/self_review_hook_819_820.test.sh` covers #819 self-hook pass, real transformation block, #820 grandfather warning, dirty historical artifact block, current committed artifact block, and untracked artifact block.
- writing-claims:2 PASS - validation output recorded before commit.

## Lead review

Approved. The fix is narrow, evidence-bearing, and keeps mutation/promotion gates strict for current work while preventing historical schema drift from blocking unrelated future work.
