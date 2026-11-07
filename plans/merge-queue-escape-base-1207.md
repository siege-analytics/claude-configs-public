---
propagation-deferred: commission forbids issue writes; the PR body reproduces this artifact and the hub relays it to Root
---

# Pinned merge queue: escapes, exempt bases and proof failures (#1207)

## Assumptions

Domain(s): software engineering
Geospatial cross-cut: no
Goal source: siege-analytics/claude-configs-public#1207 corrections authorized by the operator on 2026-11-07 ("Please feel free to make meritorious corrections"), scoped by the Siege Claude Hub commission. The scope is the hostile review of #1207 at 7b6f424 plus main 9f47b035: blocker B1, the exempt-base operator decision, non-blocking follow-up 1, and docs/CHANGELOG corrections.
Goal source verification: `scripts/discipline/evaluate-ticket.sh siege-analytics/claude-configs-public#1207` returns BLOCK (missing Context/Goal, evidence token, design reference, Assumptions). The commission prohibits editing the #1207 body, so the exemption below applies.
Plan reference: plans/merge-queue-escape-base-1207.md#design
Pre-author-inventory: plans/merge-queue-escape-base-1207.md#pre-author-inventory
Investigate-artifact: plans/merge-queue-escape-base-1207.md#investigation
Pre-mortem-artifact: plans/merge-queue-escape-base-1207.md#pre-mortem
Hostile-review-artifact: input review is the Claude Opus 5.5 hostile review of #1207 at 7b6f424 plus main 9f47b035, relayed by the hub. A cross-family hostile review of this exact pushed head is commissioned by the hub after the PR opens.
Project-contribution: the queue lane's audit names the PR that is actually enqueued; no-task admission is bounded to an explicit, single-sourced base policy; and an unreadable proof no longer removes existing task authority.

## Exemption: Goal source verification

Reason: #1207's body predates the evaluate-ticket rubric. This worker's commission forbids editing it, so the structural BLOCK cannot be cleared from this task.
Evidence: `./scripts/discipline/evaluate-ticket.sh siege-analytics/claude-configs-public#1207` printed "BLOCK: ... missing sections: Context,Goal". The scope, acceptance tests and revert proofs come from the commission and the hostile review, and are reproduced in this file and in the PR body.
Falsification: this exemption is wrong if the commission authorized editing #1207's body, or if any item implemented here is not in the commissioned scope list.

## Pre-author-inventory

Verified against origin/develop 6cae44ad3c09c3cf6fb980428bbc5ca5ee330c31:

- `hooks/lib/github-merge-queue.py` `parse()` rejects NUL/LF/CR only. `hooks/lib/task_actions.py` `shell_tokens` drops a backslash inside double quotes, where the shell keeps it.
- `verify()` never compared the destination base to a policy. The GraphQL form performed no read, and audited null repository/number/base.
- Any proof read failure raised, and the resolver denied with `Queue enqueue denied:` even under a task gate. That message also covered a non-queue `--admin` merge.
- Eight publication guards call `--queue-required COMMAND CWD`, which runs `parse` plus `verify`.

## Investigation

- `craft-settings-router.py` `RoutingError` subclasses `ValueError`. Runner timeout (`HookTimeout`) and the output bound raise it.
- The ordinary path denies any `gh api` mutation ("GraphQL is not modeled", `task_actions.py` `github_project_action`). A non-exempt GraphQL request therefore stays denied.
- `Queue enqueue denied` is asserted by `hooks/_test/github_merge_queue.py` and by `hooks/_test/github_project_scope.py`, the latter for GraphQL commands only. The new form-specific label keeps the GraphQL wording.
- A live read-only `gh api graphql` probe of the node shape was blocked by the mutation gate. The `PullRequest` fields `id number baseRefName headRefOid repository{nameWithOwner}` are therefore inference from the public schema. A wrong shape fails closed.

## Design

1. `parse()`: `require('\\' not in command, 'backslash escapes unsupported')` directly after the single-line check. Ordinary CLI merges return before it. `shell_tokens` is unchanged, because PR #1170 owns `task_actions.py`.
2. `QUEUE_EXEMPT_BASES = ('develop',)` lives in the helper. It is the single source of the policy, and `docs/pinned-merge-queue.md` names it.
   - CLI form: a non-listed base returns `None` before the rules read, so the ordinary task path applies.
   - GraphQL form: one fixed read-only `node(id:)` lookup under the same three-second deadline and 64 KiB bound. The returned node id and head must equal the request. The repository and number must be well formed.
     - A non-listed base returns `None`; the ordinary path denies it.
     - A failed or malformed read denies.
     - The audit records the real repository, number and base.
3. `ProofUnavailable(ValueError)` covers the proof failing to run or answer: non-zero exit, oversize, deadline, runner timeout, undecodable JSON, or ambient `GH_HOST`. Readable mismatches stay plain `ValueError`.
   - For the CLI form, `verify()` returns `None`. A canonical task-scoped pinned merge keeps its task path. Guards get exit 1 and run every local check.
   - For GraphQL it propagates and denies.
4. The resolver denial label is form-specific: `Queue enqueue denied:` for `gh api`, `Pinned merge denied:` for `gh pr merge`.

## Pre-mortem

Task-ID: merge-queue-escape-base-1207 (siege-analytics/claude-configs-public#1207)

- Tiger 1, Severity: high. The read-failure fallback could widen admission.
  - Mitigation: `None` reaches the ordinary path, which needs an owning task.
  - Tests: no-task failure modes deny; owned failure modes allow without an audit; the guard predicate exits 1.
- Tiger 2, Severity: high. The GraphQL lookup could trust a different node or head. Mitigation: id and head equality; the `othernode` and `stale` fixtures deny.
- Tiger 3, Severity: medium. Base variants could bypass the policy. Mitigation: exact tuple membership on the server-reported `baseRefName`.
- Elephant 1, Severity: low. GraphQL now adds one read per consulting hook. Accepted.
- Elephant 2, Severity: medium. The live GraphQL shape is unverified. If it is wrong, the request fails closed.
- Paper Tiger 1, Severity: low. The double-quoted `\$id` form is now rejected. The documented form is single-quoted.

Implementation may proceed: yes.

## Test plan

`hooks/_test/github_merge_queue.py` runs real UMG and guard executions with a fake `gh` transport; no remote mutation runs. New or changed tests:

| Item | Test |
|---|---|
| 1 | `test_shell_escapes_cannot_change_validated_literal_bytes` (double-quoted and mixed-quote forms deny, no audit) |
| 2 | `test_only_policy_bases_are_exempt` (policy constant; main base: no-task CLI and GraphQL deny with no rules read; task CLI allowed without exemption; guard predicate exits 1; GraphQL still denied) |
| 2 | `test_graphql_lookup_failure_or_mismatch_is_not_exempt` (fail, bad, huge, hang, stale and othernode deny, even with a task) |
| 2 | `test_exact_graphql_variables_and_literal_use_one_node_lookup` (exactly one node read each; audit carries repository, number, base and form) |
| 3 | `test_cli_proof_read_failure_keeps_task_scope_without_exemption` (no task: deny; owned: allow, no audit; predicate exits 1; `GH_HOST` CLI keeps task, GraphQL denies; stale head still denies with `Pinned merge denied:`) |
| 3 | `test_unreadable_proof_is_typed_and_only_cli_falls_back` (in-process: `ProofUnavailable` raised, CLI `verify` returns `None`, GraphQL raises `ValueError`; a stale head is not `ProofUnavailable`) |
| 4 | `unavailable_helper_controls` asserts the form-specific labels |

Updated read-count tests: `test_repository_environment_routes_cli_without_a_local_repository` and `test_entire_local_publication_stack_ignores_unrelated_head_once`. The latter now asserts per-hook fresh read counts instead of a total.

Revert proofs were run on the working tree, restoring each line afterwards:
- R1: the backslash reject removed. The escape fixture fails, with both forms admitted and an audit row written.
- R2a: the CLI base check removed. The main-base fixture fails, because no-task CLI is admitted.
- R2b: the GraphQL base check removed. The main-base fixture fails, because no-task GraphQL is admitted.
- R2c: the GraphQL lookup replaced by the old no-read return. The lookup-failure, one-lookup/audit and main-base fixtures fail.
- R3: the CLI `None` fallback removed. The read-failure fixture fails, because every owned mode is denied.

## Peer review

- Syntax: `ast.parse` passes on the three changed Python files.
- Scope: `git diff --stat origin/develop` touches only the helper, its resolver call site (two lines), its test, its doc, CHANGELOG and this artifact. `hooks/lib/task_actions.py` is untouched.
- Scanner: `skills/detect-ai-fingerprints/scan.sh --working` reports no finding on changed lines. Remaining findings are pre-existing whole-file handler findings at unchanged lines.

## Lead review

- The class is closed for the queue lane. Inside double quotes the shells give special meaning to `\`, `$` and backquote. The input review confirmed that `$` and backquote were already rejected, and `\` is now rejected, so an admitted command contains no shell escape.
- The shared lexer class remains open outside the queue lane, and is deferred to PR #1170's owner.
- The exempt-base policy fails closed in both forms. `None` never reaches the audit.
- Blast radius: the helper's nine runtime callers (resolver plus eight guards) see narrower admission and one extra GraphQL read.

## Findings

| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| L1 | P3 | GraphQL form does not read branch rules; it relies on the server to reject a non-queue base | noted; deferred to hub |
| L2 | P3 | Live GraphQL node shape unverified (gate blocks read-only probe) | noted; fails closed |

## Canary and rollback

- Canary: not run. This worker is prohibited from installs and deploys, and no installed runtime was changed. The real-hook fixture suite, run against a copied `hooks/` tree, is the pre-integration substitute. Root owns integration, promotion and any installed canary.
- Rollback: revert this commit. The change is source-only; its only persistent effect is audit rows that now carry real repository, number and base for GraphQL. Reverting restores the reviewed 9f47b035 behavior, including blocker B1.

## Quantified claims

- "one fixed read-only node(id:) lookup": `test_exact_graphql_variables_and_literal_use_one_node_lookup` asserts exactly one `graphql` read per admitted command.
- "eight publication guards": `git grep -l -- '--queue-required' hooks/git hooks/bash` lists 8 files.
- Suite counts and hosted CI results are recorded in the PR body from the exact runs.

## Rework ledger

| Rework trigger | Root skip | Check cost | Rework cost | Ratio |
|---|---|---|---|---|
| Stack test expected 27 GraphQL-inclusive reads, observed 22 | Assumed every guard consults the helper for `gh api` | 1 grep | 1 test edit | 1:1 |
