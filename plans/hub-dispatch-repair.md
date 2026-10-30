# Hub dispatch accounting repair — #1133

## Assumptions

The approved remediation plan P0.8/P4 and the operator's instruction to finish authorize this scoped repair. Administrative caps are load shedding, not a permission boundary. Session metadata is the observed source of child liveness; hub-threads.json is derived state. Missing host callbacks remain a documented bounded-lease limitation, never fabricated completion.

Pre-mortem-artifact: plans/hub-dispatch-repair.md
Hostile-review-artifact: plans/hostile-review-hub-dispatch.md

## Design and investigation

Current main reserves before its parallel sibling protocol guard denies requests. The successful-child parser ignores outer content arrays. Validate the same existing protocol before the locked admission boundary, keep the existing session/task policy, parse direct/content/outer-array results, release only matching failures, and bind idempotent request identity to argument fingerprints. A hub without a host call ID must use an explicit unique CCP_SPAWN_REQUEST_ID prompt token. Unknown-role/steward communication remains unrestricted. No speculative global session-task adoption is added.

Alternatives considered: shorter expiry alone leaves ordinary rejected calls exhausting capacity; model acknowledgment is not evidence of child creation. A host-wide transaction would be stronger but is outside these hooks. Existing flock/atomic replacement serializes local derived-state updates.

## Pre-mortem

A different sibling can still deny after validation without completion: keep the bounded existing lease and report host limitations. Reused request tokens could hide distinct calls: require identical argument fingerprints. Duplicate success callbacks could duplicate load: retain request identity on the witnessed child. Error wrappers might contain IDs: error-bearing envelopes do not count as success. Source/package parity can drift: generated checks and full CI remain mandatory.

## Peer review

Independent review requested against exact source; no approval claimed yet.

## Lead review

Checked shared protocol authority, request identity and task count boundaries. No user projects or live source settings changed during implementation.

## Quantified claims

Focused Hub suite passes 14 tests before the final fingerprint amendment; final rerun recorded separately. Canary and full hook checks remain separate receipts.

## Test plan

Real subprocess tests cover repeated protocol-denied calls, slot admission, exact task isolation, outer-array completion, failure/cancellation release, duplicate callbacks and idempotent argument-bound tokens. Preserve all original communication/steward/concluded-child controls. Rollback restores the previous reviewed package; retain derived-state evidence and allow leases to expire without deleting unrelated children.

## Independent correction and acceptance

Independent reviewer reproduced two phantom/replay bugs and a nested error variant. Corrected all before integration. Completed requests and explicit pending token retries now deny instead of authorizing another tool execution; duplicate Post remains idempotent. Overall failure suppresses child creation across all recognized wrappers. Reviewer approved revised sources; focused2 tests pass4.789s, Hub14 pass26.096s before final nested-wrapper-only correction. Full integrated suite follows.
