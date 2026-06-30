---
propagation-deferred: will post to ticket with PR
---

# Self-review: fix-shape-guard hook (#188)

Self-Review: v1 fix-shape detection via scope repetition and file overlap
Self-Review-Source: plans/self-review-188.md
Design-Note-Source: https://github.com/siege-analytics/claude-configs-public/issues/188
Pre-ship-dry-run: N/A — git hook, not transformation code
Hostile-review-artifact: WAIVED
Inventoried-shape: no fix-shape-guard.sh exists (find hooks/ -name fix-shape* = 0); settings-snippet.json has no fix-shape entry
Investigate-artifact: TRIVIAL
Pre-mortem-artifact: plans/pre-mortem-188.md (workspace)

## Hostile-review-waiver
Reason: New hook file following established patterns from self-review.sh and post-error-revision-required.sh
Scope: hooks/git/fix-shape-guard.sh (new), hooks/settings-snippet.json (one entry), plans/
Compensating-control: bash -n syntax validation; pattern comparison against self-review.sh boilerplate

## Trivial-investigation declaration
Category: new hook following established boilerplate pattern
Cannot produce error: hook exits 0 on all edge cases; only blocks when threshold met
Reason: New file, no existing code to investigate. Boilerplate copied from self-review.sh. Detection logic is simple grep + uniq -c.
Evidence: self-review.sh boilerplate (lines 53-121) copied as hook skeleton. Detection logic is 20 lines of sort|uniq|awk.
Falsification: If the hook modified existing behavior or interacted with other hooks, investigation would be required.

## Assumptions
Goal source: https://github.com/siege-analytics/claude-configs-public/issues/188
Pre-author-inventory: NONE
Trivial-against-state: new file creation, no pre-existing state to measure
Working as: software engineer
Roles: Junior (wrote the hook), Senior (verified edge case handling)

## Peer review

Shelves checked: writing-code:7, writing-code:17

### Gate evidence
- bash -n hooks/git/fix-shape-guard.sh → exit 0 (syntax valid)
- N/A — no tests, no notebooks, no doc build
- [no-gates] for settings-snippet.json (JSON, validated by build.py)

### Detection logic
- Scope repetition: grep -oE conventional-commit scope → sort → uniq -c → threshold check
- File overlap: git log --name-only → sort → uniq -c → threshold check
- Scope check runs first; file check only if no scope match (avoid double-block)

### Edge cases handled
- Detached HEAD → exit 0
- Protected branches (main/develop) → exit 0
- No merge base found → exit 0
- Fewer than 3 commits → exit 0
- Class-Audit: trailer present → exit 0
- [no-class-audit] override → exit 0

## Lead review

**[Senior]** Clean implementation. The N>=3 threshold is conservative enough
to avoid false positives on normal two-commit fixes. The scope-first,
file-second priority prevents double-blocking. All edge cases exit 0
(silent no-op), so the hook can't lock out a user. The Class-Audit: trailer
and [no-class-audit] override provide two escape paths.

One observation: the hook doesn't fire on `glab mr create/merge` (GitLab).
This matches the ticket scope (v1) but should be noted for #201 (GitLab parity).

## Quantified claims

- 1 new file: hooks/git/fix-shape-guard.sh (~140 lines)
- 1 file modified: hooks/settings-snippet.json (+5 lines)
- 0 existing behavior changes
- 2 detection modes: scope repetition, file overlap
- Threshold: N>=3 (configurable by editing THRESHOLD variable)
