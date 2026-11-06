# Preserve ordinary scoped merges

## Assumptions

Goal source: the operator's per-task authorization requirement, #1207's additive queue exemption and the independently reproduced ordinary-merge regression. Roles: release maintainer, implementer and source reviewer.

Pre-author-inventory: at9a03ca8, an external real-hook fixture proves that a valid existing task authorizes a pinned Core merge under pre-queue3956000 but the new helper denies it because Core does not require a queue. Pinned auto-merge also regresses while an unpinned merge still passes. No real remote mutation was executed. Both main and1209 auto-merge are disabled; existing CI continues.

Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1207
Pre-mortem-artifact: plans/pinned-merge-scope-preservation-1207.md#test-plan
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/pull/1209
Project-contribution: make the queue exemption additive without removing existing task authority or publication checks.

## Design

Only a proven required-queue CLI request or exact intrinsic GraphQL enqueue receives the no-task queue exemption. A confirmed nonqueue target and ordinary nonexempt merge options return to the existing task/ownership path. Their local publication guards must still run. Admin bypass and malformed head pins do not gain permission. Nonexempt does not mean universally forbidden: existing scoped authority remains authoritative.

Keep the pure grammar classifier separate from a new bounded queue-required predicate. The latter proves CLI queue requirements before any of the eight local guards skip; exact GraphQL enqueue is intrinsically queue-only. Pass the actual payload cwd, not the hook process cwd. The resolver alone records queue admission audits. No agent-writable permission cache, environment grant, role registry or task-first shortcut is introduced. A broad task must not make a real queue operation inspect an unrelated local HEAD.

Reuse the fixed bounded reads. The current router budget is90seconds; six registered guards plus the resolver have at most21seconds of proof execution at three seconds each, before cleanup and other hooks. Eight potential guard callers plus the resolver have at most27seconds. This adds network work and is not claimed to be free or atomic with execution.

## Test plan

Reproduce pinned normal merges, including auto and other legitimate nonexempt options: no task denies, valid task follows ordinary authority, and local review/test checks still run. Required-queue CLI and exact GraphQL enqueue retain no-task behavior and skip unrelated local evidence, including when a broad task exists. Deny malformed pins, admin, arbitrary GraphQL and composed mutation smuggling. Assert bounded read shapes/counts, cwd routing and exactly one resolver audit per admitted queue operation. Run genuine source-bound focused checks, canonical refresh, independent review and protected exact-head CI.

## Peer review

Two independent assessments rejected task-first selection and unauthenticated decision caches. Both require fresh queue proof before skipping local guards. Exact-source review follows implementation.

## Lead review

Keep all existing ordinary publication guards and role policy. Preserve holds/settings and normal develop/main delivery; no candidate install or bypass. The earlier14queue/7disclosure results and51-row scan describe9a03 only.

## Quantified claims

The external comparison observes pre-queue scope allow and current scope deny for both pinned Core forms. Current changed-source tests and scanner results remain pending.
