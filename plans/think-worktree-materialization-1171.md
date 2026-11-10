---
ticket_refs:
  - siege-analytics/claude-configs-public#1171
---

# Owned worktree materialization risk

Goal source: issue1171 comment6761077615 and the explicit source-only repair assignment.

## Investigation

Current task_tier expands repository/directory targets through tracked ls-files,
so unchanged workflow/release files floor a worktree-creation operation at C.
It also floors any sibling destination at C solely for being outside repo_root,
even after ordinary own-Task scope selection has proven that assigned destination.
The existing bounded pytest risk view already uses actual branch/working changes;
PR1177 is closed unmerged, but that helper exists in the current canonical source.

## Proposed bounded repair

Recognize a sole literal supported git worktree add operation for risk assessment
only. Keep it a mutation with at least B, normal own-Task scope/lifecycle checks
and the independent K5 develop source guard. Use actual source branch changes
against known develop plus staged, modified and untracked changes. Preserve risky
destination prefixes. Unsupported syntax or unavailable Git evidence retains C.
Do not certify network clone sources, force/reset operations, shell wrappers or
mixed commands. Do not alter the branch guard, runtime identity or authorization.

## Pre-mortem and controls

- Risk: a checkout exemption hides actual workflow changes. Exercise committed,
  staged, modified and untracked risky changes; all must retain C.
- Risk: a sibling-path allowance expands authority. Exercise missing destination
  scope, foreign Task/session, lifecycle and a declared C; preserve denial.
- Risk: a tier repair becomes branch-source permission. Verify develop positive
  and main/implicit-main negative through the actual branch guard separately.
- Risk: unavailable Git state is mistaken for an empty diff. Inject listing,
  revision and baseline failures and require C.
- Risk: the operation overwrites work or uses an unsupported route. Decline
  forced/reset/opaque/mixed forms and verify active worktree state preservation.

## Validation and delivery

Add a red-first actual UMG fixture using real disposable repositories containing
unchanged tracked workflows/release files. After the repair execute the allowed
worktree creation and verify its materialized files and unchanged source work.
Run affected existing tier/execution/scope suites, canonical generation/freshness,
genuine content-bound tests and invocation-only native commit hooks. Retain this
pre-work plan and report exact results, including limitations. No push, protected
merge, installation or client mutation is authorized in this task.
