# Deployment provenance and ownership independent review

Review-only current working diff in /private/tmp/claude-config-deployment-repair, 2026-10-29. No source, live runtime or global/user config changes by reviewer. Temporary local fixtures only.

## Must-fix findings

1. Mutable source reader controls immutable-source certification. `_deploy_source_files` imports working sibling source_snapshot.py and trusts its git_files output before tracked cleanliness is established. Reproduced isolated local Git/origin main with unchanged build.py, dirty source_snapshot.git_files returning current worktree bytes, and dirty README: validate_deploy_source returns accepted main SHA instead of rejecting. Read bootstrap helper bytes from accepted Git objects (or use a fixed object reader), preventing replacement-ref substitution too. Author is implementing correction and regression.

2. Managed hardlinks can mutate outside target. `_validate_deploy_paths` only rejects symlinks. Temp fixture workspace/.claude/settings.json hardlinked to outside operator-settings.json (nlink2) passes preflight. Subsequent in-place write_text/copy2 on settings, root KERNEL/RESOLVER/bundle, bin/catalog files can overwrite an outside alias before final verification. Reject multiply linked regular managed paths or atomically replace; add regression. No real user config was touched.

## Positive checks

Source/target overlap and explicit output overlap preflight now happen before activation; --deploy plus --dist rejects. Exact-object private generation and artifact-only verification/stamp stages distinguish copied bytes from actual host invocation. Native hook cleanup uses actual resolved installation ownership rather than familiar filenames. Duplicate registration detection preserves triple identity and checks multiplicity.

Independent settings-drift suite passed all fixtures. Independent native_push_test.py:20 passed in47.569s. Full deployment/provenance tests and exact-head re-review remain pending author corrections. Aggregate source registration snapshot changes must deliberately account for removed duplicate registrations and dispatch PostToolUseFailure additions.

## Corrected working source: approved

Original blockers are resolved: the snapshot reader is bootstrapped from literal accepted Git bytes; policy/snapshot reads disable replacement objects and ambient Git root/index/object routing. Managed-path preflight now uses lstat, rejects aliases/hardlinks, non-directory parents and special/non-regular leaves before writes. Output/source/target overlap is checked before mutation. Independent full deploy_source_policy_test passed after immutable-reader/replacement/routing/hardlink corrections, exercising actual immutable build/activation and stamp invalidation on source/copy corruption. After the final leaf-type amendment, independently verified FIFO RESOLVER and settings leaves plus file-as-parent fail immediately without opening them. No remaining must-fix findings in this working diff. Author's final full rerun and exact commit remain separate receipts.

Persisted-state lens: per skills/shelves/systems-architecture/data-intensive/SKILL.md's data-outlives-code principle, accepted Git objects are the system of record; workspace artifacts and deploy-stamp are derived. The stamp reports artifact-byte verification and is invalidated before mixed-generation writes; it must not be read as host invocation evidence. Host registration/UAT, managed backup/rollback and preservation of concurrently edited user-global configuration remain coordinator acceptance requirements. No actual global/user settings were modified by this review.
