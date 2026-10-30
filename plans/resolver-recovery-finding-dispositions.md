# Resolver recovery findings

Scope: eight writing-code-7 reports for hooks/lib/resolve-think-gate.py in
/private/tmp/runtime-fullbranch-scan-provisional.log, compared with
origin/develop 20bb5fb9c4eb88bc40c4f3f43b6c91e5a4fb7903. This provisional scan is
not acceptance evidence: the coordinator identified a scanner resource failure
and is rerunning the complete scan. Original locations below identify the
provisional reports, not final source line numbers.

The implementer changed only the resolver and its existing task_keyed_gates.py
tests. No noqa annotations, path filters or scanner suppressions were added.
The correction delta is /private/tmp/resolver-recovery-corrections.patch. It does
not include the router author's separate denial-marker guard; the coordinator
will merge that guard and pin the final source/scanner identities separately.
This is author-side analysis and test evidence, requiring independent review
before final per-finding acceptance.

## Original line 116: host_binding_present JSON failure

Disposition: fixed unsafe predicate, not accepted as inherited debt.
Reason: malformed nonempty callback input cannot establish an unbound native
terminal context. Although find_gate_for_repo already rejected JSON parse errors
before its native fallback, the separate host-binding predicate incorrectly
returned false. Nonobject JSON and malformed tool_input shapes also needed an
unambiguous bound outcome.
Evidence: ResolverRecovery.test_malformed_callback_is_bound_and_cannot_read_native_gate
checks malformed JSON, nonobject JSON and malformed tool_input, demands true host
binding and no legacy root gate selection; truly absent callback input still
permits the native compatibility read. The actual existing invalid-host fixture
also passed through test-guard with native evidence available.
Falsification: any malformed supplied callback yielding an unbound result or a
legacy gate would invalidate the fix. Remaining exception return true is a
fail-closed predicate outcome; it grants no session/task identity.

## Original line 329: _same_repo realpath recovery

Disposition: fixed unsafe recovery, not accepted as inherited debt.
Reason: failure to compare repository identity must not recover through a shared
origin and grant a scope match. The broad exception/pass hid that failure.
Evidence: the handler now narrows expected path errors, emits a diagnostic and
returns false. ResolverRecovery.test_uncomparable_repository_cannot_recover_through_origin
injects an OSError and proves the origin fallback is not called even when mocked
to match. Normal path comparison and origin fallback remain for valid inputs.
Falsification: calling the origin fallback after path comparison failure, or
returning true for that failure, would invalidate this disposition. The remaining
reported diagnostic-plus-false handler is an explicit scope denial.

## Original line 386: _within incomparable paths

Disposition: demonstrated fail-closed predicate false positive.
Reason: ValueError or TypeError means containment cannot be established; false
excludes the target from task scope and own-session scratch authority. It does
not substitute a default scope or authorize a mutation.
Evidence: ResolverRecovery.test_unsafe_path_and_shell_shapes_do_not_match injects
a canonicalization ValueError and demands false. Existing scope-specificity and
placeholder/scratch isolation methods passed with the real resolver/hooks.
Falsification: an exception producing containment true, or a caller granting
mutation authority because this predicate is false, would invalidate this claim.

## Original line 621: find_gate_for_repo malformed action

Disposition: demonstrated non-authorizing optional-result false positive; shape
validation strengthened for nonobject payloads and nonmapping tool_input.
Reason: malformed action input yields no selected gate. It cannot proceed to the
legacy native gate fallback after a failed parse.
Evidence: the malformed-callback method tests actual find_gate_for_repo with a
legacy root test-gate present, including malformed tool_input. Every bad shape
yields None. The existing invalid-host/native-evidence end-to-end fixture passed.
Falsification: returning a gate from the malformed-action handler, or reaching a
legacy fallback after it, would invalidate the claim.

## Original line 791: _git_lines unavailable listing

Disposition: optional-result helper contract is valid; a true caller defect was
fixed rather than deferred.
Reason: None means Git could not establish a listing. The directory-classification
caller already converted it to Tier C, but the lone-commit caller used `or []`,
turning a failed staged/modified listing into an apparently empty commit. That
could lower the review floor. Both listings must now be established before use.
Evidence: ResolverRecovery.test_failed_git_listing_cannot_lower_commit_review_floor
injects a real TimeoutExpired exception at the subprocess boundary, checks None,
and independently fails each staged/modified listing. Both force Tier C with
`cannot enumerate commit targets`. Existing conventional-message commit target
classification passed. The helper now documents None in its Optional contract.
Falsification: either unavailable listing producing a lower floor, or a caller
treating None as an authoritative empty set, would invalidate this disposition.

## Original line 804: _lone_git_commit unknown shell shape

Disposition: demonstrated fail-closed predicate false positive.
Reason: unsupported shell syntax must not claim the narrow lone-commit target
selection. False keeps the generic conservative classification path in place.
Evidence: ResolverRecovery.test_unsafe_path_and_shell_shapes_do_not_match supplies
an unterminated quoted commit message that raises UnknownShape and checks false.
The existing conventional-message commit classification method passed, showing
valid quoted messages retain their intended staged/modified target behavior.
Falsification: an UnknownShape result being treated as a lone commit, or false
selecting the lone-commit branch, would invalidate the claim.

## Original line 879: _load unreadable or malformed gate

Disposition: demonstrated non-authorizing optional-result false positive.
Reason: an absent, unreadable, malformed or nonobject file is no gate authority.
The exception set is now narrowed to expected read/parse/type failures rather
than suppressing arbitrary implementation exceptions. Optional None is documented.
Evidence: ResolverRecovery.test_missing_unreadable_and_malformed_gate_is_no_authority
checks absent input, malformed JSON, a JSON array and an injected PermissionError;
all yield None. Existing gate-selection tests exercised real scope resolution.
Falsification: returning authority from any failed load, or an authority caller
using None as a successful gate, would invalidate the claim.

## Original line 723: own_session_path stat recovery

Disposition: fixed unsafe recovery, not accepted as inherited debt.
Reason: creating a new lifecycle file can legitimately encounter FileNotFoundError,
but a different stat failure leaves hardlink ownership unproven. The previous
OSError/pass continued into the scratch exemption even when inspection failed.
Evidence: ResolverRecovery.test_unreadable_lifecycle_target_is_not_owned_scratch
first proves an absent new own-session gate path is allowed, then injects
PermissionError and proves denial. The handler emits a diagnostic; only actual
absence retains the creation exception. Existing placeholder/scratch isolation
also passed through actual hook execution.
Falsification: a non-ENOENT stat error authorizing scratch, or removing hardlink
rejection for an existing file, would invalidate the fix.

## Direct tests and handoff

Using PATH=/opt/homebrew/bin:/usr/bin:/bin and TMPDIR=/private/tmp:

- ResolverRecovery: six methods passed; /private/tmp/resolver-recovery-targeted-test.log.
- Gates.test_invalid_host_binding_cannot_use_native_legacy_test_evidence: passed
  in 9.062 seconds; /private/tmp/resolver-existing-host-test.log.
- Conventional commit classification, scope specificity/tie, and unexpanded
  template/scratch isolation: three passed in 7.450 seconds;
  /private/tmp/resolver-existing-scope-test.log.
- Scoped diff whitespace check passed.

No accepted real inherited debt remains from these eight findings; identified
unsafe recovery paths were repaired. Predicate/optional-result reports remain
raw where the scanner still reports them. Final complete scanner output,
independent per-finding approval and aggregate tests remain coordinator steps.
