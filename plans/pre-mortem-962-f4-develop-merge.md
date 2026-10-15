# Pre-mortem: merge F1 and F2/F3 develop into F4

Goal source: coordinator message from Skills-Reviser Session Recovery after F1 and F2/F3 reached `develop` at `4dcad7c2582cf1fca13d9ad922513599fd1234ca`.

## Scope

Merge `origin/develop` into `fix/962-f4-enforcement-risk`, preserve the F4 enforcement graph, resolve shared generated evidence authoritatively, and revalidate F1-F4 together. Do not merge the PR or affect main, release, deployment, installation, or publication.

## Predicted failures and controls

1. **Generated inventory conflict drops one feature's evidence.** Regenerate with `bin/skill-inventory.py`; require both `review_risk_test.py` and `skill_lifecycle_test.py` under the branch skill.
2. **Incoming workflow edits invalidate F4's exact CI invocation counts.** Run `bin/_test/review_risk_test.py`; it parses the actual isolated build and exact workflow invocation sites.
3. **Incoming build/package changes create an unclassified blocking entrypoint/helper.** Require the F4 graph audit to pass against generated manifest/settings and helper-site snapshot.
4. **F1 exception becomes broadly permissive.** Run promotion graph fixtures, ordinary lifecycle freshness, and the raw main-baseline no-context negative.
5. **F2/F3 packages regress outside source checkout.** Run the four-layout isolated consumer runtime integration plus source/nested/flat/Claude Code/Craft Agent hook validation.
6. **Shared metrics or inventories become stale after conflict resolution/artifacts.** Regenerate inventory, rebuild all layouts, and run every freshness checker.
7. **Green focused tests mask a broader regression.** Rerun all Python, hook, workflow, package, layout, discipline, and diff-hygiene suites.
8. **Merge is pushed without review at its immutable identity.** Obtain pre-commit hostile ACCEPT, commit locally, obtain another independent review of the exact commit SHA, then push without force.

## Rollback

Before push, abort the merge if unresolved. After the merge commit is pushed, revert only that merge commit or update the feature branch with a follow-up fix; never rewrite shared history. No external runtime state is changed.
