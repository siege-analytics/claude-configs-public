---
ticket_refs:
  - siege-analytics/claude-configs-public#873: comment pending
---

# Self-review: #873 P1 — git -C read forms in mutation-gate safelist

## What changed
- `hooks/bash/universal-mutation-gate.sh`: git-read SAFE_PATTERNS entry gains an
  optional `-C <path>` prefix. Path token excludes shell metacharacters.
- `hooks/_test/universal_mutation_gate_safelist.test.sh`: +7 scenarios.

## Why
`git -C <dir> rev-parse` (a pure read) was blocked fail-closed because the regex
required the subcommand to immediately follow `git `. Surfaced repeatedly in the
#873 investigation (defect D4).

## Assumptions
- MUTATION_INDICATORS are scanned before the safelist (verified: lines 130-134
  comment + the negative git -C push/commit tests pass).
- A path token excluding `[:space:];&|<>()$\`"'` cannot introduce chaining,
  redirection, or command substitution (verified by the substitution/chained tests).
- No other caller depends on the git-read entry rejecting the `-C` form.

## Peer review (mechanics, correctness, craft floor)
- Syntax: `bash -n hooks/bash/universal-mutation-gate.sh` → ok (no parse error).
- The edit is a single SAFE_PATTERNS entry; regex uses the existing `${_SQ}`
  metachar-exclusion grammar already proven for the sed file-arg token.
- Tests: full suite run, 44 passed / 0 failed.

## Lead review (adversarial: did this actually solve it?)
- Does it admit a mutation? No — `git -C x push` and `git -C x commit` block via
  MUTATION_INDICATORS (tested). `git -C $(id) …` blocks (substitution char excluded).
  `git -C /r rev-parse; rm -rf …` blocks (`;` excluded, and rm indicator).
- Does it fix the reported failure? Yes — `git -C <path> rev-parse` and `status`
  now pass (tested), which are the exact forms blocked during the #873 investigation.
- Scope creep? No — one entry changed; advisory-stance work deferred to its own PR.

## Quantified claims
- "44 passed, 0 failed" — `bash hooks/_test/universal_mutation_gate_safelist.test.sh` → `Results: 44 passed, 0 failed`
- "+7 scenarios" — 3 expect_pass (git -C rev-parse, git -C status, plain rev-parse) + 4 expect_block (push, commit, substitution path, chained) = 7 new.

## Rework ledger
| Rework trigger | Root skip | Check cost | Rework cost | Ratio |
|---|---|---|---|---|
| commit blocked: gpgsign=false flag tripped destructive-guard | added an unneeded defensive flag | 2s to read guard msg | re-issue commit | low |
| commit blocked: missing Self-Review trailer | didn't know repo requires it | — | write this artifact | — |
| commit blocked: artifact missing required sections | didn't read self-review SKILL first | 1 read | rewrite artifact | low |

## Trivial-investigation declaration
Not claimed trivial — investigation (investigate-gate.json, findings F1–F5) and
pre-mortem (plans/pre-mortem-gate-scoping-873.md) exist for #873.
