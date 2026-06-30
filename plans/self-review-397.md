---
propagation-deferred: will post to ticket with PR
---

# Self-review: Tiger severity scoring (#397)

Self-Review: 5-dimension severity scoring with composite score and worked example
Self-Review-Source: plans/self-review-397.md
Design-Note-Source: https://github.com/siege-analytics/claude-configs-public/issues/397
Hostile-review-artifact: WAIVED

## Hostile-review-waiver
Reason: Documentation addition to existing skill file, no executable code
Scope: skills/pre-mortem/SKILL.md (new Tiger severity scoring section + artifact format update)
Compensating-control: text-only changes; scoring is advisory enhancement, not enforcement

## Trivial-investigation declaration
Category: documentation addition
Cannot produce error: no executable code modified
Reason: Adding scoring dimensions and worked example to skill file
Evidence: git diff --stat shows only .md files changed
Falsification: If a hook parses the pre-mortem artifact format and the new Severity field breaks parsing, investigation would be required

## Assumptions
Goal source: https://github.com/siege-analytics/claude-configs-public/issues/397
Investigate-artifact: TRIVIAL (see ## Trivial-investigation declaration above)
Pre-mortem-artifact: TRIVIAL (see ## Trivial-investigation declaration above)
Pre-author-inventory: NONE
Trivial-against-state: documentation addition, no state contact
Working as: software engineer
Roles: Junior (wrote the scoring section), Senior (verified dimension weights and tier mapping)

## Peer review

Shelves checked: writing-prose:1, writing-claims:1

### Gate evidence
- N/A — no executable files, no tests, no notebooks, no doc build

## Lead review

**[Senior]** Clean enhancement. The scoring augments (not replaces) the
existing urgency tiers, so no existing artifacts break. The worked
example with the pagination Tiger is concrete and demonstrates the
calculation. The per-project override path via PROJECT.md is the right
extensibility mechanism.

## Quantified claims

- 1 file modified: skills/pre-mortem/SKILL.md
- 5 scoring dimensions with weights summing to 100%
- 4 priority tiers (emergency-stop, mitigate-before-ship, monitor-after-ship, accept-and-document)
- 1 worked example

## Findings

No findings.
