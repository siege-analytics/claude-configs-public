# Hostile review: proportional review risk policy

## Scope

Independent deep review of classifier, policy, commit-msg, prompt-time push/PR gate, native pre-push history gate, package/deploy runtime, and adversarial fixtures.

## Findings and resolution

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| H1 | S2 | Commit-msg unconditionally skipped merge/revert/fixup/squash subjects. | Removed subject-based bypasses. Native pre-push explicitly excludes only true multi-parent merge commits because policy scope is non-merge commits. |
| H2 | S2 | Pre-push/runtime line grep accepted body text, duplicate tiers, and ambiguous trailers. | All gates use `git interpret-trailers --parse`; exact cardinality is enforced. |
| H3 | S2 | `[no-review]` was enforced only by commit-msg. | Commit-msg, runtime, and pre-push independently permit it only after Tier A classification. |
| H4 | S2 | Any tierless HEAD was treated as legacy. | Policy pins `legacy_before_epoch`; post-policy tierless commits block. Pre-policy commits retain full legacy validation. |
| H5 | S2 | Tier A exited before universal ticket traceability. | Ticket or explicit `[no-ticket]` is checked before Tier A/no-review exits in all creation/push gates. |
| H6 | S2 | Tier C promises were not mechanically complete. | Require Hostile-Review, Negative-Tests, Full-Suite, and Canary-Rollback trailers plus pre-mortem/hostile fields in the full artifact. |
| H7 | S2 | Installed commit hook resolved only target-repo runtime. | Resolve hook-relative packaged runtime with source-repo fallback; package and deploy classifier/policy; deployment test asserts both. |
| H8 | S2 | Delete/rename/root/missing-policy and other attack shapes lacked coverage. | Added A/C/D/M/R/T + no-renames classification and fixtures for deletion, rename, root commit, missing/malformed policy, symlink/critical path, submodule default, copy/docs, duplicates, and tierless history. |
| H9 | S2 | Editable policy could remove its own Tier C pattern. | Code-owned bootstrap floor plus independent hardcoded floors in commit-msg, runtime, and pre-push protect classifier, policy, and enforcing hooks. Test strips all data-driven high-risk patterns and still gets Tier C. |
| H10 | S2 | Pre-push accepted empty artifact paths. | Validate committed Tier B/C sections and Tier C evidence fields; hostile file paths must be non-empty. |
| H11 | S2 | Commit-msg only warned when a local artifact path was absent. | Missing path-like sources now block; explicit URL/ticket pointers remain supported. |

## Residual boundary

No repository-local control is literally uneditable by a repository change. The bootstrap floor is duplicated across classifier and three enforcement boundaries so a single policy/classifier edit cannot downgrade itself. GitHub protected required checks remain the external merge boundary. Emergency `--no-verify` remains visible but native pre-push and hosted CI supply subsequent gates.

## Verdict

No completed-review S1/S2 finding remains unresolved. Merge remains conditional on full local and protected hosted checks.
