---
propagation-deferred: will post to ticket with PR
---

# Self-review: propagation-deferred resolution warning (#251)

Self-Review: v2.5 advisory warning for unresolved propagation-deferred files
Self-Review-Source: plans/self-review-251.md
Design-Note-Source: https://github.com/siege-analytics/claude-configs-public/issues/251
Pre-ship-dry-run: N/A — self-review.sh is a bash enforcement hook, not transformation code
Hostile-review-artifact: WAIVED
Inventoried-shape: self-review.sh v2.4 ends at line 1036, exit 0 at line 1039; DIFF_FILES available at line 579
Investigate-artifact: TRIVIAL
Pre-mortem-artifact: plans/pre-mortem-251.md (workspace)

## Hostile-review-waiver
Reason: Single addition to existing enforcement hook, advisory only (no exit 2)
Scope: hooks/git/self-review.sh (new v2.5 block)
Compensating-control: bash -n syntax validation; advisory-only (cannot lock out users)

## Trivial-investigation declaration
Category: advisory warning addition to existing hook
Cannot produce error: exits 0 regardless (warning only, no block)
Reason: Adding a stderr warning to an existing hook. No blocking behavior. Pattern is simpler than v2.3/v2.4 blocks.
Evidence: v2.5 block never calls exit 2. All paths continue to exit 0.
Falsification: If the warning could cause exit 2, investigation would be required.

## Assumptions
Goal source: https://github.com/siege-analytics/claude-configs-public/issues/251
Pre-author-inventory: NONE
Trivial-against-state: advisory warning addition, no state contact
Working as: software engineer
Roles: Junior (wrote the warning), Senior (verified advisory-only behavior)

## Peer review

Shelves checked: writing-code:17

### Gate evidence
- bash -n hooks/git/self-review.sh → exit 0 (syntax valid)
- N/A — no tests, no notebooks, no doc build

### Advisory-only verification
- v2.5 block never calls exit 2 — only cat >&2 for warning text
- All paths fall through to exit 0
- Pattern: read DIFF_FILES, check .md files for propagation-deferred:, warn on stderr

## Lead review

**[Senior]** Clean advisory addition. The critical property is that it
never blocks (no exit 2). The while-read loop over DIFF_FILES is safe —
empty DIFF_FILES produces empty DEFERRED_FILES, no warning emitted.
The head -20 limit prevents reading entire large files. The case
filter ensures only .md files are checked.

## Quantified claims

- 1 file modified: hooks/git/self-review.sh
- v2.5 block is ~25 lines
- 0 blocking behavior (advisory only)
- 0 new dependencies
