---
propagation-deferred: will post to ticket with PR
---

# Self-review: ticket-guard / pre-work-check chaining contract (#237)

Self-Review: Explicit chaining between ticket-guard and pre-work-check skills
Self-Review-Source: plans/self-review-237.md
Design-Note-Source: https://github.com/siege-analytics/claude-configs-public/issues/237
Pre-ship-dry-run: N/A — skill text changes, no transformation code
Hostile-review-artifact: WAIVED
Inventoried-shape: pre-work-check has no prerequisite section (grep -c Prerequisite SKILL.md = 0); ticket-guard Interaction section has 3 bullets, no pre-work-check mention
Investigate-artifact: TRIVIAL
Pre-mortem-artifact: TRIVIAL

## Hostile-review-waiver
Reason: Documentation-only change to two SKILL.md files — no executable code modified
Scope: skills/pre-work-check/SKILL.md, skills/ticket-guard/SKILL.md
Compensating-control: Both files are markdown prose; changes are additive cross-references

## Trivial-investigation declaration
Category: documentation-only prose change
Cannot produce error: markdown cross-references cannot cause runtime failures
Reason: Two SKILL.md files need cross-references added. The content of both skills is fully understood from reading them. No executable code, no data shapes, no external dependencies.
Evidence: Both skills read in full. ticket-guard is 122 lines, pre-work-check is 49 lines.
Falsification: If either skill had complex logic, conditional routing, or hook integration, investigation would be required.

## Assumptions
Goal source: https://github.com/siege-analytics/claude-configs-public/issues/237
Pre-author-inventory: NONE
Trivial-against-state: documentation-only skill text change, no state contact
Working as: software engineer
Roles: Junior (wrote the cross-references), Senior (verified sequencing logic)

## Peer review

Shelves checked: writing-code:17

### Gate evidence
- N/A — no executable code, no tests, no notebooks, no doc build
- [no-gates] — markdown-only changes to SKILL.md files

### Cross-reference verification
- pre-work-check now declares ticket-guard as prerequisite (new section before Checklist)
- ticket-guard now lists pre-work-check as per-ticket companion (new bullet in Interaction section)
- Both reference each other bidirectionally

## Lead review

**[Senior]** The chaining contract is the simplest viable fix: pre-work-check
says "ticket-guard must have run first" and ticket-guard says
"pre-work-check is the per-ticket follow-up." Neither invokes the other
programmatically — the contract is declarative, which matches how the
resolver routes skills (it reads SKILL.md, not function calls).

## Quantified claims

- 2 files modified: skills/pre-work-check/SKILL.md, skills/ticket-guard/SKILL.md
- 0 new files
- pre-work-check: +8 lines (Prerequisite section)
- ticket-guard: +1 line (Interaction bullet)
