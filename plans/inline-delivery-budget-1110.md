# Complete inline hook delivery (#1110)

## Context and evidence

Exact ticket candidate 18727842cc01207ed21f5e653cea3eae5b6e89e3 emitted 10008 UTF8 bytes for the existing large-selection case at a valid 73-byte checkout root. The selector budgets capability content, while final delivery also contains the mandatory kernel, repeated absolute paths and optional plan warnings. The completed baseline retained that failure; the other 51 hook launchers, full review risk, scanner fixtures and freshness checks passed. The old temporary checkout disappeared during another run; committed source was recovered intact into a durable worktree.

## Design and acceptance

Buffer the existing complete delivery before publishing it. Below 10000 bytes, publish the original output unchanged. At or above that boundary, replace optional selection, resident and plan-warning content with the complete canonical kernel plus a short visible over-budget/kernel-only diagnostic. If mandatory delivery itself cannot fit, or private buffering fails, emit one structured blocking response. Never truncate UTF8, the kernel or a selection. Capability selection, task permissions and the existing byte limit do not change.

The normalized metrics checker measures the real hook in a private, fixed 32-byte reference root. It copies only fixed runtime/data files and selected hash-checked canonical source data, isolates ambient plans and interpreter settings, and refuses nonregular source reads. This reporting reference does not alter the production cap or its long-root tests.

## Assumptions

The private temporary file has one hook writer and is cleaned on exit; this is not a multiwriter filesystem CAS claim. Canonical source remains the policy authority. Existing early invalid-kernel checks remain. Live Craft delivery and protected CI are separate rollout requirements.

## Pre-mortem

The main risks are counting characters instead of bytes, publishing a partial load set, dropping mandatory policy, corrupting under-budget output, missing late plan warnings, leaking a private buffer, or treating a storage error as a successful empty response. Actual tests cover long roots, 9999/10000-byte boundaries, multibyte output, Unicode warning paths, oversized mandatory UTF8 policy, unavailable temporary storage, unchanged normal output and cleanup. The existing one-interpreter and kernel-validation cases remain.

## Peer review

Independent review accepted the frozen delivery implementation and separately ran its actual delivery tests and the added metrics portability controls. The exact source identities, FD/ERR handling assessment and limits are recorded in the hostile-review artifact. Scanner, graph and final integration results remain separate evidence.

## Lead review

The change stays at final publication. Existing rendering is buffered without editing its selection algorithm. Private buffering preserves trailing bytes, while the direct failure descriptor can emit a sole blocking response before publication. The test and its existing launcher are protected at tier C, with the review-risk downgrade and dependency negatives retained.

## Quantified claims

The original progressive fixture passed 20 cases after the repair, and nine new actual-delivery and portability tests passed, including a separate independent run. Dependency graph verification passed without invocation snapshot changes. The completed baseline and final producer evidence are retained by the coordinator; no clean overall baseline or live-host acceptance is claimed.

Pre-mortem-artifact: plans/inline-delivery-budget-1110.md
Hostile-review-artifact: plans/hostile-review-inline-delivery-budget-1110.md
