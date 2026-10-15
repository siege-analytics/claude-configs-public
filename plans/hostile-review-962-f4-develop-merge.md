# Hostile review: F4 merge with F1 and F2/F3 develop

Goal source: coordinator request to reconcile PR #997 with `develop` at `4dcad7c2582cf1fca13d9ad922513599fd1234ca`.

## Review target

Resulting staged tree relative to updated `origin/develop`, including the authoritatively regenerated inventory conflict resolution and merged validation summary.

## Reviewer prompt

Challenge whether incoming build, workflow, lifecycle, resolver, installer, metrics, and consumer-package changes invalidate F4's generated entrypoint derivation, exact helper-edge snapshot, exact CI invocation counts, Tier C policy, exclusions, change-shape tests, or freshness checks. Challenge F1/F2/F3 interoperability rather than trusting green claims.

## Verdict

**ACCEPT**

> No blocking findings. The diff retains Tier C coverage for the audited paths, checks entrypoints against generated artifacts, exercises removal of helper and CI invocation sites, and tests modification, deletion, rename, and generated-output freshness. Nothing shown establishes an F1 promotion or F2/F3 consumer-package regression.

## Exact-SHA round 1

Exact merge commit `30607cc23e7acc1f5b55b83242d4c992e3c2c7d6` was withheld from push and independently reviewed.

**REJECT**

1. High: configured/generated entrypoint sets could shrink with their source registry; helper-free blockers had no independent required-entrypoint snapshot.
2. Medium: a helper path assignment counted as an edge without proving that the assigned variable was subsequently sourced or executed.

Remediation:

- add independent required entrypoint sets for canonical settings, generated manifest, and generated enforcement settings;
- remove every registration from its parsed surface in memory and require the snapshot audit to fail;
- count helper assignment-to-execution/source sites;
- remove every assignment and every downstream use independently and require the chain audit to fail.

## Pre-commit remediation round 2

The first remediation added independent entrypoint snapshots and assignment-use checks. Review returned **REJECT**:

1. High: a later line containing `$VARIABLE` and `python3` could count even when another script was executed and the audited variable survived only in a comment/argument.
2. Medium: converting registrations and uses to sets masked duplicate occurrences; downstream mutations always targeted occurrence zero.

Second remediation:

- compare per-path registration occurrence counters on all three surfaces;
- remove and duplicate every registration occurrence by index;
- accept an assigned helper only when its exact quoted variable is the Python script operand or sourced file;
- retain every use occurrence with its actual line index;
- remove, duplicate, and replace every helper script operand with a decoy while retaining `$VARIABLE` in a trailing comment; all must fail.

## Pre-commit remediation round 3

The occurrence-aware remediation was also **REJECTED**:

1. High: an assignment to another path could retain the audited helper basename only in a trailing comment and satisfy the assignment parser.
2. High: `echo python3 "$HELPER"` could satisfy an unanchored Python-use search despite not executing the helper.

Third remediation:

- require a quoted assignment value to end at the helper basename;
- require `python3` to appear in command position after the start of a command or a shell delimiter;
- mutation-test assignment-path replacement with the helper basename retained in a trailing comment;
- mutation-test `echo`-prefixed non-execution for every downstream use;
- hash-pin all 45 exact helper invocation lines and all 57 exact assignment-use occurrence lines, so any parser-preserving rewrite still requires explicit audit reconciliation.

## Pre-commit remediation round 4

The exact helper-site result was **REJECTED** with one high finding: a configured hook command could retain the audited executable as token zero but append `>/dev/null 2>&1; true`, suppressing its block and forcing success without changing path/count evidence.

Fourth remediation:

- hash-pin each complete canonical settings registration record, including event, matcher, hook type, and full command;
- hash-pin each complete generated manifest gate and generated settings registration;
- mutate every canonical/generated settings occurrence by appending output suppression and forced success, requiring the surface audit to fail.

## Pre-commit remediation round 5

The reviewer initially rejected an `exit 0` content edit to a protected guard because the graph audit does not prove arbitrary future blocker semantics. Reassessment against F4's actual contract returned **ACCEPT**: every audited dependency is modified in a real staged repository, computes Tier C, and rejects real `--declared B` with exit 2/`valid=false`. Tier C intentionally requires independent semantic review; F4 does not claim to prove every possible Tier C implementation change correct.

## Final pre-commit verdict

**ACCEPT**

No finding is waived. Four concrete graph/classification gaps were fixed; the fifth scenario was accepted after scope reconciliation. The rejected merge SHA remains unpushed. A new exact-SHA review is still required before push.
