# Self-review: #1003 Craft/backend canary packet

Pre-mortem-artifact: plans/pre-mortem-1003-craft-backend-canary.md
Hostile-review-artifact: plans/hostile-review-1003-craft-backend-canary.md

## Assumptions

- The driver prepares artifacts only and cannot create a Craft session/workspace, install, delete, publish or mutate a provider.
- Direct user instruction outside the manifest is the only future live-run authority. A recorded approval source/reference cannot verify or create that authority.
- Imported host exports can be checked for internal consistency but remain unverified until independently observed through an approved live procedure.
- Installed application/package presence is artifact evidence, not proof that a live session selected that backend or adapter.
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
- The prior canonical resolver protected `KERNEL.md` but did not emit composition `RESIDENT.md`. The separately owned selector render-mode correction was independently accepted at `c4f27563e0d09b3116c9b5ad123e8c2cc4dfb957` and normally integrated as `6a3c2efc593f209ba6d9594a29e43bfb8cab634a`. Materialization and fresh attestation now invoke that canonical final-payload hook and require exact resident/kernel counts, both scoped skills and absent controls; arbitrary kernel-path rejection remains unchanged.
- The accepted-develop packet cannot call production `build.py --deploy`, whose current-origin/main check remains intact. A separately pinned setup script copies an exact top-level allowlist, rejects changed/unexpected/symlinked content, runs only disposable hook registration/wiring/verification, and creates no production deploy stamp.
- Setup previously trusted that materialization had been attested earlier, leaving source install/wire/verify scripts and fixture configuration mutable before execution. The setup entrypoint now reruns shared attestation immediately before its first workspace mutation, checks exact HEAD/full clean tree/package/composition/payload plus canonical origin/local bare push transport, and binds that receipt. Regression mutations prove no workspace copy or setup command occurs after source, identity or transport drift.
- The approval subject previously included lifecycle `status`, so proposal → approval-recorded changed the digest named by external approval. The subject now excludes only `status` and `operator_approval`; a regression proves lifecycle stability and stale-approval rejection after substantive backend mutation.
- Connection/model aliases did not bind installed host/backend builds. The subject now separately pins exact Craft application manifest/main bundle, Claude SDK manifest/version and Pi/OpenAI implementation markers. Read-only discovery is captured at materialization and replayed by fresh attestation; backend evidence must bind its digest and artifact-backed host-observed active runtime identity. Missing identity remains `unsupported-unverified`, and the Pi adapter cannot imply Codex CLI behavior.
- The first discovery tests accidentally required this Mac application and therefore could not run on hosted Linux. Internal-only dependency seams now inject a real temporary artifact reader and platform temp base into unit materialization/attestation/evidence/setup paths; production CLI defaults remain exact `/Applications/...` and `/private/tmp`. The portable test exercises matching, changed, missing, symlinked and missing-adapter-marker files, retains real source/package/composition/local-hook work, and is registered exactly once in the hosted build workflow.
- Raw substring extraction treated `NO_OP_RESTORED` as a second `NO_OP` start and compaction variables were initialized too late. The executable README regression now matches prescribed delimiters in actual user content and proves complete, distinct no-op/restored and compaction before/after slices; backend identity/evidence directory are initialized before the first compaction receipt.

## Peer review

Pending independent exact-head review after accepted provider/native integrations and final digest refresh.

## Lead review

Self-review found and corrected three blockers: nondeterministic package timestamps, missing Git ancestry in archive materialization, and self-written approval/evidence escalation. The current driver returns `authorization_effect: none`, labels imported evidence unverified, and exposes no live launcher or deletion path. Independent review remains required.

## Quantified claims

Twelve focused tests pass without creating a Craft workspace/session. They cover path confinement, missing approval/prerequisites, detached source/package/composition/payload materialization, canonical synthetic identity over local transport, selected resident content and controls, native trailers, exact allowlisted payload copying without a deploy stamp, existing-root refusal, exact-byte attestation, exact event cardinality, artifact confinement/digests, backend/transition/overall budgets, unsupported capability state, no-self-report, synthetic relabeling, side-effect closure and cleanup residue. The proposal validates in preparation mode and rejects `--require-approval-record`; structurally consistent imported evidence remains unverified and non-authorizing.

## Pending before publication

- Refresh exact generated package/payload observations from one post-review materialization before external approval; stable accepted source/canonical/composition/driver pins are already refreshed.
- Complete the Python/hook/workflow/package/scanner/freshness publication matrix, including installed-build discovery and stale/unverified identity denials.
- Publish a draft PR and obtain independent exact-head review.
- After review/integration, materialize exact package bytes and request separate direct user authorization; the remaining shared-parent #1002 slice is not claimed or satisfied by this packet.

## Explicit non-claims

No live session/workspace was created; no host canary, installation, credential read, provider mutation, release, protection change, `main` change, #1017 review or rollout occurred. A reviewed preparation PR does not authorize a live run.
