# Self review: nested shelves by path only

## Assumptions

Goal source: runtime validation showed `shelves--systems-architecture`, `shelves--data-intensive`, and `shelves--geospatial` are not directly loadable as workspace skill slugs in this session.
Working as: software engineer and tech lead
Pre-author-inventory: validated parent and nested shelf slug lookup behavior; inspected active references introduced/repaired in prior hotfix.
Investigate-artifact: plans/self-review-nested-shelves-paths-only.md
Pre-mortem-artifact: plans/self-review-nested-shelves-paths-only.md
Hostile-review-artifact: plans/self-review-nested-shelves-paths-only.md
Project-contribution: removes ambiguity for collaborator sessions: nested DDIA/geospatial shelves must be read by explicit file path, not `[skill:]` invocation.

## Peer review

- writing-rules:1 PASS — no new enforcement claims.
- writing-rules:8 PASS — avoids unverifiable nested `[skill:]` slugs; uses explicit shelf file paths.
- shelf-readiness/routing PASS — preserves DDIA/geospatial routing requirements through concrete file paths.

## Validation

- `python3 bin/sync-skill-references.py --check`
- `python3 bin/build.py --check`
- `git diff --check`

## Lead review

Approved. This follow-up removes the remaining ambiguity introduced by the first hotfix: nested shelves are named as concrete repository files, not as runtime skill invocations.

## Quantified claims

- 0 direct DDIA/geospatial nested shelf invocation refs introduced by this follow-up.
- Reference sync, build check, and whitespace diff checks pass locally.
