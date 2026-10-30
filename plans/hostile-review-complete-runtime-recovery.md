# Integrated independent source review - #1134

Source proposal accepted for a local candidate commit, subject to the remaining
post-commit workflow and protected-host acceptance gates below. This is not a
claim of completed promotion or installed backend delivery.

## Source identity and review scope

Protected base: 20bb5fb9c4eb88bc40c4f3f43b6c91e5a4fb7903. Frozen complete scan tree:
cea67cd6b7e834a989a0e8481eefcd3a79820186. Source and test blobs, trusted scanner
identities, raw output and individual dispositions are recorded in
plans/scanner-recovery-identities.json and plans/scanner-recovery-dispositions.md.
A final bounded metadata transport correction and two new controls are reviewed
in plans/hostile-review-router-transport.md. The superseding complete scan tree
is 419799e2c3d3c3d6c5febdd311e7cf907e8f02d6, with the same individual finding
behaviors verified by AST context, not counts. See
plans/runtime-final-source-verification.json and
plans/hostile-review-final-source-freeze.md. Later additions are review records
only and do not change that final production source. A local review-evidence ref retains the scan tree.

Independent slice receipts cover strict test evidence, reader/Git effects,
spawn request lifecycle, session binding, runtime pins, immutable deployment,
skill ownership, normal installer wiring, cancellation and scanner execution.
The additional source reviews are committed as hostile-review-atomic-settings-publication,
hostile-review-router-hardening, hostile-review-bootstrap-startup,
hostile-review-integrated-resolver-risk and hostile-review-runtime-bytecode.
Each receipt states its bounded scope; none substitutes for full validation.

## Adversarial corrections verified

Review exposed and corrected strict-to-legacy child rebinding, guessed UUID
scratch authority, malformed callback/native recovery, failed Git listing tier
downgrade, unproven scratch ownership and repository comparison recovery.
Real swap races and exchange-then-interruption controls preserve displaced data
and report failure. Publication is point-in-time verification with private
recovery, not a multiwriter transaction. Native CLI skips policy before loading
the router; startup failures block inside enrolled Craft. JSON denies, exact
matchers, global duplicates and environment ownership have focused controls.

The coordinator independently reran the frozen router25, trust17 and reader9
suites, cancellation/evidence regressions, settings-drift12, direct header,
audit/cleanup/ownership and recovery-metadata fault controls. Catalog refresh
and dependency graph checks passed. Test counts identify those executions;
they do not establish all-handler coverage or full-suite acceptance.

The full branch scan completed exit1 with27 findings. An independent reviewer
accepted F01-F27 individually as demonstrated locator/predicate/capture false
positives with source identities, evidence and falsifiers. Raw non-clean output
is retained. No scanner suppression, ignore or clean-exit conversion was used.

## Required acceptance after candidate commit

The first full local workflow FAILED when a read-only Git helper generated
bytecode inside an immutable selected package. That failure remains a failure.
The actual added file was isolated; no inventory exclusion was introduced.
The fixed CLI import boundary and native child environment passed real
inventory-equality controls. Selected component fixtures read committed Git
objects, so the complete normal workflow must rerun after the source candidate
commit, with a fresh content-bound receipt, before any push or promotion.

Protected feature/develop/main checks, exact-source CA hub re-review, published
main, backed-up normal installation, same-GA-session operational and A/B task
isolation, fresh-session and native-CLI canaries remain separate gates. The
Craft0.15.6 Pi/Codex callback limitation remains an external vendor boundary.
