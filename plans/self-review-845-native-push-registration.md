# Self-review: #845 native push registration and range semantics

Pre-mortem-artifact: plans/pre-mortem-845-native-push-registration.md
Hostile-review-artifact: plans/hostile-review-845-native-push-registration.md

## Assumptions

- Implementation begins on accepted package head `f979295b17b1d4c94cb59d1164e235db2d0b542a`, now integrated into develop as `c2ed26de0b9d936884df473527f5226667ff4f06`.
- `hooks/git/pre-push-self-review.sh` retains the accepted trailer/risk checks. Its range selection excludes only the actual destination’s advertised heads; missing objects require fetching that destination. The old `--remotes` exclusion could hide a bad interior commit via another remote or a fabricated tracking ref.
- Native hooks are bypassable local feedback. Final protected authorization remains #1002's provider-bound exact-range adapter.
- Consumer installation must name the consumer repository; workspace settings installation alone cannot imply native Git registration.

## Test plan

- Build all consumer packages and confirm generated native wrapper bytes agree.
- Install into disposable consumer repositories with explicit and invalid target combinations.
- Use real local bare-remote pushes to reject an invalid interior commit and missing source evidence, then permit a repaired valid range.
- Mutate/remove the wrapper, range hook, risk helper, policy, executable bits, and registered path independently; require verification failure and unchanged remote refs.
- Run Tier C downgrade probes, focused tests, full Python/hook/workflow suites, canonical builds, inventory, generated authority, and freshness checks.

## Peer review

Pending independent exact-head review.

## Lead review

Pending independent exact-head review.

## Quantified claims

Sixteen focused scenarios pass for actual push effects, installer preservation/registration and verifier negative mutations. The full 85-command matrix completed in 513.1 seconds with 84 passes and one stale settings-count assertion: removal of the native hook from tool-JSON registration changes 40/31 to 39/30. That expectation was corrected and the full settings-drift fixture replay passes. All other Python modules, 36 hook suites, both workflow suites, build/freshness and three validators pass. Logs: `/tmp/cc-845-full-validation.log`, `/tmp/cc-845-settings-drift-replay.log`. Independent exact-head review and hosted validation remain required before integration.

## Rollback and non-claims

Revert the bounded #845 commit. No existing consumer, shared workspace, release branch, `main`, live Craft session, provider ruleset, or production credential is changed. Native registration does not establish server-side authorization.
