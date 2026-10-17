# Self-review: progressive runtime risk trigger

## Assumptions

Domain(s): software engineering, governance enforcement
Working as: software engineer, tech lead
Goal source: approved simplification plan safety boundary plus PR #957 progressive runtime contract
Goal source verification: resolver manifest, selector, and injection hook determine which detailed safety procedures enter context; omission can silently remove enforcement guidance.
Pre-author-inventory: direct audit of `catalog/review-risk-policy.json` against PR #957 runtime surfaces
Investigate-artifact: this artifact, Assumptions and Findings
Pre-mortem-artifact: this artifact, Pre-mortem section
Hostile-review-artifact: `plans/hostile-review-progressive-runtime-risk-trigger.md`
Project-contribution: ensure changes to every progressive-loading control surface require Tier C evidence.

## Pre-mortem

### Tiger 1 — Safety route downgrade

**Severity:** HIGH. A Tier B resolver change can omit mandatory detailed procedures without independent review. Mitigation: classify manifest, selector, and injection hook Tier C and add direct fixtures. Rollback: revert this commit.

## Peer review

Compared the three PR #957 runtime control surfaces against all current high-risk patterns. None matched before this fix. Added explicit path patterns and exact assertions.

## Lead review

The change closes the class across configuration, selection implementation, and runtime injection rather than patching one file. It does not change routing behavior or load sets.

## Findings

| ID | Priority | Description | Resolution |
|---|---|---|---|
| F1 | P1 | Progressive runtime safety controls classified Tier B. | all three paths now Tier C with tests |

## Quantified claims

Three additional paths become Tier C. Runtime load-set change is zero. Source/lifecycle counts are unchanged.

## Test plan

Run classifier fixtures, review metrics freshness, full hosted-equivalent matrix, and all hook suites.
