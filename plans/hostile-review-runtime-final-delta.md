# Integration final delta review

Verdict: approved for the bounded delta described here, after the descendant
cancellation correction. No remaining must-fix finding in this scope. This is
not approval of the entire integrated branch, individual scanner dispositions,
protected CI, router implementation, deployment or actual host delivery.

Reviewed integration working source in
/private/tmp/claude-runtime-integration-20261029 against protected base
6d8f06d904b62cb20361a177f2eea8b4c74414cb. The reviewed candidate was an integration
working tree, not a final committed SHA. The coordinator must bind this receipt
to the unchanged final source after committing. Earlier ownership and wiring
slices have their own receipts.

## Scope and reviewer roles

Independent review covered the bounded subprocess timeout additions in the
selected source/test callers, validate-local validation/timeout behavior and its
new tests, and the acceptance amendment in skills/commit/SKILL.md,
skills/code-review/SKILL.md and skills/detect-ai-fingerprints/SKILL.md. It also
covered the coordinator's final producer process-group cancellation in
hooks/lib/test-evidence.py and its pending-receipt/descendant regression in
hooks/_test/test_evidence.py.

The reviewer reproduced the local-adapter defect below, then implemented its
correction in bin/validate-local.py and bin/_test/local_validation_test.py at the
coordinator's explicit request. Those two files therefore do not have a claim of
independent author/reviewer separation from this reviewer. The coordinator
separately read the final run_step helper, dispatch and sentinel test, ran the
seven-method suite independently (PASS, 5.374 seconds), and approved the pair.
The reviewer made no other source edits and changed no generated catalogs,
installed workspace or global/user configuration.

## Finding resolved

The initial subprocess.run(timeout=...) killed only the direct bash process. A
real disposable workflow running a background Python child followed by wait
returned status two after 1.09 seconds under --step-timeout 1, but its child wrote
a late-mutation marker afterward. The original six methods passed without
exercising this behavior.

The final adapter starts each step in a new session. Interrupted execution kills
its isolated process group, bounds leader reaping to five seconds, then rethrows
the failure. Normal shell completion does not cancel its normal background-job
semantics. The regression runs a real background child, expires the step budget
and waits beyond the child's scheduled write to prove no late marker appears.
This is POSIX process-group cancellation, not a general supervisor for a command
that creates detached sessions.

The producer now applies the same boundary to actual test execution. Its pending
receipt is written before launch; cancellation leaves exit_code null and every
source result pending. Independent execution of the new real descendant test
proved that the old pass is invalidated and the delayed marker never appears.
No successful receipt is manufactured after cancellation.

## Other review conclusions

The remaining bounded timeout keyword additions retain successful command
arguments and result handling. Exceptions remain non-successful; existing
producer error handling fails evidence checks closed. Source syntax validation
still checks each hook rather than treating a timeout as an accepted result.
The private build timeout precedes live activation, preserving the existing
artifact/stamp boundary on build failure.

The local adapter rejects malformed workflow/step/environment shapes, unsupported
conditional commands and empty executable plans; validates its pinned dependency;
preserves first-failure stopping; and isolates ambient Git/runtime/shell-startup
settings. List mode does not execute selected commands. Step budgets have an
explicit accepted range and expired execution does not report success.

The scanner docs change is a substantive Tier C acceptance amendment, not an
editorial clarification. It retains raw non-clean results and exit identities;
exit two or incomplete evidence blocks; every new, changed or newly exposed true
violation must be fixed based on caller-chain relevance. Remaining inherited or
false-positive findings require independent per-finding evidence, exact source
and scanner/configuration identities, Reason/Evidence/Falsification and actionable
debt tickets. There is no blanket baseline, suppression or conversion of exit one
to a passing scan. Native Git and protected CI gates are not waived. Approval of
this policy text does not itself approve any particular remaining finding.

## Direct verification

Reviewer commands used PATH=/opt/homebrew/bin:/usr/bin:/bin and TMPDIR=/private/tmp:

- python3 bin/_test/local_validation_test.py: original six methods passed; final
  seven methods passed in 5.292 seconds. Final log:
  /private/tmp/integration-local-validation-review-test.log.
- python3 hooks/_test/test_evidence.py: seventeen methods passed in 14.953 seconds,
  including actual descendant cancellation and pending receipt rejection. Log:
  /private/tmp/integration-producer-review-test.log.
- python3 bin/validate-hooks.py: forty-six paths valid; existing unreferenced-hook
  warnings remain warnings.
- git diff --check: passed at the reviewed final source.

The coordinator's separate seven-method run passed as described above. Aggregate
checks, generated-artifact freshness and final commit identity remain the
coordinator's integration acceptance steps. No source changes were made by this
reviewer after reporting the final correction.
