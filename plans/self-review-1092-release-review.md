---
ticket_refs:
  - siege-analytics/claude-configs-public#1051: gates must be task-keyed
  - siege-analytics/claude-configs-public#1086: scale pre-mutation artifacts to the change's review tier
---

# Self-review: CodeRabbit findings on the v3.5.73 release PR (#1092)

## Assumptions

Pre-author-inventory: each of the six findings was reproduced on develop d6354e6. The three new task_keyed_gates tests and the two `ss -D` read_allowlist cases fail on develop and pass here.
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/pull/1092
Pre-mortem-artifact: plans/pre-mortem-1051-slim.md
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/pull/1092
Project-contribution: terminal pushes work again; conventional commits keep their proportional tier; `ss -D` stops writing files without a gate.

- The native pre-push fallback restores pre-#1051 behaviour only when no session identity exists.

## Peer review

- **writing-code:**
  - `ss_kills` adds `-D`/`--diag`.
  - `find_gate_for_repo` selects by repository for proven reads, and gives `test-gate` the root fallback when there is no session.
  - `_lone_git_commit` uses `shell_tokens`, so quoted text is not an operator.
  - A lone commit ignores message operands, but only when the repository is a target.
  - The docs state that the hub cap is enforced at spawn, and the test-gate example gains `sessionId` and `repo_root`.
- **writing-tests:**
  - New: lone commit with a conventional message (docs-only A, hook staged C); native pre-push root test-gate; proven read selects by repository; `ss -D`/`--diag`.
  - All of them fail on develop.
- **Gate evidence:**
  - hook suites 39/39 after `bin/build.py`;
  - task_keyed_gates OK;
  - read_allowlist 248/248;
  - review_risk_test PASS;
  - generated catalogs current.

## Lead review

- **Resolves all six #1092 threads:** yes. For the hub cap, the doc now states that spawn is enforced and adoption is self-counted, because there is no adoption tool entrypoint to hook.

## Quantified claims

- New discriminating tests: 3 gate tests and 2 classifier cases.
