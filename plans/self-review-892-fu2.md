---
ticket_refs:
  - siege-analytics/claude-configs-public#892: comment pending
---

# Self-review: #892 FU2 -- project-scoped gate files

## What changed
- `hooks/lib/resolve-think-gate.py`: `find_gate_for_repo` and `_candidate_paths`
  now consult `<gate>-<project-slug>.json` (project from resolve_project) after
  the repo-slug workspace file and before the repo-local/umbrella fallbacks.
- `hooks/_test/project_scoped_gate.test.sh` (new): 3 scenarios.

## Why
D2 completion. #873 P3 added resolve_project() but gate files were not yet
project-scoped. This lets a project (electinfo, siege-utilities, ...) carry a
gate that applies to every repo in the project, while repo-specific gates still
win and umbrella (no project) repos are unchanged.

## Assumptions
- Precedence: session > repo-slug > project-slug > repo-local > umbrella
  singleton. Repo-specific is more specific than project, so it wins (tested).
- 'umbrella' is skipped in the project tier (it is the legacy singleton below),
  so a repo in no project sees zero behavior change -- additive (tested: repo in
  no project returns NONE, not the project gate).
- resolve_project fails soft (returns 'umbrella' on any ambiguity, never
  raises), so the new tier cannot break resolution.

## Peer review (mechanics, correctness, craft floor)
- Syntax: `python3 -c "import ast; ast.parse(...)"` ok.
- The project tier applies `_gate_matches_scope` exactly like the other tiers.
- _candidate_paths mirrors find_gate_for_repo's order so the resolve_many
  strict re-scan stays consistent.

## Lead review (adversarial: did this actually solve it?)
- Does it regress #873 P2 session fail-safe? No -- session_signal_resolution
  still 18/0; the project tier is inserted below the session/repo tiers and does
  not touch the legacy-singleton fail-safe.
- Does a repo-specific gate still win? Yes (tested: #repo beats #project).
- Does an unrelated repo pick up a project gate? No (tested: NONE).
- Cross-project inheritance? A project gate binds only for repos whose origin
  matches that project's PROJECT.md repo:, so project A's gate never applies to
  project B.

## Quantified claims
- "project_scoped_gate 3/0" -- `bash hooks/_test/project_scoped_gate.test.sh` -> `Results: 3 passed, 0 failed`
- "resolver suite still 18/0" -- `bash hooks/_test/session_signal_resolution.test.sh` -> `Results: 18 passed, 0 failed`

## Rework ledger
| Rework trigger | Root skip | Check cost | Rework cost | Ratio |
|---|---|---|---|---|
| first test used a fragile nested bash -c | over-engineered the harness | pre-run read-back | simplified to a ticket_for helper | low |

## Trivial-investigation declaration
Not trivial -- #892 investigation and pre-mortem exist.
