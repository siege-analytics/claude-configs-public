# Paused Task selection repair

Refs #1343. Fresh canonical branch helper selected origin/develop b8786c897bb92e37472aec43c813d537defd749d. This feature is separate from PR #1342 and does not hold that publication.

## Assumptions

Read issue #1343, resolve-think-gate.py enumeration/selection/mutation checks, and think/task-evidence.md schema and lifecycle. Paused work remains unfinished. The old inactive filter excluded only terminal states, so a parked Task still competed with the active Task in the same scope. Named pause states should be removed from active selection after canonical denial records are remembered. Unknown states must retain their fail-closed behavior rather than vanish through a new active-state allowlist.

## Test plan

Added a real universal-mutation-gate two-Task regression with parked, paused and on-hold cases, stale legacy copy, active Bash/native Write selection and explicit rebinding, denied paused bindings, no-active denial, resume of the same original gate, foreign-target denial and retained evidence/identity. It failed in all three pause cases before the source fix; unknown-status control passed (two tests, 1.700s). Initial green: two tests, 4.474s. Stronger final run: six focused tests passed in 17.508s, also covering terminal retirement/no resurrection, genuine legacy-only behavior, own lifecycle and missing-artifact/terminal denial. Python compilation and diff whitespace check passed. Canonical build passed (199 headers); inventory, generated-source authority, language and data freshness checks passed. System Python lacked PyYAML, so the existing Python 3.11 environment ran the generators without dependency installation. No full-suite, hosted CI or installed-runtime claim.

## Findings

Add only parked, paused and on-hold to the existing inactive set. Keep terminal values, all canonical claim writes and selection/mutation checks unchanged. Document the accepted vocabulary adjacent to the existing schema; paused work must resume in place rather than be marked completed or disposed. A typo remains non-authorizing and cannot silently remove an ambiguous candidate. No broader command grammar, scope or lifecycle deletion grant is added.

## Independent review

Root read the complete source/test/documentation diff and accepted the exclusion after claims and real UMG selection/denial/resumption controls. Root requested a documentation correction so reviewing/verifying describe supported scoped review and verification routes without implying they grant general implementation. That wording correction is included; no parser or authority behavior changed. Root's planned independent two-test rerun is not claimed as executed here.

Complete staged scan: exit 1, 62 findings, raw SHA256 c15a835d762459b063eec8ce1d592da785204d850b4f655a135649de27a65fd7. Author per-finding rebind is retained at instruction-refactor-evidence-20261104/core1343-parked-task-selection-20261113/staged-author-per-finding-rebind.json. All 62 rows bind actual handlers across 26 functions to prior #1342 dispositions. Every handler AST is unchanged from the selected develop base; only _session_thinks changes its final inactive set. Existing false-positive and inherited coverage-debt classes remain, including #1329. This is non-clean evidence, not a coverage or scanner-pass claim. Generated metadata changes only the five Think support-tree hashes.
