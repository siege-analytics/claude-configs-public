# Self-review: epic #962 F4 enforcement dependency risk

## Assumptions

Goal source: GitHub issue #962 latest comment (finding F4) and PR #958 review 5528052640.

Working as: software engineer responsible for review-policy enforcement and CI/runtime integrity.

Pre-mortem-artifact: `plans/pre-mortem-962-f4-enforcement-risk.md`

Hostile-review-artifact: `plans/hostile-review-962-f4-enforcement-risk.md`

- The requested base is exactly `0bae4ff108de5ad3b339a868818b05ea1e7c70bd`; both initial HEAD and merge-base with `origin/develop` matched it.
- F4 changes review classification and evidence only. It does not change hook runtime behavior, publish artifacts, install hooks, deploy, release, promote to main, or merge.
- A dependency is Tier C only when it can bypass, downgrade, or falsely validate a blocking decision, generate blocking runtimes, or define authoritative discovery for such a checker.
- Generated evidence remains below Tier C only when a Tier C checker recomputes expected bytes and rejects modified/deleted/stale output.

## Test plan

1. Reproduce exact-base Tier B for `hooks/lib/scope-check.sh`, `hooks/infrastructure/catalog-guard.sh`, and `bin/generated-source-authority.py`.
2. Require Tier C after the change for all audited dependencies.
3. For every added dependency, stage a modification, deletion, and rename to a documentation path; require Tier C and real CLI rejection of `--declared B`.
4. Parse source hook settings and an actual isolated build's generated blocking manifest/settings to derive entrypoints.
5. Pin exact executable caller-to-helper and CI invocation sites; remove each individual site in memory and require graph audit failure.
6. Invoke generated-source-authority and kernel-budget checkers against modified and deleted temporary catalogs, then require current catalogs to pass.
7. Run all 17 Python modules, all 36 hook suites, both workflow policy suites, all freshness gates, source and consumer hook validators, flat-layout validation, discipline scanner suite, and diff hygiene.
8. Run hostile review to acceptance and request external exact-SHA GitHub re-review after opening the draft PR.

## Peer review

The isolated hostile reviewer rejected five successive patch rounds and accepted round six. All findings and fixes are recorded in `plans/hostile-review-962-f4-enforcement-risk.md`.

The configured external OpenAI cross-review attempt failed with exhausted quota and is not represented as successful evidence. External exact-SHA review will instead be requested through GitHub Copilot on the draft PR.

## Lead review

- **Policy precision:** additions name three agent-comms blockers, one infrastructure guard, seven Python helpers, three shell helpers, five CI/runtime implementations, and two review-risk test suites. No `^hooks/` or `^hooks/(lib|infrastructure)/` catch-all was added.
- **Decision graph:** source registry plus actual generated manifest/settings cover active entrypoints; exact sites cover helper and workflow/checker edges.
- **Negative paths:** every F4 dependency receives modification, deletion, rename-source, and declared-B rejection coverage. Generated Tier A exclusions receive real modified/deleted checker rejection.
- **Advisory exclusions:** `log-block.sh` cannot alter caller block decisions because failures are ignored; scaffold-test-stub is unregistered; review-risk metrics derive evidence but do not classify/enforce; unknown agent-comms paths stay Tier B.
- **Generated changes:** `catalog/review-risk-metrics.json` is refreshed. The authoritative inventory generator recalculates heuristic source/test references after hardcoded paths became registry/build-derived edges, adding the strengthened test as evidence and updating the resulting summary count.
- **Rollback:** revert the single F4 commit. No external installation or deployment rollback is needed.

## Quantified claims

- Exact base reproduced: 1 commit SHA, `0bae4ff108de5ad3b339a868818b05ea1e7c70bd`.
- Named pre-change reproductions: 3/3 Tier B.
- F4 dependency paths under exhaustive change-shape tests: 21.
- Change shapes per dependency: 3 (modification, deletion, rename), each with declared-B rejection.
- Required source/generated entrypoints: derived from 1 canonical settings registry plus 1 isolated build's manifest/settings.
- Caller-to-helper edges: 45 exact edges, each with one exact invocation/validation site and individual removal detection.
- CI/checker invocation site specifications: 13, including 3 independently mutated `build.py` workflow occurrences.
- Generated exclusion catalogs: 2, each tested modified, deleted, and current.
- Hostile-review result: 5 REJECT rounds resolved, round 6 ACCEPT.
- Full validation target: 17 Python modules, 36 hook suites, 2 workflow policy suites, package/freshness/layout/discipline checks.
- Runtime load-set change: 0.
- Release/install/deploy/main/merge actions: 0.

## Canary and rollback

Canary: run `python3 bin/review-risk.py --paths <path> --declared B` for each named F4 path. The expected result is computed Tier C, `valid: false`, and exit 2. Run representative advisory/generated paths to confirm their documented lower tier remains unchanged.

Rollback: revert the F4 commit. This restores the prior policy, tests, metrics, inventory evidence, and documentation. Do not install, deploy, publish, release, promote, merge, or make the PR ready as part of rollback or verification.
