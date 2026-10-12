# Main/develop reconciliation and release manifest — 2026-10-12

## Invariant

Feature work integrates through `develop`; the only release promotion is `develop` → `main`; publishing and workspace installation occur only from the promoted `main` revision. After promotion, `main` is synchronized back into `develop` so `main` remains an ancestor of `develop`.

## Baseline

- Pre-reconciliation `main`: `f870439d2bd0ee995d5b5c24467d63094339977b`
- Pre-reconciliation `develop`: `391729146b77709ca007a120bf7f4d6735f22733`
- Divergence before reconciliation: 30 main-only commits and 38 develop-only commits by ancestry; patch-equivalent filtering reduced the effective content delta.

## Retained for the next main release

| Capability | Source work | Disposition | Verification |
|---|---|---|---|
| Gate scoping, runtime detection, and project/session resolution | #873 follow-ups, #880–#891, #893–#895 | Retain newer develop implementation | full build and hook matrix |
| CA enforcement manifest/runtime wiring | #892 follow-ups, #893–#895 | Retain | manifest, runtime, settings-drift tests |
| Hub concurrency stale-thread pruning | #915 | Retain develop side of conflict; it supersedes the older gate already on main | `hub_concurrency_gate.test.sh` |
| Session-local empty-REPO_ROOT signal resolution | #926 | Retain develop side of conflict | empty-root and session-resolution tests |
| Test-tracking and comprehensive-test caller coverage | #931–#934, #943–#947 | Retain | dedicated guard tests plus settings drift |
| Hostile-review hardening and source/artifact reconciliation | #935–#939 | Retain | build/reference validation |
| Coordinator and fix-shape guard corrections | #937, #940–#942 | Retain | dedicated guard tests |
| Committed merge-then-deploy policy | #924 | Retain after mutable-marker bypass correction | #924 focused tests, baseline hook tests, hosted CI |
| Review/design records under `plans/` | associated merged PRs | Retain as source provenance; not runtime deployment content | build excludes them from consumer packages |

## Discarded or superseded

- PR #906: closed without merge; exact content was already merged through #905 and its simulated merge had no tree delta.
- Older main-side versions of the four conflicted files: superseded by the tested develop implementations above.
- Scoped `promote/*`, release-branch, and hotfix bypass routes: removed by the accompanying policy change; future main PRs must have head `develop`.
- No already-merged develop capability is removed in this reconciliation. Each effective code group has an associated merged PR and focused tests; removal would be a new product decision rather than cleanup of duplicate promotion history.

## Conflict resolutions

- `bin/_test/settings_drift_test.py`: keep develop’s 40 triples / 31 hooks fixture.
- `hooks/_test/hub_concurrency_gate.test.sh`: keep develop’s #915 stale-pruning coverage.
- `hooks/agent-comms/hub-concurrency-gate.sh`: keep develop’s #915 implementation.
- `hooks/lib/resolve-think-gate.py`: keep develop’s #926 session-scoped modes.

## Release gate

Promotion is allowed only after the reconciled tree passes reference synchronization, `build.py --check`, a full build, layout/hook validation, settings drift, notebook guards, every hook scenario test, GitGuardian, and review on the canonical `develop` → `main` PR.
