---
ticket_refs:
  - siege-analytics/claude-configs-public#873: comment pending
  - electinfo/craft-agents#49: comment pending
---

# Self-review: #873 P1 (guards) -- advisory UserPromptSubmit branch guards + audit

## What changed
- `hooks/resolver/branch-state-guard.sh`: no longer emits {"continue": false} on
  a protected branch. Emits an advisory <branch-state-guard> narration and logs
  the would-have-blocked event.
- `hooks/resolver/pre-action-guard.sh`: same for detached HEAD and protected
  branch. Workaround-tally advisory unchanged.
- `hooks/_test/branch_state_advisory.test.sh` (new): 8 scenarios.

## Why
This is the source fix for craft-agents#49. Both hooks emitted continue:false,
which Craft honors as a hard turn-halt BEFORE the model runs, so a workspace in
detached HEAD (or on a protected branch) hard-halted EVERY Claude turn including
read-only questions. The hard block belongs at the PreToolUse mutation point
(branch-guard.sh still blocks the actual commit); at prompt-submit we narrate.

## Assumptions
- Removing the prompt-submit block does not remove enforcement: the PreToolUse
  git branch-guard and the native pre-push branch-guard still hard-block real
  commits/pushes to protected branches. This hook only ever fired at
  prompt-submit, where a block is wrong for a read-only turn.
- Audit visibility must not be lost -> every would-have-blocked event is logged
  to enforcement-blocks.jsonl via log_block_event (fail-safe, never errors under
  set -e). Verified: the log file is written (test) .

## Peer review (mechanics, correctness, craft floor)
- Syntax: `bash -n` on both guards ok.
- log_block_event call matches its 3-arg signature (gate_id, invariant, command).
- set -e safety: the audit calls are guarded with `|| true` and readability
  checks so a missing/broken log-block.sh degrades rather than aborts the hook.

## Lead review (adversarial: did this actually solve it?)
- Does a Craft Claude turn still get hard-halted on detached HEAD? No -- tested:
  no continue:false in detached HEAD, an advisory is emitted instead.
- Can you still commit to a protected branch undetected? No -- the commit-time
  branch-guard is unchanged; this only relaxes the prompt-submit narration.
- Feature-branch happy path? Silent, unchanged (tested).
- Enforcement visibility? Preserved in the audit log (tested).

## Quantified claims
- "8/0" -- `bash hooks/_test/branch_state_advisory.test.sh` -> `Results: 8 passed, 0 failed`
- "resolver suite still 18/0" -- `bash hooks/_test/session_signal_resolution.test.sh` -> `Results: 18 passed, 0 failed`

## Rework ledger
| Rework trigger | Root skip | Check cost | Rework cost | Ratio |
|---|---|---|---|---|
| (none) | - | - | - | - |

## Trivial-investigation declaration
Not trivial -- #873 investigation and pre-mortem exist; this is the highest-stakes
change in the epic (alters guard behavior), fully tested.
