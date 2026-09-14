---
ticket_refs:
  - siege-analytics/claude-configs-public#873: comment pending
---

# Self-review: #873 P4 -- gate_applies() task-relevance predicate

## What changed
- `hooks/lib/gate-registry.sh`: add `gate_applies <gate-id> <action-class>
  [runtime]`. Returns "block" only when the gate governs the current action
  class AND its runtime policy blocks; otherwise "advisory".
- `hooks/_test/gate_registry.test.sh`: +6 scenarios (and a no-class fixture).

## Why
D1: gates had no task-relevance axis -- a gate fired regardless of whether the
current action was in its scope. gate_applies makes relevance explicit: a gate
whose action_class differs from the action being attempted is advisory, even if
its policy is block. That is the "a design gate must not block list *.pdf" fix.

## Assumptions
- Unknown/empty current action class is treated as in-class (conservative: do
  not silently stop governing because the action could not be classified).
  Verified by the "empty action class -> in-class" test.
- A gate with no declared action_class governs everything (legacy behavior).
  Verified by the no-class fixture test.
- gate_applies composes the P0 primitives (gate_action_class + gate_runtime_policy)
  and changes no guard yet; guards wire it in a follow-up.

## Peer review (mechanics, correctness, craft floor)
- Syntax: `bash -n hooks/lib/gate-registry.sh` ok.
- Pure function over the manifest; inherits the fail-soft behavior of its
  callees (missing manifest -> advisory).
- Decision table covered: in-class+block, out-of-class (x2), in-class+advisory,
  empty-action, no-declared-class.

## Lead review (adversarial: did this actually solve it?)
- Does an out-of-class action escape a blocking gate? Yes by design -- that is
  the point; tested for branch-guard vs mutation and vs design.
- Could it let a relevant mutation through? No -- in-class + block still returns
  block (tested); empty/unknown action is in-class (conservative), not skipped.
- Does it change enforcement today? No -- no guard calls gate_applies yet; this
  PR adds the predicate and its tests only.

## Quantified claims
- "17/0, +6 new" -- `bash hooks/_test/gate_registry.test.sh` -> `Results: 17 passed, 0 failed` (11 prior + 6 new gate_applies, minus none; net 17).

## Rework ledger
| Rework trigger | Root skip | Check cost | Rework cost | Ratio |
|---|---|---|---|---|
| test referenced $TMP/noclass.json before creating it | wrote assertion before fixture | caught pre-run on read-back | added fixture | low |

## Trivial-investigation declaration
Not trivial -- #873 investigation and pre-mortem exist.
