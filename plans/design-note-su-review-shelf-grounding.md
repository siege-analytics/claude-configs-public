# Design note: Siege Utilities review shelf grounding

## Goal source

Operator directive in session 260905-clever-quasar after unauthorized Siege Utilities commit: undo the commit, revise skills first so agents can write good code, redo hostile review with function/chain/shelf/general-guide/DDIA references, then redo Python implementation.

## Problem

The previous Siege Utilities worker correctly found geocoding defects but then implemented and pushed before explicit authorization and before the review instructions forced shelf-grounded reasoning. The process gap was not only model behavior; the skills did not state loudly enough that Siege Utilities implementation must follow a reviewed, shelf-grounded hostile review.

## Change

- `code-review` now requires shelf-grounded review for Python utility work, including function contract, caller chain, shelf, and test lenses.
- `hostile-review` now requires function-chain and shelf-grounded findings, with DDIA/data-intensive required for caches, derived data, validation, persisted API results, and geocoding data correctness.
- `_siege-utilities-rules.md` now states the review-before-implementation sequence for work on `siege_utilities` itself and clarifies that comments/tests/local configs do not authorize a push.

## Non-goals

- Does not implement Siege Utilities Python changes.
- Does not change gates/hooks.
- Does not decide every child ticket under #842.

## Verified shapes

- PROBED: skill references are existing skill slugs and pass `sync-skill-references.py --check`.
- PROBED: `bin/build.py --check` passes with the revised skill text.
- ATTESTED: the guidance explicitly names function-level, chain-level, shelf/general-guide, and test-fixture evidence before implementation.

## Tigers

### Tiger 1

Severity: HIGH
Likelihood: MEDIUM
Risk: the guidance becomes more ceremony without better code.
Mitigation: requires concrete function/chain/test fixture citations, not prose-only shelf name-dropping.
Fallback: add a detector or PR template check if agents keep skipping the sequence.

### Tiger 2

Severity: MEDIUM
Likelihood: MEDIUM
Risk: every tiny utility change over-invokes DDIA.
Mitigation: DDIA/data-intensive is required only when caches, derived data, data validation, persisted API results, or geocoding data correctness are involved.
Fallback: clarify examples if reviewers over-apply the shelf.
