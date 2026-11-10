---
ticket_refs:
  - siege-analytics/claude-configs-public#1241
  - siege-analytics/claude-configs-public#1261
---

# Branch review followup (#1261, #1229)

Two automated review findings were confirmed against exact develop e077d16f in isolated actual Git fixtures. Path-only worktree requests could create protected main/develop names from a known develop tip because the guard checked a placeholder. An exact already-authorized v0.15.6 release command passed without a newline and failed with one because shell substitution stripped command bytes. No live repository was changed by the probes.

## Assumptions

Normal features still use verified develop; protected bootstrap and exact authorized release sources retain their existing routes. Existing branch reuse is not creation. Hook payload command bytes remain the comparison authority; do not relax matching or synthesize authorization metadata.

## Pre-mortem

- Deriving a real name too early could block legitimate reuse. Preserve the existing-ref return first, and exercise actual existing-main reuse plus ordinary derived-feature creation.
- Preserving the extractor delimiter could reject every exact grant. The first focused attempt caught that baseline failure; retain its log and remove exactly the extractor's one output newline while preserving0/1/2 command newlines.
- Normalizing metadata could widen release authority. Keep the exact existing comparison, roles, Task scope and lifecycle checks unchanged; preserve their negative cases.

## Peer review

Both actual counterexamples were posted directly in PR1261 threads4521777211 and4521777216. Root is independently reviewing the narrow runtime/test delta; no external static finding is treated as proof by itself.

## Lead review

The protected-name check now receives the actual derived basename only after existing-branch reuse. A Bash sentinel preserves trailing command LF, then removes only extract-json.py's output delimiter. No new source exception, field, registry, permission or timeout is added.

## Quantified claims

Two focused methods passed6.813s, including actual Git reuse/creation and existing release-role/lifecycle controls. The first delimiter-preserving attempt failed the baseline, was corrected and remains preserved externally. Full branch and canonical/source-bound producer results are separate and will be recorded truthfully.

## Test plan

Run all30 branch-source methods with unchanged budgets, build canonical outputs and check inventories/kernel/progressive/risk closure. Record the actual changed source/test/shell bytes through the public native producer, validate the committed receipt, and use invocation-only native commit/prepush. Normal exact-head hosted acceptance remains required.

Pre-mortem-artifact: plans/branch-review-followup-1261.md#pre-mortem
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/pull/1261

Actual final branch validation: all30 methods passed27.181s, then the genuine3-input producer reran all30 methods and all6 canonical closure checks successfully. Both changed runtime files match all4 package layouts exactly. Native commit/strict receipt and independent final source review remain separate. No live repository or frozen promotion source was changed.
