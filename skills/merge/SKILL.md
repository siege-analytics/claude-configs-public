---
name: merge
description: Merge a reviewed branch or pull request using the target project's approved topology, method and readiness conditions. Use for integration, release or hotfix merges; project policy supplies the applicable route and authority.
allowed-tools: Bash
---

# Merge a reviewed change

Use this shared procedure with the target project's selected policy. A project extension may supply release roles, billing exceptions or additional readiness; it does not grant authority or weaken the safety kernel.

## Establish the operation

Identify the target repository, source and destination branches, current commits, pull request and your assigned role. Inspect the target's approved policy and existing instructions. Use [`develop-guard`](../develop-guard/SKILL.md) for the normal develop integration route and safe bootstrap when it is missing. Repository defaults or observed main-only history do not select a different normal-development base. Separately authorized release/backport operations retain their exact approved source and destination.

An integration branch identifies a feature target, not a release or hotfix route. For those operations, require the matching project procedure and its authority. For the Siege scaffold, K5 and [`develop-guard`](../develop-guard/SKILL.md) own feature/fix -> develop -> main and exact-main deployment; [`writing-releases`](../_writing-releases-rules.md) owns applicable release artifact/version mechanics. A generic example, available branch or selected procedure cannot override that boundary.

## Establish readiness

Apply [`standing-approval`](../_standing-approval-rules.md) to the existing authorization and its conditions. Use [`self-review`](../self-review/SKILL.md) and the project's selected review procedure for required artifacts, reviews and evidence. Inspect the exact source-bound results before treating evidence as missing.

Complete missing preparation within your role and obtain required independent review. Keep the dependent merge stopped until its actual prerequisites pass; continue independent authorized work. An instruction to merge is not a waiver of review, protected checks, role limits or an explicit owner hold. Ask only for a missing material decision or authority.

Verify immediately before the merge:

- Remote source and target match the reviewed scope; no unexpected commits or local work would be overwritten.
- Required reviews, checks and project-specific release conditions cover the current snapshot.
- Your role and existing grant cover this operation, including its destination and method.
- No applicable owner hold, ownership conflict or unresolved material choice blocks it.

## Perform the approved merge

Use the project's normal pull request, merge queue or approved Git procedure and configured merge method. Bind the operation to the reviewed head where the host supports it. Do not substitute local protected-branch pushes for the declared workflow or invent an admin/billing exception when a check rejects the operation.

Resolve routine conflicts within an implementation-authorized role by inspecting both intended changes and validating the result. Changed source receives the review and checks it requires. Escalate incompatible requirements or an unresolved product/authority choice; hold that merge. Review-only work does not authorize edits.

If execution fails, inspect current durable state before retrying: the merge may have succeeded despite a transport error. Preserve evidence and report the specific failed predicate rather than assuming success or reopening settled authorization.

## Verify and hand off

Observe the actual merge result and resulting commit/tree. Verify any required post-merge checks, release publication or deployment separately; a merged PR alone is not proof of delivery.

Update the work item and give the next responsible actor the resulting commit, scope, verification and remaining dependencies. Follow the project's ticket and session-status policy. If the source contains an authorized hotfix or release-only change, perform any project-required synchronization through its reviewed path.

Clean up only fully merged branches within your authority that are unused and not retained. Keep active worker branches, main/integration branches and audit-retained branches. Cleanup is not a condition of declaring a verified merge complete. [`compound`](../compound/SKILL.md) is advisory.
