# Self-review: merge updated develop into F4

## Assumptions

Goal source: coordinator message from Skills-Reviser Session Recovery.

Working as: software engineer responsible for F4 review-policy integrity across F1-F4 integration.

Pre-mortem-artifact: `plans/pre-mortem-962-f4-develop-merge.md`

Hostile-review-artifact: `plans/hostile-review-962-f4-develop-merge.md`

- F4 head before merge was `d229e043a15ef76a31a227ceeb9a83f44254484a`.
- Updated develop is `4dcad7c2582cf1fca13d9ad922513599fd1234ca` and contains F1 plus F2/F3.
- The only merge conflict was generated `catalog/skills-inventory.json`; the authoritative generator resolved it.
- No main, release, deployment, installation, publication, ready transition, or PR merge is authorized.

## Test plan

1. Run F4 dependency/invocation audit and commit/push policy suite.
2. Run F1 synthetic promotion graph fixtures, ordinary lifecycle freshness, and raw pinned-main no-event negative.
3. Run F2/F3 four-layout isolated consumer runtime test.
4. Run all 18 Python modules, 36 hook suites, and 2 workflow policy suites.
5. Run full build/check, generated authority, kernel, review/progressive metrics, language/data scope, inventory, lifecycle, five hook-layout validators, flat layout, discipline scanner, and diff checks.
6. Require named F4 paths to compute Tier C and reject declared B with exit 2.
7. Require staged merge result to compute Tier C.
8. Obtain hostile ACCEPT for the staged result and the exact local merge SHA before push.

## Peer review

An isolated hostile reviewer examined the resulting PR diff relative to updated develop and returned ACCEPT with no blocking findings. It specifically evaluated incoming build/workflow/package changes against F4's generated-entrypoint, helper-edge, CI-site, path-shape, exclusion, and freshness contracts.

## Lead review

- **Conflict correctness:** regeneration retained both F4 `review_risk_test.py` and F1 `skill_lifecycle_test.py` evidence rather than choosing a side.
- **F4 integrity:** graph audit and commit/push suite pass; all three named canaries remain Tier C and reject B.
- **F1 integrity:** promotion fixtures and ordinary check pass; raw pinned-main baseline without event/graph proof still fails closed.
- **F2/F3 integrity:** all four installed layouts pass prompt selection, readable paths, push enforcement, parity, and negative cases.
- **Full-suite integrity:** 18 Python, 36 hook, 2 workflow, all freshness/package/layout/discipline gates pass.
- **Rollback:** revert the merge commit or add a follow-up fix; do not force-push.

## Quantified claims

- Merge conflicts: 1 generated file, 0 unresolved.
- Python modules: 18/18 PASS.
- Hook suites: 36/36 PASS.
- Workflow suites: 2/2 PASS.
- Consumer layouts: 4/4 isolated runtime PASS; 5/5 source/package validators PASS.
- F4 named canaries: 3/3 Tier C, `valid=false`, exit 2 for declared B.
- Generated authority: 198 sources, 804 snapshots, 2,904 mappings current.
- Lifecycle: 0 completions, 198 legacy exceptions current.
- Runtime deployment/release/install/main actions: 0.

## Canary and rollback

Canary: run `review_risk_test.py`, `skill_lifecycle_test.py`, `consumer_runtime_test.py`, then the three named F4 `--declared B` probes. Roll back by reverting the merge commit; no external installation or deployment cleanup is needed.
