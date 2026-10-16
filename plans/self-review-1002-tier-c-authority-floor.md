# Self-review — #1002 authority dependency Tier C floor

Pre-mortem-artifact: plans/pre-mortem-1002-tier-c-authority-floor.md
Hostile-review-artifact: plans/hostile-review-1002-tier-c-authority-floor.md

## Assumptions

- The accepted #848 resolver remains configured-policy evaluation until this pilot supplies protected/native evidence.
- Tier classification governs review evidence; it does not itself authenticate that evidence or grant operation authority.
- `catalog/effective-policy-selection.json` is authority-sensitive. The working `catalog/effective-policy.json` and synthetic fixtures are proposal content and must not become approval receipts.
- #1001 owns composition. This slice must remain valid without selecting its final package shape.

## Peer review

The accepted #848 hostile review required the explicit authority-dependency closure before enforcement use. A new hostile audit attempted pattern, rename/delete, policy-plus-helper, test-only, schema/catalog, package/generated and proposal-confusion bypasses. It found no blocker and recorded the bounded reviewed-policy residual.

## Lead review

The change extends only the existing canonical review-risk policy. The executable expectation list enumerates seven paths: both helpers, both behavioral test modules, the immutable selection receipt, contract schema and contract catalog. The existing mutation loop applies modification, deletion, rename-source and Tier B downgrade probes to all seven. Proposal-only policy and fixture paths have explicit Tier B assertions.

No resolver value, selection receipt, contract content, generated instruction, runtime guard, workflow, protected setting, installation or release artifact changes in this slice.

## Test plan

- Build both layouts before generated-output checks.
- Run `bin/_test/review_risk_test.py`.
- Run `hooks/_test/review_risk_policy.test.sh`.
- Run direct `review-risk.py --declared B` rejection for each authority dependency.
- Prove working policy remains valid at declared Tier B.
- Run every Python module, hook suite and workflow policy suite.
- Rebuild and verify inventory, metrics, generated authority, ontology and `git diff --check`.

## Quantified claims

Focused results so far:
- authority dependency paths at Tier C: 7/7;
- direct Tier B downgrade probes rejected: 7/7;
- proposal catalog remains Tier B: 1/1;
- review-risk Python regression: passed, including staged modify/delete/rename for the expanded audited closure;
- review-risk hook suite: 12/12.

Full-suite results: 21/21 Python modules, 36/36 hook suites, and 2/2 workflow suites passed. Inventory, progressive metrics, generated authority (198 sources / 804 snapshots / 2,904 mappings), ontology (34 terms / 136 bound values), and both-layout build checks are current.

## Canary and rollback

Canary: changing only `catalog/effective-policy-selection.json` or only `bin/effective_policy.py` must compute Tier C and reject declared Tier B. Counter-canary: changing only `catalog/effective-policy.json` remains Tier B and has no authorization effect. Revert this commit to restore prior review classification; no runtime/install/protected state changes require rollback.

## Independent review and integration refresh

Independent review at exact `eec0dd5383c3351115c67fd53a68fc5759a8da27` reproduced all 7 direct Tier B rejections, all 21 staged modify/delete/rename-source rejections, the 3 proposal controls, the complete review-risk suite and 12 hook-policy scenarios. It found no classifier blocker. It did find stale generated metrics: the policy grew from 2,621 to 2,746 characters without refreshing `catalog/review-risk-metrics.json`.

The replacement merges accepted `develop@4ca8f4060a511920190e3c2346f23512a289e906` without rewriting the reviewed commit and regenerates that metric. The combined matrix passes 22/22 Python modules, 36/36 hook suites, 2/2 workflow suites, all 25 work-cycle scenarios, review-risk mutations, build/freshness and ontology checks. Terminal hosted checks and a fresh exact-head integration verdict remain required. No broader classifier or runtime behavior changes are included.
