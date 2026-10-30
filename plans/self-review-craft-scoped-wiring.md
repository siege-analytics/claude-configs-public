# Self-review: Craft scoped wiring

Domain: software engineering
Goal source: plans/craft-scoped-wiring.md
Plan reference: plans/craft-scoped-wiring.md
Investigate-artifact: plans/craft-scoped-wiring.md
Pre-mortem-artifact: plans/craft-scoped-wiring.md
Hostile-review-artifact: plans/hostile-review-craft-scoped-wiring.md

## Assumptions

Working as: implementer in isolated bugfix/craft_scoped_wiring, based on 6d8f06d
with the approved ownership patch staged as the comparison baseline.
Reading for: the normal installer must select and verify the same scoped policy
file, then register the router only after local checks succeed.
Failure shapes: writing the new policy but verifying an old copy; build restoring
the old project-autoload wrapper after migration; missing helper reporting success;
local policy failure followed by global registration.

The router implementation is a separate reviewed slice. This slice uses its
confirmed --workspace, --apply and --verify-registration CLI contract. Direct
legacy wire/verify defaults remain unchanged. Receipt presence chooses only a
fixed filename, not trust or policy authority. No global registration or live
workspace operation was performed from this development worktree.

## Peer review

Independent review approved the final unstaged wiring diff and new fixture,
with no remaining must-fix finding. The staged ownership baseline is excluded
from this review scope. Independent actual wire, orchestration and progressive
mount tests passed. The receipt records the ownership, verifier selection, argv
transport and malformed-policy findings resolved during review.

## Lead review

Function lens: --settings-file selects the wire destination and every verifier
settings assertion. Workspace command substitution uses the workspace root,
including when an explicit policy file lives elsewhere. Existing direct callers
retain their old defaults. The loader keeps Python 3.9 annotation compatibility. Both writer paths retire
only the generated command identity and preserve foreign same-basename hooks
and metadata. The verifier locates the actual deployed wrapper despite preceding
foreign hooks; build refuses malformed operator JSON without replacing bytes.
Installer JSON probes transport paths through argv, including apostrophes.

Chain lens: required helper preflight -> build/deploy -> base managed policy ->
wrapper merge -> explicit local policy verification -> router apply -> read-only
registration verification. The sync entrypoint also checks hook drift before
registration. No optional-file branch silently skips the required router.

DDIA lens: the policy file is managed workspace state; the router receipt is
registration evidence verified by its owner. Build only uses receipt presence
to choose the fixed non-autoload filename. It cannot derive an arbitrary write
path or establish runtime delivery from receipt content.

## Validation

Full flat build passed: /private/tmp/craft-wiring-build.log.
Actual progressive_mount_test passed, including malformed JSON byte preservation,
foreign-hook preservation and owned-wrapper selection, repeated migrated deployments,
legacy operator settings preservation and verifier --settings-file selection:
/private/tmp/craft-wiring-progressive-test.log.
wire_enforcement_automations_test passed with default compatibility, repeated
scoped writes and an alternate explicit policy path resolving workspace commands.
craft_installer_wiring_test passed using actual shell entrypoints and disposable
fake HOME dependencies with spaces and an apostrophe: option propagation, ordering, missing-helper refusal and
local-verification failure refusal. check_deploy_drift_test passed:
/private/tmp/craft-wiring-drift-test.log. Shell syntax and diff whitespace checks
passed. Native_push_test passed all twenty cases after the verifier change:
/private/tmp/craft-wiring-native-test.log. These checks do not claim a live Craft
router callback.

Frontmatter preflight tests passed after providing the required inert helper in
the existing prerequisite fixture. The full suite later stopped at the existing
stale inventory outputs: /private/tmp/craft-wiring-frontmatter-test.log. The
coordinator owns combined generated artifact refresh and integrated checks.

Scanner --working log: /private/tmp/craft-wiring-scanner.log. A new prose adverb
was removed; the remaining whole-file Python subprocess/test-discovery diagnostics
predate this wiring patch. Reason: broad legacy cleanup is outside this bounded
slice. Evidence: diagnostics identify existing calls/handlers in the baseline.
Falsification: a diagnostic on newly introduced code requires a fix. No clean
scanner result or final integration acceptance is asserted here.
