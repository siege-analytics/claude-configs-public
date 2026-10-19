---
ticket_refs:
  - siege-analytics/claude-configs-public#1057: universal-mutation-gate blocks read-only commands
---

# Self-review: #1057 positive read allowlist in universal-mutation-gate

## Assumptions

Pre-author-inventory: a mock local Craft workspace (`~/.craft-agent/workspaces/my-workspace`) was installed from `main` v3.5.68 with `bin/sync-workspace-hooks.sh`. With no task gate, it blocked `sed -n 1,5p`, `for` loops and `python3 -c "print(1)"`, which is #1057's symptom.
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1057
Pre-mortem-artifact: plans/pre-mortem-1057-read-allowlist.md
Hostile-review-artifact: https://github.com/electinfo/electinfo_claude_skills/pull/349
Project-contribution: proven reads stop costing a turn in every consumer workspace without a task gate. Writes the indicator list used to miss are now gated.

- The classifier is a byte-identical copy of the electinfo version, with this repo's stricter policy applied to both: no curl, awk or multi-line commands; `sed` and `jq` tightened.
- macOS: the classifier needs python3 ≥ 3.6, and the installer already requires ≥ 3.9. The bash changes are 3.2-compatible.

## Peer review

- **writing-code:** the change only adds an allow path for proven reads and only adds mutation indicators. Unrecognised commands reach the existing gate unchanged.
- **writing-tests:**
  - The new `hooks/_test/read_allowlist.test.sh` fails 10 cases against `develop`'s gate (the read cases) and passes 106/106 here.
  - Its must-block list is every reproducer from three hostile-review rounds.
- **Gate evidence:**
  - `read_allowlist`: 106/106.
  - `universal_mutation_gate`: 29/29.
  - `universal_mutation_gate_safelist`: 60/60.
  - `831`: PASS.
  - `empty_reporoot`: PASS.
  - `build.py` and `--check`, `generated-source-authority --check` and its test, `settings_drift_test`, `review_risk_test`: all pass.
  - The new library ships in all four dist layouts.

## Lead review

- **Solves #1057:** yes, for proven reads with no gate.
- **Out of scope:**
  - #1051/#1055's task-keyed redesign.
  - The designing state still admits any non-indicator command, unchanged from #574.

## Quantified claims

- `read_allowlist` must-block cases: about 90 (every reviewer reproducer).
- Against `develop`: 10 failures.
- Upstream suites: 29 + 60 tests, plus 2 PASS suites.
