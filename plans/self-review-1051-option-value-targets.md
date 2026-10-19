---
ticket_refs:
  - siege-analytics/claude-configs-public#1051: option values redirecting mutation targets
---

# Self-review: #1051 option values cannot redirect mutation targets

## Assumptions

Pre-author-inventory: the blocker was reproduced through the real hooks at `2bc6e62` before authoring. `cp notes.md <repoB>/f.txt -S .bak`, run from the session's own `plans/`, was allowed with no gate, with an unrelated designing gate, and with task A implementing. Base `4d6fbd2` blocked it in all three states. See the review comment linked below.
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/pull/1055#issuecomment-6272431836
Pre-mortem-artifact: plans/pre-mortem-1051-option-value-targets.md
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/pull/1055#issuecomment-6272431836
Project-contribution: a mutation's target can no longer be hidden or redirected by an option value, so it is checked against the gate of the task that owns it.

- GNU `cp`, `mv` and `chown`/`chmod` permute options, so value-taking options can follow operands.

## Peer review

- **writing-code:**
  - every change adds targets or fails closed, and nothing removes a target;
  - `--` ends option parsing;
  - `-` is an operand.
- **writing-tests:** the new test was run against the unfixed parser and fails 6 assertions there, so it discriminates. It passes with the fix.
- **Gate evidence:**
  - `task_keyed_gates.py`: 43 tests OK.
  - `universal_mutation_gate`: 29/29.
  - `universal_mutation_gate_safelist`: 60/60.
  - `universal_mutation_gate_831`: PASS.
  - `universal_mutation_gate_empty_reporoot`: PASS.

## Lead review

- **Solves the blocker:** yes, for the reproduced shapes:
  - a trailing or clustered `-S`, and `--suffix`;
  - `chmod`/`chown --reference`, with `=` and as a separate token;
  - `cp`/`mv -t`;
  - attached option paths (`sort -o/x`, `--output=/x`);
  - `--`.
- **Not addressed here:** the major finding on the same review, the designing-state read-only regression. That is a classifier design question for #1055's owner.

## Quantified claims

- **New test:** 12 cross-task command shapes are blocked, and the own-session `plans/` shape is blocked. 4 in-scope forms pass.
- **Against the unfixed parser:** 6 failures (verified by stashing the change).
- **Suites:** 43 + 29 + 60 tests pass, plus 2 PASS suites.
