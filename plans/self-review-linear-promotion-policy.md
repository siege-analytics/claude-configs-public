# Self-review: canonical develop-to-main promotion policy

## Assumptions
Domain(s): software engineering
Geospatial cross-cut: no
Goal source: User directive on 2026-10-12: “The linear promotion strategy is develop->main. Nothing is merged through till it gets to main, and nothing is deployed till main is installed on the working area.”
Goal source verification: Approved execution plan requires develop-only integration/validation, canonical develop→main promotion, main-only publishing, and exact-main workspace installation.
Plan reference: `plans/reconciliation-2026-10-12.md`
Pre-author-inventory: `.github/workflows/build-and-publish.yml`, `.github/workflows/pr-base-guard.yml`, `.github/workflows/_test_pr_base_guard_policy.sh`, `bin/build.py`, `bin/install.sh`, deploy-drift tests.
Investigate-artifact: `plans/reconciliation-2026-10-12.md`
Pre-mortem-artifact: approved Craft Agent plan `reconcile-and-protect-claude-configs.md`; principal risks restated below.
Hostile-review-artifact: pending independent review before push.
Project-contribution: Establishes one auditable integration→release→installation path and prevents branch divergence from recurring.

## Pre-implementation comprehension
Current behavior: develop and main diverged; scoped promotion branches can target main; hotfix/release labels bypass topology; pushes to develop force-publish all consumer branches; `build.py --deploy` accepts any checkout.
Intended behavior: feature work integrates into develop, only develop may target main, only main publishes, and merge-then-deploy repositories can install only the exact current remote main SHA.
Steps: tighten workflow triggers and head policy; add ancestry checks; commit the deployment model; add exact-main deploy guard; add negative tests; validate the combined tree; set GitHub protections only after checks exist on main.
Success criteria: forbidden branch shapes fail; develop validates without publishing; main alone publishes; non-main deployment fails before workspace mutation; exact-main deployment succeeds; main is an ancestor of develop.
Risks: required checks could deadlock branches if enabled before workflow delivery; branch-name-only checks could accept divergent develop; stale local refs could permit stale installs; post-promotion merge commit temporarily puts main ahead until back-sync.

## Senior adversarial checklist
1. The prior policy called scoped cherry-pick promotions “linear”; that was the core conceptual error.
2. Observable behavior is expressed as allowed/blocked PR and deployment outcomes.
3. Publishing, tags, consumer branches, local installation, and ancestry are all covered.
4. Post-promotion back-sync remains necessary because GitHub creates a main merge commit.
5. Existing workflows, policy tests, build deploy code, and protection API state were inspected.
6. Work is isolated in the reconciliation worktree and branch.
7. Negative cases cover feature/promote/release/hotfix main PRs and non-main deployment.
8. The class is addressed in GitHub checks plus local deploy enforcement, not a one-off branch repair.
9. Done includes hosted checks, protection re-read, main promotion, back-sync, and exact-main install verification.
10. Protection ordering and deployment verification will not be skipped.

## Peer review
Pending implementation. Required checks: YAML inspection, shell syntax, Python AST/compile, policy fixtures, deploy-source fixtures, full build, full hook matrix, and GitHub hosted checks.

## Lead review
Approach-fit: canonical branch topology plus code-level deployment source validation closes both repository and workstation paths. Blast radius includes all PR routing, release publication, and Craft Agent installation. Sequencing must deliver workflows to main before making their check names required.

## Findings
| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| P1 | P1 | Develop pushes currently publish release branches. | pending fix |
| P2 | P1 | Main guard permits scoped promotion, release, and hotfix bypasses. | pending fix |
| P3 | P1 | Workspace deployment accepts non-main revisions. | pending fix |
| P4 | P2 | GitHub cannot represent a permanent develop-superset after a main merge without post-promotion synchronization. | enforce immediate sync workflow/checklist |

## Quantified claims
- “30 main-only and 34 develop-only before #924” — `git rev-list --left-right --count origin/main...origin/develop` at the audited heads → `30 34`.
- “32 hook suites” — reconciled-tree loop over `hooks/_test/*.test.sh` → `HOOK_SUMMARY count=32 failed=0`.

## Rework ledger
| Rework trigger | Root skip | Check cost | Rework cost | Ratio |
|---|---|---|---|---|
| Local CI first used macOS Python 3.9 | CI Python floor not mirrored in initial shell | Low | Low | 1:1 |
| #924 commit trailers were passed as separate paragraphs | `interpret-trailers` formatting not checked | Low | Low | 1:1 |

## Evidence-predates-work
Artifact: plans/self-review-linear-promotion-policy.md
First-added commit: populated after this artifact commit
Work commit: subsequent policy implementation commit
Verification: artifact commit must be an ancestor of the policy implementation commit.
