---
ticket_refs:
  - siege-analytics/claude-configs-public#1051: gates must be task-keyed
  - siege-analytics/claude-configs-public#1055: task-keyed gates PR (this branch's base)
  - siege-analytics/claude-configs-public#1069: option values cannot redirect mutation targets
  - siege-analytics/claude-configs-public#846: one read classifier
---

# Design: land #1051 as a slim #1055 on current develop

## Problem (evidence)

1. **Gates are session-wide, not task-keyed (#1051).** One task's think/mutation gate blocks every other task in the session. That is the operator's original complaint.
2. **Terminal gates keep blanket write rights on released main (v3.5.70).** In `hooks/bash/universal-mutation-gate.sh` lines 511–524, a `complete`/`disposed`/`done-awaiting-pr` gate with an investigate artifact exits 0 for every command. A Mac install session reproduced it: a finished install gate let `touch` through until the gate was set back to `designing`.
3. **#1055 fixes both, but is stuck.** It has 51 files and four review rounds. Its last review (2bc6e62) left:
   - a blocker: the `cp … -S .bak` cross-task write, fixed in stacked #1069;
   - a major: 917 designing-state reads that base allowed are now blocked. Cause: #1055 carries its own read classifier (`task_actions.reader`), which differs from the one released in v3.5.69.
4. **It conflicts with develop** in four files: the gate, `review_risk_test.py`, and two catalog files.

## What done looks like

- A mutation is authorized only by an `implementing` gate, with complete artifacts, whose scope owns the mutation's target. A gate never blocks another task's reads or mutations.
- Terminal gates of any spelling authorize nothing. Own-session cleanup still works.
- Read proof comes from `hooks/lib/read-only-command.py`:
  - exit 0: read-only in every gate state;
  - exit 3: a veto, never a read;
  - exits 1 and 4: fall through to #1055's existing action analysis.
- #1069's target-parsing fix is included.
- Replay of the 2,845-command corpus, in two states (no gate; designing gate for an unrelated task), against develop's gate:
  - no command that develop blocks becomes allowed, except proven reads and the explicitly listed investigation commands;
  - the designing-state allow→block count falls well below 917, and every remaining one is listed with a reason.
- These pass: all hook suites; #1055's acceptance tests; `read_allowlist`; `review_risk_test`; build `--check`; generated-source-authority.

## Design

1. Start from #1055 head 2bc6e62. Merge #1069 (1 commit), then `origin/develop`.
2. Resolve the conflicts:
   - **Gate:** #1055's thin gate wins. Its `task_actions` already handles redirects and targets. Develop's legacy `READ_VERDICT`/`SAFE_PATTERNS`/`FD_SCAN` blocks belong to the code #1055 replaces, so they are dropped. Their must-block fixtures are kept and must still block.
   - **`review_risk_test.py` and the catalogs:** re-derive the edges and digests from the merged tree.
3. In `task_actions.action()`, consult `read-only-command.py` first:
   - exit 0 returns `read_only: true`;
   - exit 3 returns not-read-only, with an error naming the veto;
   - anything else proceeds unchanged.

   Nothing #1055 already blocks becomes allowed except commands the released classifier proves read-only. This is the same proof main ships today.
4. Leave lifecycle and R3 as #1055 has them. Record in the CHANGELOG that `complete` is included.

## What could go wrong

- **The `read-only-command.py` result is trusted at a new point.** Mitigation: the same classifier already gates main; the full `read_allowlist` and #1055's negative fixtures run against the merged tree.
- **Merge resolution drops a develop fix.** Mitigation: every develop gate fixture (`read_allowlist`, `universal_mutation_gate*`) runs against the merged gate.
- **Hub-cap and canonical-claims behaviour changes under the merge.** Mitigation: #1055's 42 acceptance tests and `task_keyed_gates.py` run.
- **The stacked PR (#1069) is reviewed against a head that no longer exists.** Mitigation: this PR supersedes both, and #1069 is closed with a pointer.

## Rollback

Revert the merge commit on develop. Releases ship only from main, so nothing deploys until a release PR merges.

## Not in scope

- R1, R2 and R4–R7 from the 936978a review stay follow-ups.
- Removing `task_actions.reader` entirely (#846 consolidation).
- The electinfo override retirement (#348), which follows the release.
