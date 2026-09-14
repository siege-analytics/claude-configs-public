---
ticket_refs:
  - siege-analytics/claude-configs-public#873: comment pending
---

# Self-review: #873 P2 -- session-unknown fail-safe on the workspace singleton

## What changed
- `hooks/lib/resolve-think-gate.py`: in `find_gate_for_repo`, the legacy
  workspace-root singleton branch now fails safe when the session id is
  unknown. A generic singleton (no repo_root, or a non-matching repo_root)
  no longer binds; a singleton with an explicit matching repo_root still does.
- `hooks/_test/session_signal_resolution.test.sh`: +2 scenarios.

## Why
D3: the resolver keys scoping on session identity, but when no session resolves
(outside Craft, or env unset) it fell through to the shared workspace-root
singleton. `_gate_matches_scope` only rejects on positive mismatch, so a generic
no-repo singleton bound to ANY repo. That is the cross-project bleed that
governed an unrelated action in the 2026-09-12 incident.

## Assumptions
- The develop resolver was already hardened (realpath + git-origin repo match,
  session + sessionId checks, --all foreign-session exclusion). The remaining
  hole was specifically the session-unknown + generic-singleton path. Verified by
  reading find_gate_for_repo and _gate_matches_scope on develop before editing.
- With a KNOWN session, the existing scope check is sufficient, so the new guard
  is gated on `if not sid`.

## Peer review (mechanics, correctness, craft floor)
- Syntax: `python3 -c "import ast; ast.parse(open('hooks/lib/resolve-think-gate.py').read())"` ok.
- The new branch reuses `_same_repo` (realpath + origin), not a basename compare.
- Scoped paths (session-dir, repo-scoped, repo-local) are untouched; only the
  legacy singleton branch changed.

## Lead review (adversarial: did this actually solve it?)
- Does a repo-matched singleton still work under unknown session? Yes -- new test
  "unknown session still binds a repo-matched singleton" passes.
- Does a known session regress? No -- all 16 prior scenarios still pass.
- Could this hide a legitimately-active gate? Only a generic no-repo singleton
  under an unidentifiable session, which is exactly the ambiguous case that
  should fail safe (the task can re-register a scoped gate).

## Quantified claims
- "18/0, 16 prior + 2 new" -- `bash hooks/_test/session_signal_resolution.test.sh` -> `Results: 18 passed, 0 failed`

## Rework ledger
| Rework trigger | Root skip | Check cost | Rework cost | Ratio |
|---|---|---|---|---|
| (none) | - | - | - | - |

## Trivial-investigation declaration
Not trivial -- investigation (investigate-gate.json #873) and pre-mortem exist.
