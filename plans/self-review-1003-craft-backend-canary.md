# Self-review: #1003 Craft/backend canary packet

Pre-mortem-artifact: plans/pre-mortem-1003-craft-backend-canary.md
Hostile-review-artifact: plans/hostile-review-1003-craft-backend-canary.md

## Assumptions

- The driver prepares artifacts only and cannot create a Craft session/workspace, install, delete, publish or mutate a provider.
- Direct user instruction outside the manifest is the only future live-run authority. A recorded approval source/reference cannot verify or create that authority.
- Imported host exports can be checked for internal consistency but remain unverified until independently observed through an approved live procedure.
- Final accepted #1002/#845/develop identities and materialized exact package bytes must be refreshed before review or authorization.

## Classification

Tier C. The driver prepares executable fixtures, records externally supplied approval evidence, defines imported host-evidence consistency checks and observes cleanup. A false allow could expose shared runtime state; dependency and mutation coverage are mandatory.

## Dependency closure

- Driver: `scripts/canary/craft-backend-canary.py`
- Exact disposable setup: `scripts/canary/setup-disposable-workspace.py`
- Behavioral tests: `bin/_test/craft_backend_canary_test.py`
- Proposal: `examples/probe-matrices/craft-backend-canary/approval.proposal.json`
- Evidence template: `examples/probe-matrices/craft-backend-canary/host-evidence.template.json`
- Cleanup template: `examples/probe-matrices/craft-backend-canary/cleanup-receipt.template.json`
- Runbook: `examples/probe-matrices/craft-backend-canary/README.md`
- Pre-mortem and hostile review: `plans/pre-mortem-1003-craft-backend-canary.md`, `plans/hostile-review-1003-craft-backend-canary.md`

The final change must register driver/tests/templates in the review-risk policy and regenerate review-risk metrics/source authority.

## Self-review findings

- Initial full-tree package pins were nonreproducible because three generated JSON files contain `built_at`. The packet now pins canonical package content with only those explicit fields normalized, records exact materialized bytes, and requires re-attestation against a digest-bound external approval record. The record has `authorization_effect: none`; the driver cannot grant approval.
- A source archive lacked Git ancestry needed by immutable policy selection. Materialization now uses a detached local clone at the full source revision, validates the source tree listing, builds with full history, and requires zero tracked drift.
- Cleanup receipts originally implied a retained file outside the allowlist. `verify-cleanup` now accepts stdin and performs no deletion, allowing receipt text to be reviewed without creating another path.
- Proposal-only refusal now occurs before unresolved live prerequisites, making the authorization boundary explicit.
- Evidence now requires exactly nine unique named events per backend, unique confined artifact bytes with matching digests, and actual per-backend/transition/overall intervals within the pinned budgets; returned counts/timing are observed rather than hard-coded.
- Startup, no-op and compaction probes no longer substitute ordinary reads/errors for capability evidence. The runbook requires host registration/invocation/boundary records, a real disposable zero-output resolver adapter with exact restoration, and post-compaction nonce plus denial behavior. Missing host records remain `unsupported-unverified` and fail validation.
- Materialization now gives the fixture the approved strict-release identity without network use: it seeds the bare fixture through a local URL, then stores the canonical origin without `insteadOf` rewriting that would corrupt resolver identity. It includes foreign/global negative controls and native commit trailers.
- A reproduced payload-order bug showed generic package `bin/catalog` overwriting composition-specific resolver data. Assembly now copies generic dependencies first and the declared strict-release composition last; the final payload resolver must select strict-release plus both scoped skills.
- The current canonical resolver correctly protects `KERNEL.md` but does not emit composition `RESIDENT.md`. A separate owner is implementing a bounded canonical selector render-mode correction; this packet will not duplicate it and remains blocked until that exact head is independently accepted, normally integrated, repinned, and exercised through the actual registered hook. Arbitrary kernel-path rejection must remain unchanged.
- The accepted-develop packet cannot call production `build.py --deploy`, whose current-origin/main check remains intact. A separately pinned setup script copies an exact top-level allowlist, rejects changed/unexpected/symlinked content, runs only disposable hook registration/wiring/verification, and creates no production deploy stamp.

## Peer review

Pending independent exact-head review after accepted provider/native integrations and final digest refresh.

## Lead review

Self-review found and corrected three blockers: nondeterministic package timestamps, missing Git ancestry in archive materialization, and self-written approval/evidence escalation. The current driver returns `authorization_effect: none`, labels imported evidence unverified, and exposes no live launcher or deletion path. Independent review remains required.

## Quantified claims

Ten focused tests pass without creating a Craft workspace/session. They cover path confinement, missing approval/prerequisites, detached source/package/composition/payload materialization, canonical synthetic identity over local transport, selected resident content and controls, native trailers, exact allowlisted payload copying without a deploy stamp, existing-root refusal, exact-byte attestation, exact event cardinality, artifact confinement/digests, backend/transition/overall budgets, unsupported capability state, no-self-report, synthetic relabeling, side-effect closure and cleanup residue. The proposal validates in preparation mode and rejects `--require-approval-record`; structurally consistent imported evidence remains unverified and non-authorizing.

## Pending before publication

- Integrate the final independently accepted `develop` prerequisites and refresh every source/package/composition/payload/driver digest.
- Register the setup driver in Tier C risk/workflow coverage and run the complete Python/hook/workflow/package/scanner/freshness matrix.
- Publish a draft PR and obtain independent exact-head review.
- After review/integration, materialize exact package bytes and request separate direct user authorization; the remaining shared-parent #1002 slice is not claimed or satisfied by this packet.

## Explicit non-claims

No live session/workspace was created; no host canary, installation, credential read, provider mutation, release, protection change, `main` change, #1017 review or rollout occurred. A reviewed preparation PR does not authorize a live run.
