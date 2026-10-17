# Self-review: #848 effective-policy resolver

Pre-mortem-artifact: this document, "Failure analysis" and "Peer review" sections
Hostile-review-artifact: this document, "Peer review" section

## Assumptions

- `catalog/effective-policy.json` at `3e42303b0ed999524f3ddec75f2ce5b0892aac4f` has an independent content-only ACCEPT with exact blob/raw/canonical hashes. The working copy is proposal-only. `parent_contract_revision` identifies the accepted #851 contract source, not policy approval.
- #848 is configured-policy evaluation only. Trusted protected/live adapter evidence remains unavailable until #1002/#1003.
- The bounded pilot covers exactly the three #851 fields and two synthetic identities; broader composition and migration remain separate tickets.

## Scope

Bounded to the three #851 pilot policy fields, two synthetic repository identities, pure `explain/check/validate` evaluation, generated manifest agreement, and documentation. It does not implement skill/resident composition (#1001), actual workflow enforcement (#1002), live host discovery (#1003), rollback execution (#1004), release, deployment, installation, or `main` mutation.

## Authority model

- Active policy is loaded from the exact selected ancestor commit/blob and checked against reviewed raw/canonical digests. The receipt is separately sealed in resolver code; working policy/fixture edits remain proposals and missing/non-ancestor history or digest drift fails closed.
- Parent defaults come from `catalog/gate-contracts.json`; organization and project patches are independently checked against its allowed paths.
- Exact canonical host/owner/repository identity selects one project. Missing/foreign/disagreeing identity does not inherit another project.
- Candidate policy, installation metadata, task evidence, and capability state cannot alter precedence. A candidate is diagnostic-only and is never selected as its own approved policy.
- Policy allow and capability readiness remain separate from final enforcement. Even caller-supplied `verified` states cannot produce final allow in #848; trusted protected/live adapter proof is deferred to #1002/#1003.

## Failure analysis

| Failure | Prevention/evidence |
|---|---|
| Working-tree loosening authorizes itself | Resolver decides with approved object; candidate appears only under `proposed_policy` with `authorization_effect: none` |
| Basename or current-directory identity leaks project state | Pure evaluator requires explicit host/owner/repository; foreign and ambiguous negatives |
| Locked field changed at org/project layer | Path allowlists from #851 reject at source validation |
| Correct value declared at wrong layer | Layer-specific allowlists reject even if the resulting value would be schema-valid |
| Capability metadata manufactures authorization | Capability inputs affect descriptive readiness after policy decision, never values/provenance or final allow; CLI exit tests prove caller-supplied `verified` remains fail-closed |
| Generated copy drifts | Exact source object and digest embedded; protected CI validates agreement |
| Resolver CI silently becomes conditional | Existing exact protected-step validator now seals both resolver commands |
| Resident text disagrees with guard values | `resident_workflow` renders directly from the same resolved values |
| Project A state appears in project B | Resolver has no process-global selected project; each call reconstructs values from parent defaults |

## Peer review

A pre-publication hostile audit reproduced one blocking flaw: caller-supplied `verified` capability states could make final decision `allow` and `check` exit 0 without a trusted host/protected adapter. That exploit is closed: policy-allowed operations remain final `unknown`, with exact CLI exit tests.

A collaborator then reproduced a second blocker at `d13c239`: editing both the mutable catalog and matching fixture changed active policy/resident text under the unchanged claimed revision. The first head is rejected. The corrected policy snapshot at `3e42303…` received a content-only ACCEPT. The remediation now loads that exact ancestor commit/blob, verifies the recorded hashes and review URL, seals the receipt, and treats working-tree catalog/fixtures only as proposals.

## Lead review

The coordinating session re-executed the capability spoof directly after remediation: synthetic trunk `feature -> main` returns policy `allow`, final `unknown`, and `check` exit 1 even when both required capabilities are passed as `verified`. It reproduced the dual-edit previous-policy gap, invalidated the first head, then reran the same dual edit in a disposable clone: selected policy remains strict `develop`, `feature → main` remains denied, resident text remains `develop`, and the working loosening is reported only as a proposal.

## Quantified claims

- Focused resolver suite: 33/33 tests, including immutable selection, receipt/hash mismatch mutations, generated-selection drift, and the original dual-edit reproduction.
- Existing gate-contract suite: 20/20 tests.
- Repository Python modules: 21/21 under Python 3.13.
- Native hook suites: 36/36.
- Workflow policy suites: 2/2.
- Ontology: 34 terms and 136 bound values.
- Generated authority: 198 sources, 804 artifact snapshots, 2,904 mappings.

## Test plan

- Focused resolver mutation suite: precedence, source/path/value validation, identity normalization and ambiguity, candidate self-authorization, capability readiness, evidence confusion, ticket matching, review authorization effect, generated agreement, duplicate JSON keys.
- Existing gate-contract suite and probes.
- All Python module tests, hook suites, workflow tests, full build, generated-source authority, ontology generation/check, skill inventory, and package validators.
- Independent exact-SHA hostile review after publication. Any new head invalidates its verdict.

## Residual risk and deferred proof

Capability values are explicit unauthenticated evaluator inputs, not runtime-discovered facts. #1003 must prove trusted adapters and live states. #1002 must prove an actual protected workflow consumes the same policy and is the first slice permitted to produce final allow. #1004 must prove rollback and prior-approved revision recovery. No claim here upgrades configured metadata to runtime-observed or acceptance-blocking evidence.
