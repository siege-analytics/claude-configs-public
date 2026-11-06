# Queue loader and duplicate-work follow-up

## Assumptions

Goal source: operator-authorized repair, #1156, #1207 and the two new source-supported review findings on #1203. Roles: implementer, release maintainer and source reviewer.

Pre-author-inventory: develop3762e387 contains the reviewed queue repair; its source CI passed 68 hook test files. The resolver loads the queue module before classifying every nonempty command, with module execution outside its denial handler. Coordination Check 1 searches only fix/feat names containing a ticket number, despite permitting other project branch forms. Main auto-merge is disabled for these corrections; existing CI continues.

Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/pull/1203#discussion_r4487805770
Pre-mortem-artifact: plans/queue-loader-wip-followup-1207.md#test-plan
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/pull/1203
Project-contribution: keep queue-only dependencies out of unrelated task operations and recognize existing work before dispatch.

## Test plan

Use the queue parser's existing candidate prefix before loading its module. Keep load failures inside the queue denial path. With the helper missing, ordinary reads and valid local task operations must retain their normal classification; queue requests must fail closed. Preserve all existing pinned queue and ordinary merge cases. Check the ticket's recorded branch and all project-approved branch forms without creating a new approval requirement. Run focused queue/disclosure and risk controls, canonical freshness, genuine source-bound receipts and required protected CI.

## Peer review

Independent exact-source review follows the frozen correction. The bot findings are evidence to verify, not authority to add gates.

## Lead review

Keep both changes narrow. Preserve task scope, required queue proof/audits, holds/settings and normal develop/main publication. No candidate installation, bypass, fabricated receipt or cancellation of the current CI run.

## Quantified claims

The preceding queue candidate passed 25 selected commands and 68 hosted hook test files. These are historical parent results, not proof of this correction.
