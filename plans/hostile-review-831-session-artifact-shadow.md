# Hostile review: #831 stale session-scoped artifact gate shadowing

Reviewer source: independent secondary model, Sonnet-class with extended reasoning.

## Initial review

Verdict: BLOCK.

Findings:

- HIGH: Generic no-ticket/no-task artifact gates could still match any current ticket.
- HIGH: Generic workspace-root artifacts without explicit repo/session scope could still authorize mutation.
- MEDIUM: Repo scoping compared only basename, allowing same-basename repo collisions.
- MEDIUM: Tests did not cover generic artifacts, workspace-global artifacts, foreign/session scope, or same-basename repo collisions.

## Fixes after initial review

- Artifact gates resolved through `--resolve-many` now require explicit current ticket/task.
- Artifact gates resolved through `--resolve-many` now require explicit repo scope and session marker when session id is known.
- Repo identity checks use realpath equality or matching git remote origin, not basename alone.
- Tests cover generic session artifacts, generic workspace-root artifacts, same-basename repo collision, stale-only block, current-artifact pass, and `--session-known`.

## Final review

Verdict: PASS.

Confirmed:

- Stale wrong-ticket session artifacts no longer shadow current repo-scoped artifacts.
- Generic no-ticket/no-task artifacts do not satisfy current-ticket matching.
- Generic workspace-root artifacts without explicit repo/session scope do not authorize mutation.
- Same-basename different repos are rejected via realpath/origin matching.
- `--session-known` is implemented.
- Stale-only/generic-only cases fail closed.
- Worktree regression risk is low: linked worktrees should resolve through shared origin; mismatched origin URL formats fail closed rather than bypass.
