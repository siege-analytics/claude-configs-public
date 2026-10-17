# Author hostile probes: native argument correction (#1027)

## Reviewer Assumptions

Working as: author falsification, not independent ACCEPT.
Reading for: opaque Git arguments at every wrapper/dispatcher boundary.
Predicted failures: early successful help; binding replacement; compatibility
redispatch; missing/extra native arguments accepted; changed destination refs.

## Baseline F1

The unmodified posted probe failed at 5fc9250 before product edits. Normal selected
build/install/wire/verify passed, origin release denied, --selected trunk failed,
and --help release succeeded. The red assertion and ref snapshots are retained.
The old 127-command ledger does not establish correctness of this boundary.

## Correction call-chain review

Generated wrappers insert -- after their fixed native event. Retained explicit
aliases consume their sentinel, then insert the same boundary. parse_arguments
never sends native payloads through argparse and checks exact arity before either
adapter. Native main loads only the local Git binding; an argument cannot provide
one. Runtime verification and the pending journal still precede policy, resolver
or compatibility invocation. The retained commit hook uses cat -- for its path.

The settings parser requires one binding, rejects abbreviation and duplicate
controls, and checks command presence against its event. Only standalone usage
help exits successfully. The native and settings negative fixtures exercise the
public process boundary, without a mocked evaluator.

The executable examples now push ordinary and option-like aliases to one local
bare remote using native paths and file URLs with spaces/Unicode. Allowed heads
are asserted, and each denial records before/after refs. The Siege case retains
its range-review denial for invalid unpublished history, including on release;
no new target-policy rule is introduced. It also checks message paths, malformed
arity, every complete settings vector and pending-state refusal for each vector.

## Author review and limits

Correctness/security: fixed event and data boundary; no permissive unknown-option
parser or untrusted binding fallback. Integrity: old runtime inventory/pin checks
remain mandatory, and the effective-policy modules are unchanged. Resource/error
behavior: existing subprocess timeouts and failure diagnostics remain. Packaging:
new wrappers are rebuilt into the verified inventory. Native payloads are opaque
up to their actual filesystem/Git consumer; empty files/names are not invented.

The DDIA shelf's source/derived-data distinction remains: immutable source and
external adoption pins are authoritative; generated configuration is derived.
Recovery promises are unchanged (8/10 bounded local contract; no multi-file atomic
visibility or power-loss durability). Existing interruption/rollback tests remain
in the full matrix. No independent acceptance or live authority is claimed.

## Scanner disclosure

The unfiltered staged scan reports the same two runtime test-discovery warnings
as the baseline: native_git.py and selected_registration.py are tested through
bin/_test/selected_registration_test.py, outside the scanner's discovery layout.
No scanner filtering, suppression or test/policy weakening is introduced. The
complete PR scan and hashes will accompany the exact-head publication ledger.
