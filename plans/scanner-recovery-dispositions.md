# Scanner disposition publication record

This publication copy normalizes punctuation to ASCII and removes redundant
adverbs from the reviewed proposal. Finding IDs, source identities, outcomes,
evidence and falsifiers are unchanged. Reviewed proposal SHA256:
`bf0d82ae1c03056d9773466e67bdf68de90a34f2db80de87bb73b6685a2d2234`.
Independent acceptance is recorded separately in
`plans/hostile-review-scanner-dispositions.md`. The original proposed text below
retains its author-side status; it is not self-approval.

# Proposed final scanner dispositions  -  independent approval pending

This is author-proposed analysis, NOT approval of its own dispositions. No source
suppression, path ignore, whole-file exception, exit mapping or clean-scan claim
is used. Every row below maps one actual final raw finding to reviewed behavior,
narrow evidence and a falsifier. task_gate_review must independently accept each
row before the coordinator uses this as gate evidence.

## Exact completed scan

Protected base: `20bb5fb9c4eb88bc40c4f3f43b6c91e5a4fb7903`. Candidate scan tree: `cea67cd6b7e834a989a0e8481eefcd3a79820186`.
The coordinator observed actual completion of tool session39739 with exit **1**.
`/private/tmp/runtime-complete-source-freeze-scan.log` has exactly **27 findings**, a complete footer and no resource/error/
incomplete diagnostics. Complete raw SHA256:
`148441b6a8ba9f6efb7aed7fefb08e3737ccf86379a7f09e399bba7250faa172`.
This is **complete, non-clean**, never scanner PASS.

The scan ran from a detached protected-base worktree with only its index loaded
from the candidate tree; source/test/config selection came from those same Git
objects. Trusted scanner code ran from the integration tree and its three blob
identities match the scanned tree. No ignore or config override was used; the
candidate has no `.claude/scanner-config.toml`, so pinned scanner defaults apply.
Exact invocation, full raw output, base/candidate/source/test/scanner/policy/control
identities are in `/private/tmp/runtime-scanner-dispositions-proposed.metadata.json`.

There are fifteen **test-locator heuristic** rows, eleven **expected-outcome**
exception rows and one nested-generator **offset-use** row. Locator rows show
that actual mapped fixtures exist outside the heuristic's naming convention;
they do NOT claim every named exception handler is tested. Source/API mapping is
not itself execution evidence. Frozen trust17, reader9 and router25/control runs
are identified separately from older focused evidence. No real inherited debt is
proposed for acceptance, and no ticket substitutes for fixing a true defect.

The earlier 30-finding complete run had four genuine missing fixture subprocess
budgets, subsequently fixed. The prior complete 26-finding tree lost the old
own_registration parsing-exception finding (now exact canonical text), moved
ownership nonmatch parsing into the shared router helper, and gained CAS metadata
and native_git locator findings: net27. The resource-error provisional run remains
incomplete evidence. No full aggregate PASS is claimed: the previous workflow
failed package bytecode inventory, fixed source passed focused controls, and the
Git-object component workflow still must rerun after candidate commit.

## F01  -  bin/build.py:190

Rule: `writing-tests-5`. Enclosing function: `_deploy_source_files`.
Raw report: source has 46 except block(s) but no test file found (looked in tests/, bin/tests/, ...)

Proposed disposition: false positive for the specific heuristic/expected outcome; independent acceptance pending.

Reason: Test-discovery heuristic only: the scanner does not locate this repository's mapped `_test` fixture. Relevant chain: raw-source validation -> immutable private build -> workspace copy/merge -> artifact verification/stamp. This finding supplies no per-handler coverage measurement.

Evidence and function/caller chain: bin/_test/deploy_source_policy_test.py real immutable success, source-mutation and corrupt-copy negatives; progressive_mount_test.py malformed scoped-policy byte preservation and foreign hook ownership. Executed evidence: /private/tmp/skill-ownership-policy-test.log and /private/tmp/craft-wiring-progressive-test.log; final-source aggregate rerun remains required.

Falsification: The disposition fails if the named fixture is absent, no longer imports/dispatches this source, or the stated control does not exercise that chain. Unchecked individual handlers are not claimed covered by finding an external test file.

## F02  -  bin/craft-workspace-trust.py:352

Rule: `writing-code-7-silent-swallow(Pass)`. Enclosing function: `publish_staged`.
Raw report: except (OSError, ValueError): <Pass>

Proposed disposition: false positive for the specific heuristic/expected outcome; independent acceptance pending.

Reason: Optional recovery metadata is attempted only while handling an already failed or uncertain atomic publication. Suppressing its expected OSError/ValueError neither deletes retained versions nor returns success: the next statement unconditionally raises not-verified with the retained recovery path. This is failure-preserving observation, not silent activation recovery.

Evidence and function/caller chain: publish_staged -> recovery_manifest attempt -> unconditional ValueError -> installer/enable activation abort. Frozen real control /private/tmp/runtime-cas-metadata-control.py injects a last-moment exchange conflict and recovery_manifest OSError; /private/tmp/runtime-frozen-cas-metadata-control.log PASS proves not-verified, concurrent active bytes preserved and a private displaced version retained. Frozen trust suite seventeen PASS /private/tmp/runtime-frozen-trust17.log. Independent publication review /private/tmp/atomic-settings-publication-independent-review.md confirms interruption/retained-version boundaries.

Falsification: Metadata failure producing verified success, unlinking a retained version, blindly rolling back over a newer writer, or allowing a caller to publish an active receipt after this exception invalidates the explanation.

## F03  -  bin/craft-workspace-trust.py:44

Rule: `writing-tests-5`. Enclosing function: `snapshot`.
Raw report: source has 15 except block(s) but no test file found (looked in tests/, bin/tests/, ...)

Proposed disposition: false positive for the specific heuristic/expected outcome; independent acceptance pending.

Reason: Test-discovery heuristic only: the scanner does not locate this repository's mapped `_test` fixture. Relevant chain: snapshot/document -> inspect_workspace -> lock/stage/replace/rollback. This finding supplies no per-handler coverage measurement.

Evidence and function/caller chain: bin/_test/craft_workspace_trust_test.py imports the actual helper and exercises malformed/duplicate/nonregular config, concurrent writes, atomic create/exchange/compensation, exchange-then-interrupt preservation, legacy exact env retirement and non-main CLI refusal. Frozen seventeen-test PASS /private/tmp/runtime-frozen-trust17.log; independent review /private/tmp/atomic-settings-publication-independent-review.md. The optional helper is not normal-installer trust enrollment; no claim that all fifteen handlers have independent fault coverage.

Falsification: The disposition fails if the named fixture is absent, no longer imports/dispatches this source, or the stated control does not exercise that chain. Unchecked individual handlers are not claimed covered by finding an external test file.

## F04  -  bin/install-craft-hook-router.py:232

Rule: `writing-tests-5`. Enclosing function: `install`.
Raw report: source has 7 except block(s) but no test file found (looked in tests/, bin/tests/, ...)

Proposed disposition: false positive for the specific heuristic/expected outcome; independent acceptance pending.

Reason: Test-discovery heuristic only: the scanner does not locate this repository's mapped `_test` fixture. Relevant chain: preview/activate -> source and policy pins -> owned migration -> receipt-last publication/verification. This finding supplies no per-handler coverage measurement.

Evidence and function/caller chain: bin/_test/craft_hook_router_test.py activation migration/idempotence, concurrent CLI change and incomplete-registration controls dispatch the actual installer. Final-source router fixtures include exact legacy bootstrap migration, direct global known-policy refusal before mutation and known global env refusal; frozen 25-test PASS /private/tmp/router-final-startup-boundary.log. Atomic publication/CAS is separately exercised by the frozen trust17 suite.

Falsification: The disposition fails if the named fixture is absent, no longer imports/dispatches this source, or the stated control does not exercise that chain. Unchecked individual handlers are not claimed covered by finding an external test file.

## F05  -  bin/native_git.py:183

Rule: `writing-tests-5`. Enclosing function: `main`.
Raw report: source has 5 except block(s) but no test file found (looked in tests/, bin/tests/, ...)

Proposed disposition: false positive for the specific heuristic/expected outcome; independent acceptance pending.

Reason: Test-discovery locator false positive only: this adapter is exercised by mapped fixtures outside the scanner naming convention. Chain: native CLI argument/binding verification -> selected or compatibility command execution with descendant bytecode suppression -> policy result/error propagation. Finding an external fixture is not a measurement of all five handlers.

Evidence and function/caller chain: hooks/_test/reader_git_safety.py test_read_guard_and_native_shell_descendants_leave_inventory_unchanged executes the actual adapter -> shell -> fresh Python child and verifies unchanged bytes inventory. Frozen nine-test PASS /private/tmp/runtime-frozen-reader9.log; independent bytecode review /private/tmp/runtime-bytecode-independent-review.md. bin/_test/selected_registration_test.py directly imports native_git and dispatches its packaged CLI for opaque controls, binding-before-payload and event-specific-vector failures. That source mapping is not a claim that the previously failed full component workflow now passed.

Falsification: If the named fixtures stop importing/dispatching native_git, the shell descendant loses PYTHONDONTWRITEBYTECODE=1 or writes package bytecode, or the stated argument/binding controls cease to reach this adapter, this disposition fails. No all-handler coverage is asserted.

## F06  -  bin/validate-hooks.py:122

Rule: `writing-tests-5`. Enclosing function: `compare_settings_to_snippet`.
Raw report: source has 2 except block(s) but no test file found (looked in tests/, bin/tests/, ...)

Proposed disposition: false positive for the specific heuristic/expected outcome; independent acceptance pending.

Reason: Test-discovery heuristic only: the scanner does not locate this repository's mapped `_test` fixture. Relevant chain: compare_settings_to_snippet -> structured missing/invalid registration problems; syntax checks. This finding supplies no per-handler coverage measurement.

Evidence and function/caller chain: bin/_test/settings_drift_test.py imports compare_settings_to_snippet and tests duplicate, missing, empty and foreign registrations. Initial rerun exposed a stale expected count; root corrected to actual 46 triples/30 hooks and reports twelve PASS. The only added triple versus protected base was PostToolUseFailure/mcp__session__spawn_session/hub-concurrency-gate.sh. Direct validate-hooks actual source check: 46 paths valid.

Falsification: The disposition fails if the named fixture is absent, no longer imports/dispatches this source, or the stated control does not exercise that chain. Unchecked individual handlers are not claimed covered by finding an external test file.

## F07  -  bin/validate-local.py:97

Rule: `writing-tests-5`. Enclosing function: `run_step`.
Raw report: source has 7 except block(s) but no test file found (looked in tests/, bin/tests/, ...)

Proposed disposition: false positive for the specific heuristic/expected outcome; independent acceptance pending.

Reason: Test-discovery heuristic only: the scanner does not locate this repository's mapped `_test` fixture. Relevant chain: workflow parsing -> isolated shell step -> process-group cancellation -> non-success result. This finding supplies no per-handler coverage measurement.

Evidence and function/caller chain: bin/_test/local_validation_test.py directly dispatches a copied actual adapter. Seven methods cover malformed input, pinned dependency, isolation, first failure, timeout and real background descendant cancellation. /private/tmp/integration-local-validation-review-test.log PASS; root independently ran seven PASS. This reviewer authored the cancellation fix; root separately reviewed it.

Falsification: The disposition fails if the named fixture is absent, no longer imports/dispatches this source, or the stated control does not exercise that chain. Unchecked individual handlers are not claimed covered by finding an external test file.

## F08  -  bin/wire-enforcement.py:55

Rule: `writing-tests-5`. Enclosing function: `merge_ca_enforcement_settings`.
Raw report: source has 4 except block(s) but no test file found (looked in tests/, bin/tests/, ...)

Proposed disposition: false positive for the specific heuristic/expected outcome; independent acceptance pending.

Reason: Test-discovery heuristic only: the scanner does not locate this repository's mapped `_test` fixture. Relevant chain: actual CLI -> explicit/default destination -> merge_ca_enforcement_settings and opt-in automation merge. This finding supplies no per-handler coverage measurement.

Evidence and function/caller chain: bin/_test/wire_enforcement_automations_test.py dispatches the actual CLI for default/scoped/alternate paths and repeats; preserves foreign same-basename/malformed shell commands. Independent wiring review receipt /private/tmp/craft-scoped-wiring-independent-review.md and local PASS. No blanket JSON/automation exception coverage claim. Owned-env CLI controls PASS /private/tmp/wire-owned-env-tests.log: copy only generated known flag1, preserve unknown/operator env, reject malformed source/target env without replacing target bytes; no mandatory trust flag was added.

Falsification: The disposition fails if the named fixture is absent, no longer imports/dispatches this source, or the stated control does not exercise that chain. Unchecked individual handlers are not claimed covered by finding an external test file.

## F09  -  hooks/lib/craft-settings-router.py:517

Rule: `writing-code-7-silent-swallow(Pass)`. Enclosing function: `route`.
Raw report: except (OSError, ValueError): <Pass>

Proposed disposition: false positive for the specific heuristic/expected outcome; independent acceptance pending.

Reason: Audit is best-effort observation after the hook aggregate decision. Catching OSError/ValueError here does not choose a fallback directory, change the already computed allow/deny, or execute the protected tool.

Evidence and function/caller chain: route -> execute hooks -> aggregate -> local_audit -> return existing result. Real fixture with local_audit raising PermissionError retains a real read allow and real unscoped mutation deny, and no marker appears. PASS /private/tmp/runtime-frozen-router-disposition-controls.log.

Falsification: An audit error changing a deny to allow, choosing different scope/identity, creating a protected effect, or selecting an alternate audit directory invalidates this boundary.

## F10  -  hooks/lib/craft-settings-router.py:318

Rule: `writing-code-7-silent-swallow(Pass)`. Enclosing function: `execute_hook`.
Raw report: except ProcessLookupError: <Pass>

Proposed disposition: false positive for the specific heuristic/expected outcome; independent acceptance pending.

Reason: Expected cleanup race: killpg may find that the isolated group already exited. Ignore only ProcessLookupError, then reap the leader and preserve the original routing/I/O failure. This is not recovery to success.

Evidence and function/caller chain: execute_hook finally cleanup. Real Popen child exits, selector injects RoutingError after waiting for that exit, original RoutingError survives and leader has returncode zero. PASS /private/tmp/runtime-frozen-router-disposition-controls.log.

Falsification: Returning successful hook output after the injected failure, failing to reap the leader, or swallowing a non-ProcessLookupError cancellation failure invalidates this cleanup explanation.

## F11  -  hooks/lib/craft-settings-router.py:138

Rule: `writing-code-7-silent-swallow(Continue)`. Enclosing function: `workspace_policy_commands`.
Raw report: except ValueError: <Continue>

Proposed disposition: false positive for the specific heuristic/expected outcome; independent acceptance pending.

Reason: Expected ownership nonmatch: Path.relative_to raises for an operator command outside workspace/hooks. Continue excludes it from the managed retirement set; treating it as managed would delete foreign configuration.

Evidence and function/caller chain: Shared workspace_policy_commands -> installer managed_commands compatibility delegate -> exact project retirement and global-duplicate refusal; runtime verify_global also uses the same parser. managed_commands -> retire_project/retire_global. Router activation migration/idempotence fixture preserves foreign hooks. Direct real control appends /operator/hooks/other.sh and proves it is absent from managed_commands; /private/tmp/runtime-frozen-router-disposition-controls.log PASS.

Falsification: A foreign command entering the retired set, or failure to retain its metadata during migration, invalidates this ownership-nonmatch explanation.

## F12  -  hooks/lib/craft-settings-router.py:517

Rule: `writing-tests-5`. Enclosing function: `route`.
Raw report: source has 8 except block(s) but no test file found (looked in tests/, hooks/lib/tests/, ...)

Proposed disposition: false positive for the specific heuristic/expected outcome; independent acceptance pending.

Reason: Test-discovery heuristic only: the scanner does not locate this repository's mapped `_test` fixture. Relevant chain: scoped entrypoint -> owned receipt verification -> strict session binding -> bounded hook execution/aggregation. This finding supplies no per-handler coverage measurement.

Evidence and function/caller chain: bin/_test/craft_hook_router_test.py actual router dispatch covers corrupt/missing enrollment, identity ambiguity, protocol conflicts, execution budget/output, concurrent settings changes and real mutation denial. Frozen 25-test PASS /private/tmp/router-final-startup-boundary.log. Direct malformed ownership/audit/cleanup real fault controls also PASS, without claiming every handler is exercised. Frozen 25-test source additionally exercises markerless missing-router skip, marked startup failure mapping, exact shell ownership, deny normalization/conflicts, full tool-name matching and guarded enrollment resolution. This does not prove every one of eight handlers is covered.

Falsification: The disposition fails if the named fixture is absent, no longer imports/dispatches this source, or the stated control does not exercise that chain. Unchecked individual handlers are not claimed covered by finding an external test file.

## F13  -  hooks/lib/git_command.py:247

Rule: `writing-tests-5`. Enclosing function: `main`.
Raw report: source has 3 except block(s) but no test file found (looked in tests/, hooks/lib/tests/, ...)

Proposed disposition: false positive for the specific heuristic/expected outcome; independent acceptance pending.

Reason: Test-discovery heuristic only: the scanner does not locate this repository's mapped `_test` fixture. Relevant chain: CLI parse/prefix/invocations -> read classifier/branch/destructive/authorization policies. This finding supplies no per-handler coverage measurement.

Evidence and function/caller chain: hooks/_test/reader_git_safety.py executes actual CLI/hook chains for alternate Git targets, textconv and protected refs. The new unflagged git_command CLI inventory control proves no task_actions.pyc appears; native shell/fresh-Python propagation is checked too. Frozen nine-test PASS /private/tmp/runtime-frozen-reader9.log; independent source review /private/tmp/runtime-bytecode-independent-review.md. No all-handler coverage claim.

Falsification: The disposition fails if the named fixture is absent, no longer imports/dispatches this source, or the stated control does not exercise that chain. Unchecked individual handlers are not claimed covered by finding an external test file.

## F14  -  hooks/lib/read-only-command.py:395

Rule: `writing-tests-5`. Enclosing function: `lead_verbs`.
Raw report: source has 2 except block(s) but no test file found (looked in tests/, hooks/lib/tests/, ...)

Proposed disposition: false positive for the specific heuristic/expected outcome; independent acceptance pending.

Reason: Test-discovery heuristic only: the scanner does not locate this repository's mapped `_test` fixture. Relevant chain: lead_verbs -> reader classification -> nonzero unknown/unsafe outcome. This finding supplies no per-handler coverage measurement.

Evidence and function/caller chain: hooks/_test/reader_git_safety.py test_malformed_reader_syntax_grants_no_read_authority imports the actual module and checks malformed quote gives unknown verb and nonzero status; direct /private/tmp/reader-syntax-independent-test.log PASS. Frozen reader nine-test suite also PASS /private/tmp/runtime-frozen-reader9.log. Base64 output and textconv controls use actual effects.

Falsification: The disposition fails if the named fixture is absent, no longer imports/dispatches this source, or the stated control does not exercise that chain. Unchecked individual handlers are not claimed covered by finding an external test file.

## F15  -  hooks/lib/resolve-think-gate.py:392

Rule: `writing-code-7-silent-swallow(Return)`. Enclosing function: `_within`.
Raw report: except (ValueError, TypeError): <Return>

Proposed disposition: false positive for the specific heuristic/expected outcome; independent acceptance pending.

Reason: Fail-closed containment predicate: uncomparable canonical paths are outside scope, so false cannot grant task or scratch authority.

Evidence and function/caller chain: _within -> select_task/own_session_path. ResolverRecovery.test_unsafe_path_and_shell_shapes_do_not_match injects ValueError and demands false. Direct six-test PASS /private/tmp/resolver-recovery-targeted-test.log and actual scope/tie/placeholder three-test PASS /private/tmp/resolver-existing-scope-test.log.

Falsification: Any incomparable paths being treated as contained, or a caller using false to grant authority, invalidates this predicate explanation.

## F16  -  hooks/lib/resolve-think-gate.py:631

Rule: `writing-code-7-silent-swallow(Return)`. Enclosing function: `find_gate_for_repo`.
Raw report: except (ValueError, TypeError): <Return>

Proposed disposition: false positive for the specific heuristic/expected outcome; independent acceptance pending.

Reason: Malformed action yields no optional gate, before any native legacy fallback. Nonobject payload and nonmapping tool_input are denied.

Evidence and function/caller chain: find_gate_for_repo -> select_task/fallback. ResolverRecovery.test_malformed_callback_is_bound_and_cannot_read_native_gate provides a legacy root gate and malformed callbacks and proves no selection. Existing invalid-host actual test-guard/native-evidence fixture passed /private/tmp/resolver-existing-host-test.log.

Falsification: A failed parse selecting a task or legacy gate invalidates this no-authority result.

## F17  -  hooks/lib/resolve-think-gate.py:805

Rule: `writing-code-7-silent-swallow(Return)`. Enclosing function: `_git_lines`.
Raw report: except (OSError, SubprocessError): <Return>

Proposed disposition: false positive for the specific heuristic/expected outcome; independent acceptance pending.

Reason: Optional Git listing failure is None, not an authoritative empty listing. A real lone-commit caller defect was repaired: either failed staged/modified listing now raises into Tier C instead of using `or []`.

Evidence and function/caller chain: _git_lines -> task_tier lone-commit/directory paths. ResolverRecovery.test_failed_git_listing_cannot_lower_commit_review_floor injects TimeoutExpired and fails each listing independently; both yield C with cannot-enumerate reason. Direct six-test PASS; conventional commit real test also PASS.

Falsification: Any caller turning None into authoritative emptiness/lower review floor invalidates this contract. This is not a deferral of the earlier caller defect.

## F18  -  hooks/lib/resolve-think-gate.py:818

Rule: `writing-code-7-silent-swallow(Return)`. Enclosing function: `_lone_git_commit`.
Raw report: except UnknownShape: <Return>

Proposed disposition: false positive for the specific heuristic/expected outcome; independent acceptance pending.

Reason: Unknown shell shape cannot claim the narrow lone-commit selection. False leaves the generic conservative classification path; it is not a mutation exemption.

Evidence and function/caller chain: _lone_git_commit -> task_tier. Malformed quoted commit raises UnknownShape and returns false in ResolverRecovery.test_unsafe_path_and_shell_shapes_do_not_match. Existing conventional-message staged/modified classification test passed.

Falsification: UnknownShape being accepted as a lone commit, or false selecting the lone-commit branch, invalidates this explanation.

## F19  -  hooks/lib/resolve-think-gate.py:896

Rule: `writing-code-7-silent-swallow(Return)`. Enclosing function: `_load`.
Raw report: except (OSError, ValueError, TypeError): <Return>

Proposed disposition: false positive for the specific heuristic/expected outcome; independent acceptance pending.

Reason: Missing/unreadable/malformed/nonobject file is no optional gate authority. Expected read/parse/type errors are now narrow; arbitrary implementation exceptions are not suppressed.

Evidence and function/caller chain: _load -> task/companion/native evidence lookup. ResolverRecovery.test_missing_unreadable_and_malformed_gate_is_no_authority exercises absent file, malformed JSON, array and PermissionError, all None; direct six-test PASS.

Falsification: Any failed load yielding authority, or a caller treating None as a valid gate, invalidates the optional-result contract.

## F20  -  hooks/lib/resolve-think-gate.py:117

Rule: `writing-tests-5`. Enclosing function: `host_binding_present`.
Raw report: source has 28 except block(s) but no test file found (looked in tests/, hooks/lib/tests/, ...)

Proposed disposition: false positive for the specific heuristic/expected outcome; independent acceptance pending.

Reason: Test-discovery heuristic only: the scanner does not locate this repository's mapped `_test` fixture. Relevant chain: callback/session identity -> task scope selection -> artifact/tier/scratch checks. This finding supplies no per-handler coverage measurement.

Evidence and function/caller chain: hooks/_test/task_keyed_gates.py imports the actual resolver; ResolverRecovery six direct exception controls PASS plus real invalid-host test-guard and conventional commit/scope/placeholder controls PASS. The earlier eight-finding author analysis is /private/tmp/resolver-recovery-finding-dispositions.md. Root independently reviews the four repaired behaviors; this row does not claim all 28 handlers are covered.

Falsification: The disposition fails if the named fixture is absent, no longer imports/dispatches this source, or the stated control does not exercise that chain. Unchecked individual handlers are not claimed covered by finding an external test file.

## F21  -  hooks/lib/session_anchor.py:162

Rule: `writing-code-7-silent-swallow(Return)`. Enclosing function: `_registered_header`.
Raw report: except (OSError, ValueError): <Return>

Proposed disposition: false positive for the specific heuristic/expected outcome; independent acceptance pending.

Reason: Invalid/unreadable registered header yields no session identity. None cannot supply a UUID/directory fallback or authorize scratch. This boundary rejects duplicate header fields, malformed JSON and unsafe file forms.

Evidence and function/caller chain: _registered_header -> registered_session_dir -> router identity selection. Actual temporary control /private/tmp/runtime-session-header-disposition-control.py first binds a valid exact header, then injects malformed JSON, duplicate fields and PermissionError; each yields None and registered_session_dir empty. PASS /private/tmp/runtime-frozen-session-header-control.log. Router fixtures separately cover unique header correction, anchor ambiguity and unbound aliases; frozen twenty-five-test PASS /private/tmp/router-final-startup-boundary.log.

Falsification: A read/parse failure returning a session directory or permitting alias fallback invalidates this no-identity explanation.

## F22  -  hooks/lib/session_anchor.py:42

Rule: `writing-tests-5`. Enclosing function: `_read_regular`.
Raw report: source has 10 except block(s) but no test file found (looked in tests/, hooks/lib/tests/, ...)

Proposed disposition: false positive for the specific heuristic/expected outcome; independent acceptance pending.

Reason: Test-discovery heuristic only: the scanner does not locate this repository's mapped `_test` fixture. Relevant chain: regular/header/anchor reads -> strict registered identity selection and environment correction. This finding supplies no per-handler coverage measurement.

Evidence and function/caller chain: bin/_test/craft_hook_router_test.py real router fixtures cover malformed/missing headers, unique header identity, anchor provenance, ambiguity and mutation denial. hooks/_test/session_anchor_mistag.test.sh is the existing environment-correction fixture. Frozen twenty-five-test router PASS, plus direct malformed/duplicate/unreadable header control PASS /private/tmp/runtime-frozen-session-header-control.log. No claim every one of ten handlers has direct exception coverage.

Falsification: The disposition fails if the named fixture is absent, no longer imports/dispatches this source, or the stated control does not exercise that chain. Unchecked individual handlers are not claimed covered by finding an external test file.

## F23  -  hooks/lib/task_actions.py:207

Rule: `writing-code-7-silent-swallow(Return)`. Enclosing function: `_python_read`.
Raw report: except (ValueError, SyntaxError): <Return>

Proposed disposition: false positive for the specific heuristic/expected outcome; independent acceptance pending.

Reason: Malformed Python cannot be classified as a proven isolated read. Returning false makes action classification conservative; it does not execute the snippet or grant read authority.

Evidence and function/caller chain: _python_read -> action/read classification -> mutation gate. Safety.test_malformed_reader_syntax_grants_no_read_authority supplies invalid Python `if`, demands false, and separately rejects malformed shell syntax. Direct /private/tmp/reader-syntax-independent-test.log PASS, frozen reader nine-test PASS /private/tmp/runtime-frozen-reader9.log.

Falsification: Malformed Python receiving proven-read authority or bypassing mutation requirements invalidates this fail-closed predicate.

## F24  -  hooks/lib/task_actions.py:153

Rule: `writing-code-9-silently-dropped-param(offset)`. Enclosing function: `shape`.
Raw report: def shape(...): parameter 'offset' has a default but is never referenced in this function's own scope, not forwarded, and not named in the docstring

Proposed disposition: false positive for the specific heuristic/expected outcome; independent acceptance pending.

Reason: The offset parameter is captured by `any(p < offset for p in globs)` inside the nested generator. The scanner own-scope heuristic misses this use; removing the argument would change grammar behavior.

Evidence and function/caller chain: _reader_globs -> nested shape -> attached option expansion classification. Safety.test_malformed_reader_syntax_grants_no_read_authority accepts --include= value offset10 and rejects key offset2 with UnknownShape. Direct /private/tmp/reader-syntax-independent-test.log PASS; exact source generator use supplies source proof.

Falsification: If changing offset no longer distinguishes value/key expansion, or the nested expression stops reading it, this unused-parameter disposition fails.

## F25  -  hooks/lib/task_actions.py:207

Rule: `writing-tests-5`. Enclosing function: `_python_read`.
Raw report: source has 8 except block(s) but no test file found (looked in tests/, hooks/lib/tests/, ...)

Proposed disposition: false positive for the specific heuristic/expected outcome; independent acceptance pending.

Reason: Test-discovery heuristic only: the scanner does not locate this repository's mapped `_test` fixture. Relevant chain: shell token/action parsing -> exact read grammar or conservative mutation targets -> gate authority. This finding supplies no per-handler coverage measurement.

Evidence and function/caller chain: hooks/_test/task_keyed_gates.py actual mutation/read/scope fixtures plus reader_git_safety.py malformed Python, option grammar and real-effects controls exercise the module. Direct malformed Python/offset test PASS and real scope controls PASS. No claim all eight exception handlers are covered.

Falsification: The disposition fails if the named fixture is absent, no longer imports/dispatches this source, or the stated control does not exercise that chain. Unchecked individual handlers are not claimed covered by finding an external test file.

## F26  -  hooks/lib/test-evidence.py:64

Rule: `writing-tests-5`. Enclosing function: `working_blob`.
Raw report: source has 8 except block(s) but no test file found (looked in tests/, hooks/lib/tests/, ...)

Proposed disposition: false positive for the specific heuristic/expected outcome; independent acceptance pending.

Reason: Test-discovery heuristic only: the scanner does not locate this repository's mapped `_test` fixture. Relevant chain: read/validate receipt -> exact source/revision checks -> pending-first real test execution/cancellation -> final receipt. This finding supplies no per-handler coverage measurement.

Evidence and function/caller chain: hooks/_test/test_evidence.py imports producer/checker and runs actual fixture Git/test commands. Seventeen-test PASS /private/tmp/integration-producer-review-test.log includes timed-out descendant cancellation leaving old pass invalidated and pending result. No all-handler coverage claim.

Falsification: The disposition fails if the named fixture is absent, no longer imports/dispatches this source, or the stated control does not exercise that chain. Unchecked individual handlers are not claimed covered by finding an external test file.

## F27  -  scripts/canary/craft-backend-canary.py:55

Rule: `writing-tests-5`. Enclosing function: `load_json`.
Raw report: source has 7 except block(s) but no test file found (looked in tests/, scripts/canary/tests/, ...)

Proposed disposition: false positive for the specific heuristic/expected outcome; independent acceptance pending.

Reason: Test-discovery heuristic only: the scanner does not locate this repository's mapped `_test` fixture. Relevant chain: manifest/artifact reads -> exact/digest/confined canary setup/evidence/cleanup validation. This finding supplies no per-handler coverage measurement.

Evidence and function/caller chain: bin/_test/craft_backend_canary_test.py imports and dispatches actual canary helpers for missing/corrupt runtime artifacts, confined paths, registration, evidence and cleanup. Supplied fifteen-test PASS /private/tmp/canary-refresh-tests.log. Tests use isolated homes; they do not attest actual live backend delivery or every exception handler.

Falsification: The disposition fails if the named fixture is absent, no longer imports/dispatches this source, or the stated control does not exercise that chain. Unchecked individual handlers are not claimed covered by finding an external test file.

## Binding and acceptance boundary

The JSON metadata is the full identity/raw appendix. Source/test blobs come from
the exact candidate tree, with protected-base blobs or explicit new-file absence.
External controls, logs and review artifacts have byte counts and SHA256 pins.
The coordinator's frozen13 source pin file was checked against candidate bytes.
Independent reviewer approval is null until that review completes.
Later source changes require row/identity/raw reconciliation and re-review; later
aggregate/protected CI and actual host delivery are separate acceptance evidence.
