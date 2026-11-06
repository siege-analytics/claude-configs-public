# Correct two promotion-review instruction mismatches

Goal source: siege-analytics/claude-configs-public#1156
Review source: PR1203 findings4486347094 and4486347101.
Base: `3956000f937f036e624b10b5402d89e8526c74f3`.

## Design and investigation

The dispatch example used an approved remote-tracking integration ref without creating a local branch. Git correctly created a detached worktree, but the example omitted the task branch needed for ordinary push/PR handoff. Use an unused project-approved TASK_BRANCH and `git worktree add -b` while retaining the verified integration ref, isolated path and all prior-resolution, role and supervision rules.

The extracted Lead checklist still demanded pytest for every test suite and Sphinx for every docs change, despite the entrypoint requiring actual selected-project tooling. Change only Lead Gate2/3 to the project's actual test runner and documentation builder/reference validation. Applicable evidence is still mandatory; absent suites/docs changes require an honest applicability statement. No test, review, owner hold or protected check is waived.

## Extraction provenance

The checklist extraction initially preserved its entire baseline region. This deliberate semantic correction replaces only the contiguous Lead Gate2/3 paragraph. Mechanical reconstruction confirms every other checklist byte is identical to base3956000. The template and field-contract golden regions retain their original baseline7e1 SHA-256 pins. The revised checks-region pin is `fe89f4c4c025589717e91736e88ba5b6181a72ba0ddc5039c3b3116fa152400b`, replacing `3613f823346d2ba43a54e43978afc2a15f01c8d7cf8d6067c796e703d561d09e`. The test comment records this qualification rather than claiming the corrected checklist is unchanged from extraction.

## Pre-mortem

Launch-blocking Tiger: actual test/doc verification becomes optional. Retain applicable-gate requirements and require real command/results, with source consistency controls against the selected-tool entrypoint.
Launch-blocking Tiger: dispatch still produces detached HEAD or reuses another worker's branch. Test the literal documented command against a disposable remote-tracking ref and assert the resulting symbolic task branch; retain unused-branch guidance.
Risk: regenerated metadata can be stale. Root regenerates once on the final combined source; this slice does not edit generated source catalogs.

## Validation

Both-layout build passed. All seven Self-review disclosure cases passed (1.501s), including exact template/field preservation, the revised checklist pin, all four real package sibling/link checks, native artifact parser positives/negatives, selected-tool source consistency and a real Git worktree named-branch check. Existing coordination_alias harness passed. These tests are source/package/native-fixture evidence, not installed agent interpretation or backend parity.

The initial new worktree assertion compared all stdout with the branch name; Git also printed its normal HEAD notice. The fixture now asserts the final symbolic-ref line. No production behavior was changed for that fixture correction. No runtime hook, grant, classifier, install, protected merge or live session changed. Independent review and normal combined protected validation remain required.
