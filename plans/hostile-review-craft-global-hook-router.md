# Independent global Craft router review

Disposition: ACCEPT current frozen staged source in /private/tmp/craft-global-hook-router, subject to exact integration/commit verification and actual host canary. No remaining must-fix found in this bounded slice. Staged binary diff SHA256: 9aa331013a6a5684aa8e102dad728216a7ae6a348ce98358cba5b38671048670.

Independently reran router 18 tests PASS (4.893s) and workspace trust 9 tests PASS (1.262s), fake HOME/temp fixtures only. No live apply or user/global settings writes performed.

Reviewed native/unenrolled skip before receipt/policy reads; Craft ancestry and explicit workspace enrollment; receipt-pinned policy/router/strict anchor/classifier/task resolver; main-only immutable installer source; preservation of foreign/global/operator settings; private backups, snapshot compare-and-swap and staging-first/active-last activation. Activation is not a multi-file transaction. Later source/policy drift and partial activation fail closed rather than claiming success.

Corrected blockers were rechecked: malformed enrolled session bindings no longer skip enforcement; raw callback craft IDs cannot give unbound mutations authority; registered mapping excludes tolerant raw anchors and requires unique physical structured/header provenance; strict binding survives downstream legacy correction; a mapping that becomes ambiguous before actual Write now sets a denial-only unresolved marker and cannot fall through to payload IDs or invented UUID scratch roots; registration validates command/sync/timeout and event matcher semantics, including disabled hooks. Actual dispatched Write regression denies stale-owner and newly ambiguous UUID scratch access. Reader diagnostics remain available without granting task authority.

Subprocess dispatch has deadlines, process-group cleanup and bounded per-child output; retained output is additionally capped across the whole invocation before appending each result. Aggregate SDK decisions fail closed on child failures/conflicts; audit failure grants no authority and audit excludes prompt/input/output contents.

Limit: source/fixture review does not establish installed Craft callback delivery or Pi/Codex hook parity. Live canary and exact-main deployment remain parent integration work. Review of scanner dispositions and final aggregate generated artifacts is separate.
