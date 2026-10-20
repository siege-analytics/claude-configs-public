---
ticket_refs:
  - siege-analytics/claude-configs-public#1051: gates must be task-keyed
  - siege-analytics/claude-configs-public#1086: scale pre-mutation artifacts to the change's review tier
---

# Self-review: slim #1051 on current develop

## Assumptions

Pre-author-inventory:
- On v3.5.70, a `complete` or `done-awaiting-pr` gate with an investigate artifact let every mutation through. An operator's Mac session reproduced this with `touch`.
- The operator's Mac logged 936 gate blocks. 404 of them were workflow blocks demanding the full Tier C pipeline before any edit.
- #1055 at 2bc6e62 conflicted with develop and carried a second read classifier that blocked 917 designing-state reads.

Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1086
Pre-mortem-artifact: plans/pre-mortem-1051-slim.md
Hostile-review-artifact: plans/hostile-review-1051-slim.md
Project-contribution: each task gets its own gate, sized to its risk. Terminal gates stop authorizing, and reads pass in every state.

- Design: plans/1051-slim-design.md.
- #1055's lifecycle, hub-cap fix (B2) and canonical claims are kept unchanged. #1069's target-parsing fix is included.

## Peer review

- **writing-code:**
  - `task_actions.action()` delegates read proof to `read-only-command.py` (0 means read; 3 forces not-read).
  - `resolve-think-gate.task_tier()` computes the floor.
  - The gate requires only the effective tier's artifacts and names the tier and its reason in the block message.
- **writing-tests:**
  - `task_keyed_gates.py` passes, including new tier, declared-tier and tree-wide tests.
  - #1055's glob fixtures are realigned with the released policy. Readers whose options cannot write stay reads, and injection-capable verbs stay denied with the option-injection sentinels present.
- **Gate evidence:**
  - hook suites 39/39 after `bin/build.py`;
  - review_risk_test PASS;
  - metrics, inventory and generated-source-authority current.

## Lead review

- **Solves #1051 and #1086:** yes for the gate.
- **Replay of 2,845 commands, develop vs this branch:**
  - No gate: 157 newly allowed, mostly `cd`/`which`/`git` reads now proven per line. 11 newly blocked, all commands truncated at 200 characters.
  - Designing gate for an unrelated task: 1,258 newly blocked, 256 of them complete commands. These are scripts and programs (`node`, `python3 x.py`, `curl`, `bash x.sh`, `env | grep`) that the legacy designing state let through under #574. #1055's reviewed policy blocks them, and this branch keeps that. With tiers, implementing an ordinary-code task now needs only an investigation and a pre-mortem.
- **Out of scope:**
  - R1, R2 and R4–R7 from the 936978a review;
  - retiring `task_actions.reader`;
  - electinfo override retirement (#348).

## Quantified claims

- Replay: 157 / 11 (no gate); 1,258 newly blocked (designing), 256 complete.
- Hook suites: 39/39.
