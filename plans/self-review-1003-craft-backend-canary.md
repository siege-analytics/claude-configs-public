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

## Peer review

Pending independent exact-head review after accepted provider/native integrations and final digest refresh.

## Lead review

Self-review found and corrected three blockers: nondeterministic package timestamps, missing Git ancestry in archive materialization, and self-written approval/evidence escalation. The current driver returns `authorization_effect: none`, labels imported evidence unverified, and exposes no live launcher or deletion path. Independent review remains required.

## Quantified claims

Seven focused cases pass without creating a Craft workspace/session: path confinement, missing external approval, prerequisite pins, detached source/package materialization, existing-root refusal, exact-byte attestation, imported host-event provenance/order, no-self-report, synthetic relabeling, side-effect closure, timeout floor, and cleanup residue detection. The 12 review-policy cases and review-risk dependency/mutation audit pass. After integrating accepted provider/native develop, 16 native scenarios and 13 provider scenarios also pass. The proposal validates in preparation mode and rejects `--require-approval-record`; structurally consistent imported evidence remains unverified and non-authorizing.

## Pending before publication

- Run the complete combined Python/hook/workflow/package/scanner/freshness matrix.
- Publish a draft PR and obtain independent exact-head review.
- After review/integration, materialize exact package bytes and request separate direct user authorization; the remaining shared-parent #1002 slice is not claimed or satisfied by this packet.

## Explicit non-claims

No live session/workspace was created; no host canary, installation, credential read, provider mutation, release, protection change, `main` change, #1017 review or rollout occurred. A reviewed preparation PR does not authorize a live run.
