# Self review: #831 stale session-scoped artifact gate shadowing

## Assumptions

Goal source: siege-analytics/claude-configs-public#831
Working as: software engineer and tech lead
Pre-author-inventory: inspected deployed `universal-mutation-gate.sh`, `resolve-think-gate.py`, and the live `260525-long-swan` gate files showing current think-gate plus stale #718 session artifact gates.
Investigate-artifact: plans/design-note-831-session-artifact-shadow.md
Pre-mortem-artifact: plans/design-note-831-session-artifact-shadow.md
Hostile-review-artifact: plans/hostile-review-831-session-artifact-shadow.md
Project-contribution: prevents long-lived coordinator sessions from being blocked by stale artifact gates from older tasks while preserving missing-artifact enforcement for current tasks.

## Peer review

- writing-code:5 PASS - resolver candidate selection remains scoped to repo/session and now rejects wrong-ticket or generic artifact gates for current-task resolution.
- writing-code:5 PASS - repo matching no longer relies on basename alone; it uses realpath or git remote origin identity.
- writing-tests:1 PASS - `hooks/_test/universal_mutation_gate_831.test.sh` covers stale-session-shadow pass, stale-only block, generic session artifact block, generic workspace-root artifact block, same-basename repo collision block, and `--session-known` behavior.
- writing-tests:1 PASS - broader existing suites `universal_mutation_gate.test.sh` and `session_signal_resolution.test.sh` still pass.
- writing-claims:2 PASS - validation output recorded before commit.

## Lead review

Approved. The patch fixes the observed coordinator gate failure at the resolver layer, keeps task scoping explicit, and does not introduce a bypass: stale wrong-ticket artifacts are ignored, and if no current matching artifacts exist the mutation gate still blocks.
