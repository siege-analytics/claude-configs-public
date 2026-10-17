# Self-review: proportional review risk policy

## Assumptions

Domain(s): software engineering, governance enforcement
Geospatial cross-cut: no
Working as: software engineer, tech lead
Goal source: user-approved `skill-library-simplification.md`, Phase 5 / proposed PR 6
Goal source verification: approved plan explicitly requires Tier A/B/C machine-checkable triggers, escalation without downgrade, and evidence validation rather than artifact length.
Plan reference: `/Users/dheerajchand/.craft-agent/workspaces/my-workspace/sessions/261012-refined-storm/plans/skill-library-simplification.md`
Pre-author-inventory: `plans/investigate-risk-tier-policy.md`
Investigate-artifact: `plans/investigate-risk-tier-policy.md`
Pre-mortem-artifact: `plans/pre-mortem-risk-tier-policy.md`
Hostile-review-artifact: `plans/hostile-review-risk-tier-policy.md`
Project-contribution: replace uniform review ceremony with enforceable proportional evidence while preserving a fail-closed high-risk boundary.

## Pre-implementation comprehension

Current behavior required broadly full review artifacts without computing change risk, while some high-risk evidence remained trailer convention. Intended behavior computes a deterministic minimum from all changed paths, permits escalation only, and validates proportional evidence at commit, prompt-push, and native pre-push boundaries. Installed packages must carry the classifier and policy. Success requires positive and negative fixtures, legacy compatibility, package/deploy proof, all hook suites, and no runtime skill-load-set change.

## Senior adversarial checklist

Reject missing deletions, rename destination laundering, unknown-path Tier A, declared downgrade, missing classifier fail-open, policy self-downgrade, absent packaged dependencies, retroactive history invalidation, Tier A with runtime files, Tier B without focused tests, and Tier C without hostile review.

## Peer review

- Classifier: exact regex priority C → generated A → standard B → explicit trivial A → unknown B.
- Git shapes: staged, commit, and base/head modes use `--no-renames` with A/C/D/M/R/T.
- Commit enforcement: Tier A short record; Tier B/C source; Tier C hostile trailer; `[no-review]` only after validated A.
- Runtime enforcement: legacy commits preserve full validation; declared new tiers receive proportional structure.
- Packaging: both consumer packages and Craft deployment include classifier/policy.
- Tests: direct classifier, commit-msg, pre-push history, legacy review fixture, deployment fixture, hosted workflow freshness.

## Lead review

Approach fit: one data policy and one classifier prevent shell gates from inventing divergent risk categories. Blast radius is intentionally high because commit/push governance changes; therefore this work declares Tier C and retains full evidence. The narrow safety boundary remains non-overridable: missing policy/classifier fails closed, unknown paths are never Tier A, and deletion/rename source paths remain visible.

## Findings

| ID | Priority | Description | Resolution |
|---|---|---|---|
| R1 | P1 | Initial diff filter omitted deletions and could launder a critical rename. | fixed with `--no-renames --diff-filter=ACDMRT` and staged negative fixtures |
| R2 | P1 | Installed native hooks could lack classifier/policy runtime. | package and deploy both dependencies; assert in package and deploy tests |
| R3 | P2 | Treating all hooks Tier C contradicted the approved non-critical-hook Tier B example. | narrowed Tier C to Git/Bash/write enforcement and resolver gate/guard paths |
| R4 | P2 | Strict new tier fields could retroactively invalidate historical artifacts. | pinned epoch preserves pre-policy full validation; new tierless commits block |
| R5 | P1 | Editable policy could remove its own high-risk pattern. | code-owned classifier floor plus independent shell floors protect governance files |
| R6 | P1 | Pointer existence allowed empty or structurally invalid pushed artifacts. | validate exact committed Tier B/C content and non-empty hostile evidence |

## Test plan

Run classifier unit tests, proportional commit/push fixtures, legacy self-review fixtures, package/deploy tests, generated authority, review metrics freshness, and all hook suites. Hostile-review all executable changes. Hosted checks must pass before merge.

## Quantified claims

Freshness-checked `catalog/review-risk-metrics.json` records 3,905 classifier characters, 1,801 policy characters, fixture tiers A/B/C/C, required-evidence counts 1/3/7, and runtime load-set change 0. Before this PR the minimum artifact requirement was effectively uniform for all tiers; after it, Tier A has one short record, Tier B three focused evidence classes, and Tier C seven full evidence classes.

## Rollback

Revert the PR. Existing legacy full-validation behavior remains represented in history, and no skill lifecycle entry is retired or deleted by this change.
