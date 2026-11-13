---
ticket_refs:
  - siege-analytics/claude-configs-public#1171: comment pending (PR link after the PR opens)
---
# Self-review: #1171 execution forms pinned under the scoped mutation gate

Ticket: siege-analytics/claude-configs-public#1171 (Refs, not Closes)
Review tier: B (tests only: `hooks/_test/execution_risk.py`, no runtime file changes)
Base: develop 77d83c20

## Assumptions

- Goal source: the #1171 issue body and its comments of 2026-11-11 and 2026-11-13, plus the hub's assignment to assess the reported forms against develop source and pin or repair them.
- Develop's `hooks/bash/universal-mutation-gate.sh` (lines 95-158) doesn't read the resolver's computed `tier`. Commit 7202fb69 removed the tier-based companion checks, and it's an ancestor of 77d83c20. `origin/main` 7f5e5b19 (the installed generation) still enforces them at lines 112-380.
- No other non-test develop code reads `resolve-think-gate.py:1006` `result["tier"]` (checked with `git grep` over the tree, excluding tests).
- So the reported refusal is fixed in source by 7202fb69. This change only pins it. The computed tier for absolute-interpreter/flagged pytest and `gh issue close` is still whole-tree C; that's a known residual and is unchanged here.
- Form 4 (`python -c` import) is refused by the deliberate opaque-inline rule (`task_actions.py:2241`), not by tier. Form 6 (`gh -R owner/repo` read as a cwd path) is tracked separately in #1347.

## Peer review

- Scope: one test file with 50 added lines. No runtime, policy, generated or settings file changes.
- Positive test: the fixture task has no junior/senior or artifacts-posted companion (asserted first). Each reported form runs through the real source gate and must exit 0.
- Negatives: the same commands and cwds under `designing`, under a scope that doesn't own the toplevel, and with only another session's fully-companioned Task. Each must exit 2 with its specific reason, so a refusal for an unrelated reason can't satisfy them.
- The tests assert gate outcomes, not tier values, so a later narrowing of `_pytest_execution_targets` doesn't have to edit them.
- `os.path.realpath(sys.executable)` gives an absolute `python3.N` path on both macOS and Linux runners. The hook never executes it.

## Lead review

- Lifecycle, ownership and the inline-execution boundary are unchanged and covered by the negatives above.
- The PR makes no claim about installed-runtime behavior. #1171 stays open until a release containing 7202fb69 is installed and the original forms are re-run there.

## Test plan

- `hooks/_test/test_execution_risk.test.sh` on this branch: 17 tests OK.
- Red check: inside an `origin/main` archive with this test file copied in, `test_reported_1171_forms_need_only_owned_implementing_task` fails 5/5 subtests with "artifacts missing or wrong ticket" (the #1171 refusal). The lifecycle/scope and foreign-session negatives pass there too.
- Applicable suites (clean environment, no host session variables): task_keyed_gates, universal_mutation_gate (+ safelist, fail_closed, 831, empty_reporoot, ssh), worktree_materialization_risk, git_add_risk, env_project_execution, quoted_mutation_operands, explicit_target_operands, lean_task_pipeline, settings_drift, plus the build, skill-inventory, sync-skill-references, generated-source-authority and validate-hooks checks. Results are in the PR body.
- Local runs started from the author's private scratch directory, because the installed v3.5.92 floors toplevel Python execution to Tier C (#1171 itself). Hosted CI is the authority.

## Quantified claims

- 1 file changed, 50 insertions; 4 new test methods plus 1 helper.
- 5 reported forms pinned as allowed; 15 refusal subtests (3 conditions × 5 forms); 1 opaque-execution assertion.
