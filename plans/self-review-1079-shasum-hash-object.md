---
ticket_refs:
  - siege-analytics/claude-configs-public#1079: read-only-command.py allowlist gaps block common verification reads
---

# Self-review: #1079 shasum and write-free git hash-object are proven reads

## Assumptions

Pre-author-inventory: at develop 7cf7677 the classifier returned exit 1 for `shasum -a 256 f` and for `git hash-object f`. Each is exit 4 in a pipeline, which blocks install-verification pipelines with no gate.
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1079
Pre-mortem-artifact: plans/pre-mortem-1079-shasum-hash-object.md
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1079
Project-contribution: install and deploy verification (checksums against source and tag) runs without a task gate.

## Peer review

- **writing-code:** `shasum` joins `PLAIN`. `git hash-object` is proven only when `hash_object_writes()` is false, and the same predicate is a veto in `unsafe()`.
- **writing-tests:** 5 must-block cases and 7 must-allow cases are added to `read_allowlist`.

## Lead review

- **Solves #1079:** yes, all three shapes. `gh api … | shasum` passes now that `shasum` is proven.
- **Not done:** the electinfo override port. It follows as a separate PR, as before.

## Quantified claims

- Suites:
  - `read_allowlist`: 197/197.
  - `universal_mutation_gate`: 29/29.
  - `safelist`: 60/60.
  - `831` and `empty_reporoot`: PASS.
  - `review_risk_policy`: 12/12.
  - `review_risk_test`: PASS.
- Replay of 2,845 commands, develop vs this branch:
  - 4 commands newly allowed, all `git hash-object` with no write flag.
  - 0 newly blocked.
  - The designing state is unchanged.
