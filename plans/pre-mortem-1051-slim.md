---
ticket_refs:
  - siege-analytics/claude-configs-public#1051: gates must be task-keyed
  - siege-analytics/claude-configs-public#1086: scale pre-mutation artifacts to the change's review tier
---

## Pre-Mortem
Task: land #1055's task-keyed gates on current develop, with one read classifier and tiered pre-mutation artifacts.
Ticket: siege-analytics/claude-configs-public#1051

### Tigers

#### Tiger 1: A Tier C change is evaluated at a lower tier (Severity: high)

Mitigation:
- The floor comes from `bin/review-risk.py` `classify()`, the same classifier the commit hooks use.
- A declared tier only raises the floor.
- A directory or repository-wide target is classified by the tracked files under it plus a probe path. A lone `git commit` is classified by the staged and modified files.
- A missing classifier, policy, `repo_root` or git listing, or a target outside `repo_root`, fails closed to C.
- An independent review found that bare directory and toplevel targets fell to B. This is fixed and pinned (`test_tree_wide_targets_are_classified_by_their_contents`).

#### Tiger 2: Delegating read proof admits a write (Severity: high)

Mitigation:
- Only exit 0 from the released classifier short-circuits, and exit 3 forces not-read-only.
- The independent review found the classifier proving `kubectl -n get delete`, `ss -K` and `gh --web`. These are fixed upstream in #1089/#1090, and that classifier is carried here.
- #1055's adversarial suite (`task_keyed_gates.py`) runs against the delegated gate.

#### Tiger 3: Over-blocking ordinary work (Severity: medium)

Mitigation:
- Tier A needs only the implementing gate, and B needs an investigation and a pre-mortem.
- Reads pass in every gate state, and a session's own `data/` is scratch.
- The designing state keeps #1055's reviewed policy: no arbitrary scripts, approved diagnostics only. A scoped-execution allowance was tried, contradicted the reviewed fixtures, and was reverted.

### Launch-Blocking Assessment

None identified, provided the suites stay green at the head.
