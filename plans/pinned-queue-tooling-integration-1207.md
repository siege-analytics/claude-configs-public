# Pinned queue enqueue and applicable verification

## Assumptions

Goal source: Core#1207, Core#1156 and the operator's report that the already-authorized remote reviewer could not enqueue SU PR1794. Working as software engineer, source reviewer and release maintainer.

Pre-author-inventory: develop3956000f937f036e624b10b5402d89e8526c74f3 contains the reviewed runtime/instruction packet and passed all 67 hosted hook files. Its mutation gate has no remote queue-enqueue model. Remote evidence shows the sole ordinary reviewer/merger had existing authority; its only local task gate described a different review. A local file scope cannot represent the queue operation. SU1794 has already merged at560a858e after a separate one-time operator direction; that exception grants no future bypass.

Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1207
Pre-mortem-artifact: plans/pinned-queue-tooling-integration-1207.md#test-plan
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1207
Project-contribution: admit the compliant pinned queue actuator without another local task/permission loop, while preserving server queue requirements and actual role authority.

## Design before integration

Implement the ticket's two bounded standalone enqueue forms without requiring a local task gate. Existing policy and role decisions remain outside this command-shape hook, as with supported issue metadata. This is not arbitrary GitHub mutation permission.

The CLI form must include an exact full head pin and be proven to target a queue-required branch; otherwise the same CLI command could merge directly. The GraphQL form must be exactly one recognized enqueuePullRequest operation with a full expectedHeadOid, not an arbitrary mutation containing that word. Never admit admin, REST/direct merges, dequeue, unpinned auto-merge, extra operations, wrappers or composed local writes through this lane.

Every admission must append a structured own-session audit entry identifying the target, expected head and session. The entry means the hook admitted a constrained command; it does not claim the remote operation succeeded. Use bounded fixed read-only discovery where needed and existing session/parser mechanisms. Do not introduce a new per-repository approval policy, role-grant loader or task-written blanket grant.

Also apply the two supported promotion-review corrections: create a unique task branch in the worktree example, and use the target project's actual test/documentation tools in the Lead checklist. Applicable evidence remains mandatory. Revise the operational checklist's old command block and its provenance pin; preserve both artifact-template/field golden regions and unrelated checklist bytes.

## Test plan

- With no local task gate, admit both exact pinned enqueue shapes and require the corresponding audit entry.
- Deny admin, missing/short/nonhex head pins, unpinned auto, direct REST merge, dequeue, extra GraphQL operations and missing expectedHeadOid.
- Deny wrappers, shell expansions, redirections and chained writes riding the exemption. Preserve ordinary operation classification and task ownership elsewhere.
- Check CLI target resolution, active queue proof and bounded read failures. Do not present a policy-read/execution race as atomic enforcement; the server remains authoritative.
- Check own-session audit path integrity and observable failures without logging raw credentials or private command bodies.
- Run source and both consumer hook validators, risk-floor controls and the relevant existing task/reader/provider/project regressions after combining the sources.
- Exercise the real named-branch worktree command and review package/native artifact-parser compatibility after the narrow tooling correction.

The audit path, parser, queue semantics and shell composition are launch-blocking risks. Keep focused positive and denial controls tied to actual source. Run genuine content-bound tests, then required exact-head protected CI. No source candidate installation, fabricated receipt, hook bypass or protected-branch shortcut is authorized.

## Peer review

Root independently accepted the four-file documentation correction after inspecting its complete diff and recorded source pins. Its author reported both-layout build, seven disclosure cases and coordination checks passing; the first new Git fixture's overly broad stdout assertion was corrected without changing production behavior. Queue source review remains pending its author's frozen implementation and actual tests.

## Lead review

Keep the established sole-merger role; no parallel merger or new permission request is created here. Prior source validation and current main-promotion checks are not proof of this new helper. Preserve operator settings, holds, restored sessions and the normal develop/main path. Client imports must verify the UMG composition against the final published Core, recompose the changed self-review override, refresh all five baseline pins and update the adapter's sole guard pin and actual Core revision. Determine guard hashes from actual source bytes.

## Quantified claims

At the initial pre-integration checkpoint, the preceding packet passed 67 hosted hook files and its 21 selected commands. The separate documentation correction passed seven focused disclosure cases. New queue-helper results follow; combined validation and installed behavior remain separate.

## Reviewed queue source and corrective evidence

The first queue author run passed seven methods. Root's independent review then reproduced two defects: whitespace normalization changed quoted GraphQL node/head values, and a local self-review hook blocked the remote operation by examining an unrelated local commit. The corrected source tokenizes GraphQL without changing quoted values and shares a pure shape classifier with eight local publication/destructive guards. The mutation resolver alone performs queue proof and mandatory audit. A full-stack fixture with an unrelated unreviewed local HEAD and ignored tests admits both supported forms, writes exactly two resolver audit entries and retains local push denials.

The corrected author suite passed nine methods in 17.464 seconds. A separate reviewer passed the two corrective methods in 3.657 seconds and accepted the exact corrected source. Root then removed an unnecessary ambient GH_REPO veto: normal repository routing is shared by proof and invocation, while the returned PR/head/queue still bind the resource. The extended actual-hook suite passed ten methods in 18.646 seconds, including an execution cwd outside every Git checkout, environment repository routing, literal GraphQL targeting and alternate-host denial. That small delta and the canonical command documentation received independent source acceptance. No role-grant loader or local task gate was added.

The pre-merge queue policy read is bounded but not atomic with later CLI execution. The actual queue mutation still belongs to GitHub and the authorized sole merger. The inspected held global legacy guard can continue blocking the CLI form after a workspace-only update; the exact GraphQL enqueue form is the intended live route there, without releasing any hold or using a direct merge endpoint.

Both component patches are combined before canonical regeneration. Source fixtures are not a new protected CI result, actual queue enqueue, publication or installation. Preserve earlier failures and source-only limitations rather than relabeling them.
