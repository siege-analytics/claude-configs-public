# Self review: standing-order automation opt-in hotfix

## Assumptions

Goal source: operator reported Standing-order completion audit sessions spamming the workspace after #822/#823 sync.
Working as: tech lead and software engineer.
Pre-author-inventory: automations.json inspection showed SessionStatusChange Standing-order completion audit self-trigger loop; repo `wire-enforcement.py` auto-registered automations despite README saying opt-in.
Investigate-artifact: same-turn automations inspection and grep of `wire-enforcement.py`/README contradiction.
Pre-mortem-artifact: auto-registering SchedulerTick and SessionStatusChange prompt automations during sync can reintroduce session spam; default path must not install them.
Project-contribution: prevents future workspace syncs from reintroducing recurring standing-order watchdog/audit prompt sessions while preserving explicit opt-in.

## Peer review

- writing-code:5 PASS - default wiring still merges the blocking CA enforcement gate, but standing-order prompt automations require `--include-standing-order-automations`.
- writing-tests:1 PASS - `bin/_test/wire_enforcement_automations_test.py` proves default skip and explicit opt-in registration.
- writing-claims:2 PASS - validation output recorded before commit.

## Lead review

Approved because the change aligns implementation with README's opt-in invariant and fixes the observed workspace spam root cause without weakening blocking enforcement.
