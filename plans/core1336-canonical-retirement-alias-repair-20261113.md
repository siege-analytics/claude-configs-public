# Canonical retirement alias repair

Refs #1336. Base: 558b8808a954e220942774d6eac8419f1dd94dae.

## Assumptions

Source consulted: resolve-think-gate.py own-lifecycle dispatch, canonical claim writer, Task enumeration and task_keyed_gates.py lifecycle fixtures. Own lifecycle returns before enumeration. The prior enumeration path recorded Task id and ticket, while lifecycle cleanup recorded only Task id. A direct allowed deletion could therefore revive a legacy ticket gate. This informed a shared denial-alias calculation used by both paths; claim storage, session ownership, ambiguity and scope checks stay unchanged. Ticket aliases remain retirement records, never Task selection grants.

## Test plan

The new real universal-mutation-gate regression creates a canonical Task id plus a ticket-only legacy copy, verifies no canonical claims exist, resolves the owned rm before any enumeration, removes the fixture gate, then checks no legacy admission returns. Before the production edit it failed because the legacy gate revived. After the edit the new regression, prior enumeration retirement, same-issue distinct Task/ambiguous selector and legacy-only compatibility controls passed: four tests in 4.985s. Existing own-session lifecycle and reserved placeholder controls passed in 8.511s. One requested recovery test initially used the wrong unittest class and was not run in that invocation; the corrected ResolverRecovery unreadable-lifecycle test passed in 0.003s. A final single invocation of all seven focused controls passed in 12.814s; Python compilation and diff whitespace checks passed. No full-suite, hosted CI or installed runtime claim.

## Findings

The requested cohort base is used in a separate feature worktree; canonical prepare-task-branch.py only supports develop selection, so git worktree add selected the authorized exact cohort without changing existing worktrees. No runtime files, worker indexes or remote refs were changed.

## Independent review

Root independently read the complete three-path patch and accepted it: the shared helper preserves enumeration semantics and extends denial-only retirement to direct lifecycle cleanup. Root independently ran the new real UMG regression: PASS, 0.515s, exit 0. This acceptance was received after the author tests and before commit; it is not a pre-edit review claim. The complete PR scan remains non-clean (131 findings); this functional repair is separate from those per-finding dispositions and makes no scan-clean claim.
