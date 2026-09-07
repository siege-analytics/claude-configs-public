# Self review: issue reporting gate carve-out

## Assumptions

Goal source: operator correction in session 260905-clever-quasar that gate repairs still blocked Siege Utilities issue-filing, plus concrete repro from session 260525-long-swan.
Working as: tech lead and software engineer.
Pre-author-inventory: inspected `hooks/bash/destructive-guard.sh`, `hooks/bash/universal-mutation-gate.sh`, `hooks/_test/destructive_bash_guard.test.sh`, and `hooks/_test/universal_mutation_gate.test.sh` on current develop.
Investigate-artifact: concrete repro from 260525-long-swan showing `gh issue create` first blocked by destructive guard, then by universal mutation gate after evidence-chain override.
Pre-mortem-artifact: this artifact.
Hostile-review-artifact: plans/hostile-review-issue-reporting-carveout.md
Project-contribution: lets coordinator and reviewer sessions file evidence-bearing follow-up issues/comments without manufacturing implementation gates, while preserving blocks on PR/branch mutations and issue lifecycle mutations.

## Peer review

- writing-code:5 PASS - edits are based on inspected guard/test files and concrete blocked command output from the coordinator session.
- writing-tests:1 PASS - tests cover allowed issue create/comment with body files and blocked no-body, close/edit/delete-family, metadata/unknown flags, duplicate flags, stdin body files, PR create/merge, and chained commands.
- writing-claims:2 PASS - validation evidence recorded from focused commands: `destructive_bash_guard.test.sh` passed 30 tests; `universal_mutation_gate.test.sh` passed 29 tests; `python3 bin/build.py --check` passed; `python3 bin/sync-skill-references.py --check` passed.
- writing-prose:1 PASS - added prose uses plain ASCII punctuation.
- Hostile review PASS - `plans/hostile-review-issue-reporting-carveout.md` records the initial bypass findings, fixes, and final PASS verdict.

## Lead review

As tech lead, I approve the policy distinction: issue creation/comment with inspectable evidence is governance reporting, not implementation mutation, and should not require a fresh task think-gate.

As software engineer, I approve the implementation because both enforcement layers are patched: destructive guard allows only validated create/comment, and universal mutation gate no longer broadly safelists issue close/edit/reopen/label while allowing the same validated reporting shape.
