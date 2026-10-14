# #975 Tier C pre-mortem — language/framework scope

Base: exact `develop` `b9b631988091fcabdc1c531087da57c5ca1a0419`. Integration target: draft PR to `develop` only. No deploy/install/release/main/merge.

| Failure | Severity | Falsification / mitigation |
|---|---|---|
| A mention of a project or book is mistaken for an authoritative consumer | Tiger | Ledger records UNKNOWN for non-project sources; exact GitHub host+repo match and foreign-host/explicit-slug fixtures. No new QML project identity. |
| Authored global content remains prescriptive despite no auto-route | Tiger | Scope Siege Utilities to project rule, turn QML skill into generic optional review, preserve historical instructions as non-prescriptive reference, condition Vue contracts; inspect generated copies. |
| Reference shelf or rejected slug leaks into a matching route | Tiger | Mask explicit tokens before prose routing; reject shelves and foreign-host project slugs; regression in source and consumer packages. |
| Added routes stack too broadly or silently exceed budget | Tiger | Narrow explicit signals; positive/negative/unknown/multi-route/over-budget fixtures with 12/80k/20k caps and kernel-only fallback. Scala routing stays #976. |
| Generated snapshots/measurements become stale | Elephant | Build → inventory → authority → manifest/metrics/ledger check; full Python/hook/workflow suites and isolated packaged canaries. Costs are chars and ceil(chars/4), not runtime savings. |
| Lifecycle responsibilities or slugs are erased as cleanup | Elephant | Preserve source paths and all sources; no completion/retirement; verify source count and authority parity. |

Review gate: independent hostile review, fix findings, focused re-review on latest diff before draft PR.
