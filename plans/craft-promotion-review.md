# Craft promotion review follow-up (#1003, #994)

## Assumptions

Goal source: plans/craft-runtime-recovery.md
Plan reference: plans/craft-runtime-recovery.md
Investigate-artifact: plans/craft-runtime-recovery.md
Pre-mortem-artifact: plans/pre-mortem-craft-runtime-recovery.md
Hostile-review-artifact: plans/hostile-review-craft-promotion.md
Project-contribution: Finish the authorized Craft recovery promotion without resolving valid review blockers by deferral.

The operator authorized recovery, deployment and promotion into main. After all promotion checks passed, the automated reviewer identified additional boundary defects. The ancestry probe resolved ps through PATH; ticket grep pipelines could produce SIGPIPE with large valid messages; scissors could guess incorrectly when both Git comment settings differ. A test fixture also inherited global Git settings, and the changelog had two Unreleased headings.

The bounded follow-up uses /bin/ps (available on packaged Craft's macOS host and supported Linux fixtures), here-string matching, conservative rejection of conflicting comment settings, isolated fixture configuration, and a named historical 3.5.73 section preserving shipped notes. Production has no probe override. Disposable test copies substitute the observation boundary only after proving a PATH spoof fails against the production bytes.

Pre-mortem additions: hardcoding the observation path might break alternate hosts (they fail closed); fixture substitution might accidentally conceal a production spoof (the production-copy negative runs first); archiving notes might alter release selection (exactly one Unreleased header remains). Large message tests use bounded regular files rather than enormous shell arguments.

## Peer review

The implementer reproduced and corrected each of the five promotion findings. A fresh independent reviewer verified the diff and before/after behavior; the durable verdict is PASS in plans/hostile-review-craft-promotion.md.

## Lead review

The changes are limited to the named promotion threads and their tests. They do not implement the separately requested historical audit findings. The unresolved eval-variable dispatch limitation predates this work and remains outside the classifier's bounded literal-command contract, alongside the existing dynamic-dispatch backlog. Independent review and quantified validation are recorded below before merge.

## Quantified claims

Parent and independent reviewer each passed 138 ticket scenarios and 16 runtime scenarios. Independent before/after checks cover four valid large-message forms plus two denials, five comment-prefix configurations (three compared to actual commits), and release promotion archival/idempotence. Full build, build --check, generated-source-authority, inventory freshness, review-risk metrics and diff checks pass. The review-risk suite passed after regenerating the inventory; its initial stale-inventory failure was repaired, not bypassed. The prior complete recovery run remains documented in plans/self-review-craft-runtime-recovery.md. Hosted CI repeats the full suite for this follow-up.
