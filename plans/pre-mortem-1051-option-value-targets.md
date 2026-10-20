---
ticket_refs:
  - siege-analytics/claude-configs-public#1051: option values redirecting mutation targets
---

## Pre-Mortem
Task: in the file-mutation branch of `hooks/lib/task_actions.py`, parse value-taking options so they cannot redirect or hide targets.
Ticket: siege-analytics/claude-configs-public#1051 (review of PR #1055 at `2bc6e62`)

### Tigers

#### Tiger 1: Legitimate commands newly over-blocked

Some shapes become stricter:
- extra targets taken from paths attached to options, such as `-o/abs`;
- `mv -t` now fails closed, as `cp -t` already did.

Mitigation:
- The changes only add targets or refuse ambiguous shapes; nothing is removed from what is checked.
- The full `task_keyed_gates` suite (43 tests) and all four `universal_mutation_gate` suites pass unchanged.
- In-scope forms are asserted to pass: `cp src dst -S .bak`, `chmod --reference=src dst`, `chmod 644 dst`, and copy sources outside the task's scope (sources are reads).

#### Tiger 2: A value option missed in the table

Mitigation:
- A missed option can only make an operand look like a target. For `cp`, the destination is still the final operand. For `chmod`/`chown`, an extra operand only adds a path to check.
- Short clusters that end in `S` (`cp`, `mv`) are handled.
- Any `t` in a short cluster fails closed.

### Launch-Blocking Assessment

None identified, provided the suites stay green at the head.
