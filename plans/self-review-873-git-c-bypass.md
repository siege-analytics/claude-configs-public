---
ticket_refs:
  - siege-analytics/claude-configs-public#873: comment pending
---

# Self-review: #873 follow-up -- close git -C mutation bypass (review finding)

## What changed
- `hooks/bash/universal-mutation-gate.sh`:
  1. Normalize `git -C <path>` to `git ` on a scan copy BEFORE the mutation
     scan, so the git MUTATION_INDICATORS (anchored to `git <subcommand>`) match
     the -C form too.
  2. Add an explicit `git remote (add|remove|rm|rename|set-url|set-head|
     set-branches|prune)` mutation indicator (with optional -C), closing a
     pre-existing hole where the `remote` read entry admitted remote writes.
- `hooks/_test/universal_mutation_gate_safelist.test.sh`: +8 regression cases.

## Why
Adversarial review of PR #880 found that the `git -C <path>` read-safelist
prefix created a fail-closed BYPASS: because every git MUTATION_INDICATOR
requires the subcommand to immediately follow `git `, inserting -C made them all
miss, and the widened safelist then admitted `git -C <dir> branch -D`, `tag -f`,
`config --global`, etc. Reproduced live (allowed with -C, blocked without).
Review also surfaced `git remote add` passing even without -C (pre-existing).

## Assumptions
- Normalizing -C away for the mutation scan is safe: the path token excludes
  shell metacharacters (same grammar as the safelist), so the sed substitution
  cannot itself introduce chaining/substitution. The read safelist still sees
  the original command, so -C reads still pass.
- `git remote` reads (bare, -v, show, get-url) must keep passing; only the write
  verbs are added to the indicators. Verified.

## Peer review (mechanics, correctness, craft floor)
- Syntax: `bash -n hooks/bash/universal-mutation-gate.sh` ok.
- Live matrix: git -C {branch -D, tag -f, config --global, commit, remote add}
  all BLOCK; git -C {rev-parse, status, remote show, remote -v} all PASS; same
  for the non--C forms.

## Lead review (adversarial: did this actually solve it?)
- Any git mutation still bypass via -C? Checked branch/tag/config/commit/remote
  -- all block now (tested). Normalization is general, not per-pattern, so a
  future indicator is covered automatically.
- Did reads regress? No -- git -C rev-parse/status/remote show/remote -v pass
  (tested), and the prior 44 safelist scenarios still pass.
- Could the sed normalization corrupt a legitimate command? It only rewrites a
  `git -C <metachar-free-path> ` prefix to `git `; the safelist re-checks the
  original, and the mutation scan is the only consumer of the normalized copy.

## Quantified claims
- "52/0, +8" -- `bash hooks/_test/universal_mutation_gate_safelist.test.sh` -> `Results: 52 passed, 0 failed` (44 prior + 8 new).

## Rework ledger
| Rework trigger | Root skip | Check cost | Rework cost | Ratio |
|---|---|---|---|---|
| PR #880 shipped a mutation bypass | did not add -C to the mutation indicators when widening the safelist | adversarial review (this) | this follow-up fix | high value of the check |

## Trivial-investigation declaration
Not trivial -- security fix to the mutation gate; investigation is the review
finding itself (reproduced live).
