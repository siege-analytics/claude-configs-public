---
ticket_refs:
  - siege-analytics/claude-configs-public#873: comment pending
---

# Self-review: #873 P0 -- runtime detection + gate registry/manifest

## What changed
- `bin/build.py`: each CA_ENFORCEMENT_GATES entry gains `action_class`,
  `runtime_policy` (per-host advisory/block), and `block_signals`. Regenerated
  `dist/craft-agent/enforcement-manifest.json`.
- `hooks/lib/gate-registry.sh` (new): reads the manifest; exposes
  `gate_field`, `gate_action_class`, `gate_runtime_policy`. Fail-soft.
- `hooks/lib/detect-host.sh`: add a `codex-cli` arm (CODEX_SANDBOX,
  CODEX_SANDBOX_NETWORK_DISABLED), tested after craft.
- Tests: `gate_registry.test.sh` (new, 11), `detect_host.test.sh` (+codex, 32).

## Why
D5 (no runtime awareness) and D6 (hardcoded gate identity) are the primitives
the rest of #873 builds on. detect-host.sh already did runtime detection (#696),
so P0 extends it (codex arm) rather than duplicating, and adds the manifest
dimensions + reader that P1/P4 will consume.

## Assumptions
- P0 is additive and inert: the manifest carries new fields but no hook reads
  them yet, so no gate behavior changes in this PR. Verified: no guard script
  modified; only build.py (manifest data), the new reader lib, detect-host.sh,
  and tests.
- CODEX_SANDBOX is a process-level Codex marker, not a user-typed label.
  Flagged in-code as needing a docs/probes entry, matching detect-host's
  evidence discipline. If wrong, only the codex-cli arm misfires; craft and
  claude-code detection are untouched (verified by unchanged precedence tests).

## Peer review (mechanics, correctness, craft floor)
- Syntax: `bash -n hooks/lib/gate-registry.sh hooks/lib/detect-host.sh` ok;
  `python3 -c "import ast; ast.parse(open('bin/build.py').read())"` ok.
- Reader fails soft (missing/unreadable manifest, absent gate, unknown runtime
  all return advisory/empty, exit 0) -- tested.
- Default is advisory, matching #873 intent (a gate with no opinion narrates,
  does not hard-halt).

## Lead review (adversarial: did this actually solve it?)
- Does it change enforcement today? No -- additive/inert, proven by no guard
  edits and the full detect_host suite still green.
- Could the codex arm misclassify craft/claude-code? No -- craft tested first
  (precedence test added); codex vars are disjoint from craft/claude vars.
- Does the reader hard-error and block a tool call if the manifest is gone? No
  -- the "absent gate exits 0" and fail-soft tests assert exit 0.

## Quantified claims
- "detect_host 32/0" -- `bash hooks/_test/detect_host.test.sh` -> `Results: 32 passed, 0 failed`
- "gate_registry 11/0" -- `bash hooks/_test/gate_registry.test.sh` -> `Results: 11 passed, 0 failed`

## Rework ledger
| Rework trigger | Root skip | Check cost | Rework cost | Ratio |
|---|---|---|---|---|
| gate_registry test "missing manifest action_class empty" failed | unreadable override falls back to dist by design; test assumed empty | 1 test run | fix test to use empty-gates manifest | low |

## Trivial-investigation declaration
Not trivial -- investigation (investigate-gate.json #873, F1-F5) and pre-mortem
(plans/pre-mortem-gate-scoping-873.md) exist.
